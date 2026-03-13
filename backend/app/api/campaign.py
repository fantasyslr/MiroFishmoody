"""
Campaign API — 方案提交 + 评审 + 结算 + 校准
"""

import uuid
import threading
from collections import defaultdict
from datetime import datetime
from flask import request, jsonify

from . import campaign_bp
from ..config import Config
from ..utils.logger import get_logger
from ..utils.llm_client import LLMClient
from ..models.task import TaskManager, TaskStatus
from ..models.campaign import Campaign, CampaignSet, ProductLine
from ..models.evaluation import EvaluationResult
from ..services.audience_panel import AudiencePanel
from ..services.pairwise_judge import PairwiseJudge
from ..services.campaign_scorer import CampaignScorer
from ..services.summary_generator import SummaryGenerator
from ..services.judge_calibration import JudgeCalibration
from ..services.resolution_tracker import ResolutionTracker

logger = get_logger('ranker.api.campaign')
task_manager = TaskManager()

# 内存存储（MVP 阶段）
_evaluation_store: dict = {}


def _parse_campaigns(data: dict) -> CampaignSet:
    """从 JSON 请求体解析 campaign set"""
    campaigns_raw = data.get("campaigns", [])
    if not campaigns_raw:
        raise ValueError("至少需要 2 个 campaign 方案")
    if len(campaigns_raw) < 2:
        raise ValueError("至少需要 2 个 campaign 方案")
    if len(campaigns_raw) > Config.MAX_CAMPAIGNS:
        raise ValueError(f"最多支持 {Config.MAX_CAMPAIGNS} 个方案")

    campaigns = []
    for i, c in enumerate(campaigns_raw):
        pl_str = c.get("product_line", "colored_lenses")
        try:
            product_line = ProductLine(pl_str)
        except ValueError:
            raise ValueError(
                f"方案 {i+1}: product_line 必须是 'colored_lenses' 或 'moodyplus'，"
                f"收到 '{pl_str}'"
            )

        if not c.get("name"):
            raise ValueError(f"方案 {i+1}: name 不能为空")
        if not c.get("core_message"):
            raise ValueError(f"方案 {i+1}: core_message 不能为空")

        campaigns.append(Campaign(
            id=c.get("id", f"campaign_{i+1}"),
            name=c["name"],
            product_line=product_line,
            target_audience=c.get("target_audience", ""),
            core_message=c["core_message"],
            channels=c.get("channels", []),
            creative_direction=c.get("creative_direction", ""),
            budget_range=c.get("budget_range"),
            kv_description=c.get("kv_description"),
            promo_mechanic=c.get("promo_mechanic"),
            extra=c.get("extra", {}),
        ))

    set_id = data.get("set_id", str(uuid.uuid4()))
    return CampaignSet(
        set_id=set_id,
        campaigns=campaigns,
        context=data.get("context", ""),
        created_at=datetime.now().isoformat(),
    )


def _build_persona_predictions(panel_scores, campaigns):
    """
    从 panel_scores 构建 per-persona prediction records。
    每个 persona 对各 campaign 的 score 归一化为 preference (sum=1 per persona)。
    """
    # 按 persona 分组
    by_persona = defaultdict(list)
    for ps in panel_scores:
        by_persona[ps.persona_id].append(ps)

    records = []
    for persona_id, scores in by_persona.items():
        total = sum(s.score for s in scores)
        for s in scores:
            preference = s.score / total if total > 0 else 1.0 / len(scores)
            records.append({
                "persona_id": s.persona_id,
                "campaign_id": s.campaign_id,
                "score": s.score,
                "preference": round(preference, 4),
            })
    return records


def _build_judge_predictions(pairwise_results):
    """
    从 pairwise_results 的 votes 构建 per-judge prediction records。
    """
    records = []
    for pr in pairwise_results:
        for vote in pr.votes:
            records.append({
                "judge_id": vote.get("judge_id", ""),
                "campaign_a_id": pr.campaign_a_id,
                "campaign_b_id": pr.campaign_b_id,
                "winner_pick": vote.get("winner", "tie"),
                "dimensions": vote.get("dimensions", {}),
            })
    return records


def _run_evaluation(task_id: str, campaign_set: CampaignSet):
    """在后台线程中执行完整评审流程"""
    try:
        task_manager.update_task(
            task_id, status=TaskStatus.PROCESSING,
            progress=5, message="初始化评审引擎..."
        )

        llm = LLMClient()
        campaigns = campaign_set.campaigns

        # 加载校准权重
        calibration = JudgeCalibration()
        judge_weights, persona_weights = calibration.get_weights()

        # Phase 1: Audience Panel
        task_manager.update_task(task_id, progress=10, message="Audience Panel 评审中...")
        panel = AudiencePanel(llm_client=llm)
        panel_scores = panel.evaluate_all(campaigns)
        task_manager.update_task(task_id, progress=40, message="Panel 评审完成")

        # Phase 2: Pairwise Judge
        task_manager.update_task(task_id, progress=45, message="Pairwise 对决中...")
        judge = PairwiseJudge(llm_client=llm)
        pairwise_results, bt_scores = judge.evaluate_all(campaigns)
        task_manager.update_task(task_id, progress=80, message="对决完成")

        # Phase 3: Market Scoring
        task_manager.update_task(task_id, progress=85, message="Market scoring...")
        scorer = CampaignScorer(
            judge_weights=judge_weights,
            persona_weights=persona_weights,
        )
        rankings, probability_board = scorer.score(
            campaigns, panel_scores, pairwise_results, bt_scores,
        )

        # Phase 5.1: 持久化 per-persona / per-judge 预测
        win_probs = {c.campaign_id: c.win_probability for c in probability_board.campaigns}
        calibration.save_predictions(
            set_id=campaign_set.set_id,
            persona_predictions=_build_persona_predictions(panel_scores, campaigns),
            judge_predictions=_build_judge_predictions(pairwise_results),
            campaign_win_probabilities=win_probs,
        )

        # Phase 4: Summary
        task_manager.update_task(task_id, progress=90, message="生成总结报告...")
        summarizer = SummaryGenerator(llm_client=llm)
        summary_data = summarizer.generate(
            campaigns, rankings, panel_scores, pairwise_results,
        )

        # Resolution tracker
        resolver = ResolutionTracker()

        # 构建最终结果
        result = EvaluationResult(
            set_id=campaign_set.set_id,
            rankings=rankings,
            panel_scores=panel_scores,
            pairwise_results=pairwise_results,
            summary=summary_data["summary"],
            assumptions=summary_data["assumptions"],
            confidence_notes=summary_data["confidence_notes"],
            probability_board=probability_board.to_dict(),
            resolution_ready_fields=resolver.get_resolution_ready_fields(),
        )

        result_dict = result.to_dict()
        _evaluation_store[campaign_set.set_id] = result_dict

        top = probability_board.campaigns[0] if probability_board.campaigns else None
        task_manager.complete_task(task_id, result={
            "set_id": campaign_set.set_id,
            "campaign_count": len(campaigns),
            "top_campaign": top.campaign_name if top else None,
            "top_verdict": top.verdict if top else None,
            "top_win_probability": round(top.win_probability, 3) if top else None,
            "no_clear_edge": probability_board.no_clear_edge,
            "spread": round(probability_board.spread, 3),
        })

    except Exception as e:
        logger.error(f"评审失败: {e}", exc_info=True)
        task_manager.fail_task(task_id, str(e))


@campaign_bp.route('/evaluate', methods=['POST'])
def evaluate():
    """提交 campaign 方案进行评审（异步）"""
    try:
        try:
            data = request.get_json(force=True, silent=True)
        except Exception:
            data = None
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400

        campaign_set = _parse_campaigns(data)
        task_id = task_manager.create_task(
            "campaign_evaluation",
            metadata={"set_id": campaign_set.set_id}
        )

        thread = threading.Thread(
            target=_run_evaluation,
            args=(task_id, campaign_set),
            daemon=True,
        )
        thread.start()

        return jsonify({
            "task_id": task_id,
            "set_id": campaign_set.set_id,
            "campaign_count": len(campaign_set.campaigns),
            "message": "评审已启动，使用 task_id 查询进度",
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"提交评审失败: {e}", exc_info=True)
        return jsonify({"error": f"内部错误: {str(e)}"}), 500


@campaign_bp.route('/evaluate/status/<task_id>', methods=['GET'])
def evaluate_status(task_id: str):
    """查询评审任务进度"""
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    return jsonify(task.to_dict())


@campaign_bp.route('/result/<set_id>', methods=['GET'])
def get_result(set_id: str):
    """获取评审结果"""
    result = _evaluation_store.get(set_id)
    if not result:
        return jsonify({"error": "评审结果不存在"}), 404
    return jsonify(result)


@campaign_bp.route('/resolve', methods=['POST'])
def resolve():
    """
    提交赛后结算

    POST /api/campaign/resolve
    Body: {
        "set_id": "...",
        "winner_campaign_id": "...",
        "actual_metrics": {"ctr": 0.03, "cvr": 0.02, ...},
        "notes": "optional"
    }
    """
    try:
        try:
            data = request.get_json(force=True, silent=True)
        except Exception:
            data = None
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400

        set_id = data.get("set_id")
        winner_id = data.get("winner_campaign_id")
        if not set_id or not winner_id:
            return jsonify({"error": "set_id 和 winner_campaign_id 必填"}), 400

        # 尝试从内存获取 predicted probabilities
        predicted = None
        stored = _evaluation_store.get(set_id)
        if stored:
            board = stored.get("probability_board", {})
            predicted = {
                c["campaign_id"]: c["win_probability"]
                for c in board.get("campaigns", [])
            }

        # 内存无数据时，回退到持久化的 predictions 文件
        if not predicted:
            calibration_fallback = JudgeCalibration()
            preds_data = calibration_fallback.load_predictions(set_id)
            if preds_data:
                predicted = preds_data.get("campaign_win_probabilities", {})

        if not predicted:
            return jsonify({"error": "评审结果不存在（内存和磁盘均无数据）"}), 404

        if winner_id not in predicted:
            return jsonify({"error": f"campaign_id '{winner_id}' 不在评审结果中"}), 400

        tracker = ResolutionTracker()
        record = tracker.resolve(
            set_id=set_id,
            winner_campaign_id=winner_id,
            actual_metrics=data.get("actual_metrics", {}),
            predicted_probabilities=predicted,
            notes=data.get("notes", ""),
        )

        # 检查校准条件：同时检查 resolved_set_count 和 sets_with_predictions
        calibration = JudgeCalibration()
        resolutions = calibration.load_resolutions()
        resolved_set_ids = set(r["set_id"] for r in resolutions)
        sets_with_preds = sum(
            1 for sid in resolved_set_ids
            if calibration.load_predictions(sid) is not None
        )

        if sets_with_preds >= 5:
            recalibrate_hint = (
                f"已有 {sets_with_preds} 个有预测数据的评审集，"
                f"调用 POST /api/campaign/recalibrate 触发校准"
            )
        elif len(resolved_set_ids) >= 5 and sets_with_preds < 5:
            recalibrate_hint = (
                f"已有 {len(resolved_set_ids)} 个评审集结算，"
                f"但仅 {sets_with_preds} 个有预测数据，"
                f"还需 {5 - sets_with_preds} 个有预测数据的评审集"
            )
        else:
            remaining = 5 - len(resolved_set_ids)
            recalibrate_hint = f"还需 {remaining} 个评审集结算后才能校准"

        return jsonify({
            "status": "resolved",
            "set_id": set_id,
            "winner": winner_id,
            "predicted_win_prob": round(record.predicted_win_prob, 3),
            "recalibrate": recalibrate_hint,
        })

    except Exception as e:
        logger.error(f"结算失败: {e}", exc_info=True)
        return jsonify({"error": f"内部错误: {str(e)}"}), 500


@campaign_bp.route('/calibration', methods=['GET'])
def get_calibration():
    """查看 judge/persona 校准状态"""
    calibration = JudgeCalibration()
    stats = calibration.get_all_stats()
    resolutions = calibration.load_resolutions()
    meta = calibration.get_calibration_meta()

    # 去重计算已结算评审集数
    resolved_set_ids = set(r["set_id"] for r in resolutions)
    # 检查有多少评审集有预测数据
    sets_with_preds = sum(
        1 for sid in resolved_set_ids
        if calibration.load_predictions(sid) is not None
    )

    has_stats = len(stats) > 0
    enough_sets = sets_with_preds >= 5
    last_cal = meta.get("last_calibrated_at")

    # 从 meta 读取真实校准状态（由 recalibrate() 写入）
    persona_cal_status = meta.get("persona_calibration", "not_run")
    judge_cal_status = meta.get("judge_calibration", "not_run")

    persona_stats = [s for s in stats if s.judge_type == "persona"]
    judge_stats_list = [s for s in stats if s.judge_type == "judge"]

    if has_stats:
        status_msg = (
            f"校准已完成: {len(persona_stats)} persona ({persona_cal_status}) + "
            f"{len(judge_stats_list)} judge ({judge_cal_status})。"
            f"基于 {sets_with_preds} 个有预测数据的评审集。"
        )
    elif enough_sets:
        status_msg = (
            f"已有 {sets_with_preds} 个有预测数据的评审集。"
            f"调用 POST /api/campaign/recalibrate 执行校准。"
        )
    elif len(resolved_set_ids) >= 5 and sets_with_preds < 5:
        status_msg = (
            f"已有 {len(resolved_set_ids)} 个评审集结算，但仅 {sets_with_preds} 个有预测数据。"
            f"还需 {5 - sets_with_preds} 个有预测数据的评审集才能校准。"
        )
    else:
        remaining = 5 - len(resolved_set_ids)
        status_msg = f"还需 {remaining} 个评审集结算才能开始校准。"

    return jsonify({
        "resolution_count": len(resolutions),
        "resolved_set_count": len(resolved_set_ids),
        "sets_with_predictions": sets_with_preds,
        "calibration_supported": True,
        "calibration_ready": enough_sets,
        "last_calibrated_at": last_cal,
        "judge_stats_count": len(stats),
        "persona_calibration": persona_cal_status,
        "judge_calibration": judge_cal_status,
        "judge_stats": [s.to_dict() for s in stats],
        "message": status_msg,
    })


@campaign_bp.route('/recalibrate', methods=['POST'])
def recalibrate():
    """
    触发 judge/persona 校准

    POST /api/campaign/recalibrate
    无需请求体。
    """
    try:
        calibration = JudgeCalibration()
        result = calibration.recalibrate()
        return jsonify(result)
    except Exception as e:
        logger.error(f"校准失败: {e}", exc_info=True)
        return jsonify({"error": f"校准失败: {str(e)}"}), 500


@campaign_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """列出所有评审任务"""
    tasks = task_manager.list_tasks("campaign_evaluation")
    return jsonify({"tasks": tasks})
