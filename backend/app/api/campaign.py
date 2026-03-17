"""
Campaign API — 方案提交 + 评审 + 结算 + 校准
"""

import uuid
import json
import os
import base64
import threading
from datetime import datetime
from flask import request, jsonify, Response, send_from_directory
from werkzeug.utils import secure_filename

from . import campaign_bp
from ..auth import login_required, get_current_user
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
from ..services.brief_parser import BriefParser
from ..services.evaluation_orchestrator import EvaluationOrchestrator

logger = get_logger('ranker.api.campaign')
task_manager = TaskManager()
_calibration = JudgeCalibration()

# 内存存储（MVP 阶段）
_evaluation_store: dict = {}
_store_lock = threading.Lock()
_RESULTS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'results')
os.makedirs(_RESULTS_DIR, exist_ok=True)


def _save_result(set_id: str, result: dict) -> None:
    """持久化完整评审结果，支持服务重启后恢复。"""
    path = os.path.join(_RESULTS_DIR, f"{set_id}.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def _load_result(set_id: str):
    """从磁盘加载完整评审结果。"""
    path = os.path.join(_RESULTS_DIR, f"{set_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


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
    seen_ids = set()
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

        campaign_id = c.get("id", f"campaign_{i+1}")
        if campaign_id in seen_ids:
            raise ValueError(f"方案 {i+1}: campaign id '{campaign_id}' 重复")
        seen_ids.add(campaign_id)

        campaigns.append(Campaign(
            id=campaign_id,
            name=c["name"],
            product_line=product_line,
            target_audience=c.get("target_audience", ""),
            core_message=c["core_message"],
            channels=c.get("channels", []),
            creative_direction=c.get("creative_direction", ""),
            budget_range=c.get("budget_range"),
            kv_description=c.get("kv_description"),
            promo_mechanic=c.get("promo_mechanic"),
            image_paths=c.get("image_paths", []),
            extra=c.get("extra", {}),
        ))

    set_id = data.get("set_id", str(uuid.uuid4()))
    parent_set_id = data.get("parent_set_id")

    campaign_set = CampaignSet(
        set_id=set_id,
        campaigns=campaigns,
        context=data.get("context", ""),
        created_at=datetime.now().isoformat(),
    )

    # Store parent_set_id in CampaignSet extra for downstream use
    if parent_set_id:
        campaign_set.context = campaign_set.context  # keep original
        for c in campaign_set.campaigns:
            c.extra["parent_set_id"] = parent_set_id

    return campaign_set




ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
IMAGES_DIR = os.path.join(Config.UPLOAD_FOLDER, 'images')
os.makedirs(IMAGES_DIR, exist_ok=True)


def _allowed_image(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


@campaign_bp.route('/upload-image', methods=['POST'])
@login_required
def upload_image():
    """上传 campaign 素材图片"""
    if 'file' not in request.files:
        return jsonify({"error": "没有文件"}), 400

    file = request.files['file']
    if not file.filename or not _allowed_image(file.filename):
        return jsonify({"error": "只支持 JPG、PNG、WEBP 格式"}), 400

    # Fast-path size rejection via Content-Length header
    content_length = request.content_length
    if content_length and content_length > MAX_IMAGE_SIZE:
        return jsonify({"error": "图片不能超过 5MB"}), 413

    # Read and check actual size (Content-Length can be spoofed)
    file_data = file.read()
    if len(file_data) > MAX_IMAGE_SIZE:
        return jsonify({"error": "图片不能超过 5MB"}), 400

    # Try to resize if PIL available
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(file_data))
        max_dim = 1024
        if max(img.size) > max_dim:
            ratio = max_dim / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.LANCZOS)
            buf = io.BytesIO()
            fmt = 'JPEG' if file.filename.lower().endswith(('.jpg', '.jpeg')) else 'PNG'
            img.save(buf, format=fmt, quality=85)
            file_data = buf.getvalue()
    except ImportError:
        pass  # PIL not available, use original

    # Save with campaign_id prefix for per-campaign binding
    set_id = request.form.get('set_id', 'unsorted')
    campaign_id = request.form.get('campaign_id', '')
    save_dir = os.path.join(IMAGES_DIR, secure_filename(set_id))
    os.makedirs(save_dir, exist_ok=True)

    safe_name = secure_filename(file.filename)
    uid = str(uuid.uuid4())[:8]
    if campaign_id:
        filename = f"{secure_filename(campaign_id)}__{uid}__{safe_name}"
    else:
        filename = f"__{uid}__{safe_name}"
    save_path = os.path.join(save_dir, filename)

    # Path traversal guard: ensure resolved path stays within IMAGES_DIR
    if not os.path.realpath(save_path).startswith(os.path.realpath(IMAGES_DIR)):
        return jsonify({"error": "非法文件路径"}), 400

    with open(save_path, 'wb') as f:
        f.write(file_data)

    return jsonify({
        "image_id": filename,
        "url": f"/api/campaign/image-file/{secure_filename(set_id)}/{filename}",
        "size": len(file_data),
    })


@campaign_bp.route('/image-file/<set_id>/<filename>', methods=['GET'])
@login_required
def serve_image_file(set_id: str, filename: str):
    """提供 campaign 素材图片的静态文件访问"""
    safe_set_id = secure_filename(set_id)
    safe_filename = secure_filename(filename)
    image_dir = os.path.join(IMAGES_DIR, safe_set_id)
    file_path = os.path.join(image_dir, safe_filename)
    if not os.path.isfile(file_path):
        return jsonify({"error": "图片不存在"}), 404
    return send_from_directory(image_dir, safe_filename)


@campaign_bp.route('/images/<set_id>', methods=['GET'])
@login_required
def list_images(set_id: str):
    """列出某个 set_id 下的所有已上传图片"""
    safe_set_id = secure_filename(set_id)
    image_dir = os.path.join(IMAGES_DIR, safe_set_id)
    if not os.path.isdir(image_dir):
        return jsonify({"images": []})

    images = []
    for fname in sorted(os.listdir(image_dir)):
        if _allowed_image(fname):
            images.append({
                "filename": fname,
                "url": f"/api/campaign/image-file/{safe_set_id}/{fname}",
            })
    return jsonify({"images": images})


def _build_campaign_image_map(set_id: str) -> dict:
    """
    扫描 images/<set_id>/ 目录，构建 campaign_id -> image URLs 的映射。

    文件名格式：{campaign_id}__{uuid}__{original_name}
    - 解析出 campaign_id 的归入对应 key
    - 解析不出的归入 "_all"
    """
    safe_set_id = secure_filename(set_id)
    image_dir = os.path.join(IMAGES_DIR, safe_set_id)
    if not os.path.isdir(image_dir):
        return {}

    image_map: dict = {}
    for fname in sorted(os.listdir(image_dir)):
        if not _allowed_image(fname):
            continue
        url = f"/api/campaign/image-file/{safe_set_id}/{fname}"
        parts = fname.split("__", 2)
        if len(parts) >= 3 and parts[0]:
            image_map.setdefault(parts[0], []).append(url)
        else:
            image_map.setdefault("_all", []).append(url)

    return image_map


@campaign_bp.route('/parse-brief', methods=['POST'])
@login_required
def parse_brief():
    """将自然语言 brief 解析为结构化 Campaign 字段"""
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": "请求体不能为空"}), 400

        brief_text = data.get("brief_text", "").strip()
        if not brief_text:
            return jsonify({"error": "brief_text 不能为空"}), 400

        product_line = data.get("product_line", "colored_lenses")
        if product_line not in ("colored_lenses", "moodyplus"):
            return jsonify({"error": "product_line 必须是 'colored_lenses' 或 'moodyplus'"}), 400

        parser = BriefParser()
        result = parser.parse(brief_text, product_line)
        return jsonify(result)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Brief 解析失败: {e}", exc_info=True)
        return jsonify({"error": f"内部错误: {str(e)}"}), 500


@campaign_bp.route('/evaluate', methods=['POST'])
@login_required
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
        category = data.get("category")  # None -> default personas, "moodyplus"/"colored_lenses" -> category-specific
        parent_set_id = data.get("parent_set_id")
        current_user = get_current_user()
        submitted_by = current_user["display_name"] if current_user else data.get("submitted_by", "")

        # Compute version by walking parent chain
        version = 1
        if parent_set_id:
            cursor = parent_set_id
            while cursor:
                version += 1
                parent_result = _load_result(cursor)
                if parent_result:
                    cursor = parent_result.get("parent_set_id")
                else:
                    break

        # 防重复 set_id：检查内存和磁盘是否已有该 set_id 的结果
        with _store_lock:
            in_memory = campaign_set.set_id in _evaluation_store
        if in_memory or _load_result(campaign_set.set_id):
            return jsonify({
                "error": f"set_id '{campaign_set.set_id}' 已存在，不允许覆盖已有评审结果"
            }), 409

        task_id = task_manager.create_task(
            "campaign_evaluation",
            metadata={
                "set_id": campaign_set.set_id,
                "submitted_by": submitted_by,
                "campaign_names": [c.name for c in campaign_set.campaigns],
                "campaign_count": len(campaign_set.campaigns),
                "submitted_at": datetime.now().strftime("%m/%d %H:%M"),
                "category": category,
                "parent_set_id": parent_set_id,
                "version": version,
            }
        )

        # Wrap save_result_fn to inject parent_set_id and version into saved result
        def _save_result_with_version(set_id: str, result: dict) -> None:
            if parent_set_id:
                result["parent_set_id"] = parent_set_id
            result["version"] = version
            _save_result(set_id, result)

        orchestrator = EvaluationOrchestrator(
            task_manager=task_manager,
            evaluation_store=_evaluation_store,
            save_result_fn=_save_result_with_version,
            store_lock=_store_lock,
        )
        thread = threading.Thread(
            target=orchestrator.run,
            args=(task_id, campaign_set, category),
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
@login_required
def evaluate_status(task_id: str):
    """查询评审任务进度"""
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    return jsonify(task.to_dict())


@campaign_bp.route('/result/<set_id>', methods=['GET'])
@login_required
def get_result(set_id: str):
    """获取评审结果，附带 campaign 图片 URL 映射"""
    with _store_lock:
        result = _evaluation_store.get(set_id)
    if not result:
        result = _load_result(set_id)
        if result:
            with _store_lock:
                _evaluation_store[set_id] = result
    if not result:
        return jsonify({"error": "评审结果不存在"}), 404

    # 注入图片 URL 映射，使前端可以展示 campaign 素材图
    response = dict(result)
    response["campaign_image_map"] = _build_campaign_image_map(set_id)
    return jsonify(response)


@campaign_bp.route('/export/<set_id>', methods=['GET'])
@login_required
def export_result(set_id: str):
    """导出评审结果为可下载的 JSON 文件"""
    with _store_lock:
        result = _evaluation_store.get(set_id)
    if not result:
        result = _load_result(set_id)
        if result:
            with _store_lock:
                _evaluation_store[set_id] = result
    if not result:
        return jsonify({"error": "评审结果不存在"}), 404

    current_user = get_current_user()
    export_payload = {
        "generated_at": datetime.now().isoformat(),
        "exported_by": current_user["display_name"] if current_user else "unknown",
        **result,
    }

    json_bytes = json.dumps(export_payload, ensure_ascii=False, indent=2)
    return Response(
        json_bytes,
        mimetype='application/json',
        headers={
            'Content-Disposition': f'attachment; filename=evaluation_{set_id}.json',
        },
    )


@campaign_bp.route('/resolve', methods=['POST'])
@login_required
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

        # 防重复结算：检查 set_id 是否已结算
        existing_resolutions = _calibration.load_resolutions()
        already_resolved = any(r["set_id"] == set_id for r in existing_resolutions)
        if already_resolved:
            return jsonify({"error": f"评审集 '{set_id}' 已结算，不允许重复结算"}), 409

        # 尝试从内存获取 predicted scores
        predicted = None
        with _store_lock:
            stored = _evaluation_store.get(set_id)
        if stored:
            board = stored.get("scoreboard", {})
            predicted = {
                c["campaign_id"]: c["overall_score"]
                for c in board.get("campaigns", [])
            }

        # 内存无数据时，回退到持久化的 predictions 文件
        if not predicted:
            preds_data = _calibration.load_predictions(set_id)
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
        resolutions = _calibration.load_resolutions()
        resolved_set_ids = set(r["set_id"] for r in resolutions)
        sets_with_preds = sum(
            1 for sid in resolved_set_ids
            if _calibration.load_predictions(sid) is not None
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
@login_required
def get_calibration():
    """查看 judge/persona 校准状态"""
    stats = _calibration.get_all_stats()
    resolutions = _calibration.load_resolutions()
    meta = _calibration.get_calibration_meta()

    # 去重计算已结算评审集数
    resolved_set_ids = set(r["set_id"] for r in resolutions)
    # 检查有多少评审集有预测数据
    sets_with_preds = sum(
        1 for sid in resolved_set_ids
        if _calibration.load_predictions(sid) is not None
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
@login_required
def recalibrate():
    """
    触发 judge/persona 校准

    POST /api/campaign/recalibrate
    无需请求体。
    """
    try:
        result = _calibration.recalibrate()
        return jsonify(result)
    except Exception as e:
        logger.error(f"校准失败: {e}", exc_info=True)
        return jsonify({"error": f"校准失败: {str(e)}"}), 500


@campaign_bp.route('/tasks', methods=['GET'])
@login_required
def list_tasks():
    """列出所有评审任务"""
    tasks = task_manager.list_tasks("campaign_evaluation")
    return jsonify({"tasks": tasks})


@campaign_bp.route('/tasks/<task_id>/cancel', methods=['POST'])
@login_required
def cancel_task(task_id: str):
    """手动取消一个卡住的任务"""
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
        return jsonify({"error": f"任务已结束 ({task.status.value})，无法取消"}), 400
    task_manager.fail_task(task_id, "用户手动取消")
    return jsonify({"status": "cancelled", "task_id": task_id})


@campaign_bp.route('/tasks/<task_id>/retry', methods=['POST'])
@login_required
def retry_task(task_id: str):
    """清除失败任务的旧结果，允许使用相同 set_id 重新提交"""
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({"error": "任务不存在"}), 404
    if task.status != TaskStatus.FAILED:
        return jsonify({"error": f"只能重试失败的任务，当前状态: {task.status.value}"}), 400

    set_id = task.metadata.get("set_id")
    if not set_id:
        return jsonify({"error": "任务缺少 set_id 元数据，无法重试"}), 400

    # 清除旧结果，允许重新提交
    with _store_lock:
        _evaluation_store.pop(set_id, None)
    result_path = os.path.join(_RESULTS_DIR, f"{set_id}.json")
    if os.path.exists(result_path):
        os.remove(result_path)

    task_manager.update_task(task_id, error="已标记可重试，请重新提交评审")
    return jsonify({
        "status": "retry_ready",
        "set_id": set_id,
        "message": "旧结果已清除，请使用相同 set_id 重新 POST /api/campaign/evaluate",
    })


@campaign_bp.route('/version-history/<set_id>', methods=['GET'])
@login_required
def version_history(set_id: str):
    """获取 campaign 版本链：从当前 set_id 追溯到根，再收集所有版本"""
    # Walk backwards to find root
    root_id = set_id
    visited = {set_id}
    cursor = set_id
    while True:
        result = _load_result(cursor)
        if not result:
            break
        parent = result.get("parent_set_id")
        if not parent or parent in visited:
            root_id = cursor
            break
        visited.add(parent)
        cursor = parent
    else:
        root_id = cursor

    # Build parent -> child index by scanning all result files
    parent_to_children: dict = {}
    all_results: dict = {}
    if os.path.isdir(_RESULTS_DIR):
        for fname in os.listdir(_RESULTS_DIR):
            if not fname.endswith('.json'):
                continue
            sid = fname[:-5]
            r = _load_result(sid)
            if r:
                all_results[sid] = r
                p = r.get("parent_set_id")
                if p:
                    parent_to_children.setdefault(p, []).append(sid)

    # Walk forward from root
    versions = []
    queue = [root_id]
    seen = set()
    while queue:
        sid = queue.pop(0)
        if sid in seen:
            continue
        seen.add(sid)
        r = all_results.get(sid) or _load_result(sid)
        if r:
            # Extract campaign names and overall scores from scoreboard
            sb = r.get("scoreboard", {})
            campaign_names = [c.get("campaign_name", "") for c in sb.get("campaigns", [])]
            overall_scores = {c.get("campaign_name", ""): c.get("overall_score", 0) for c in sb.get("campaigns", [])}
            versions.append({
                "set_id": sid,
                "version": r.get("version", 1),
                "created_at": r.get("created_at", ""),
                "campaign_names": campaign_names,
                "overall_scores": overall_scores,
            })
            # Add children to queue
            for child_id in parent_to_children.get(sid, []):
                queue.append(child_id)

    # Sort by version
    versions.sort(key=lambda v: v["version"])

    return jsonify({"versions": versions})


@campaign_bp.route('/compare', methods=['GET'])
@login_required
def compare_versions():
    """对比两个版本的评审结果，计算维度分数差异"""
    v1_id = request.args.get("v1")
    v2_id = request.args.get("v2")
    if not v1_id or not v2_id:
        return jsonify({"error": "需要 v1 和 v2 参数"}), 400

    r1 = _load_result(v1_id)
    r2 = _load_result(v2_id)
    if not r1:
        return jsonify({"error": f"结果 {v1_id} 不存在"}), 404
    if not r2:
        return jsonify({"error": f"结果 {v2_id} 不存在"}), 404

    sb1 = r1.get("scoreboard", {})
    sb2 = r2.get("scoreboard", {})

    # Build campaign name -> scores map for each version
    def _campaign_map(sb):
        return {
            c["campaign_name"]: c
            for c in sb.get("campaigns", [])
            if "campaign_name" in c
        }

    map1 = _campaign_map(sb1)
    map2 = _campaign_map(sb2)

    # Compute deltas for matching campaign names
    deltas = {}
    for name in set(map1.keys()) | set(map2.keys()):
        c1 = map1.get(name)
        c2 = map2.get(name)
        if c1 and c2:
            overall_delta = round(c2.get("overall_score", 0) - c1.get("overall_score", 0), 4)
            dim1 = c1.get("dimension_scores", {})
            dim2 = c2.get("dimension_scores", {})
            dimension_deltas = {}
            for dk in set(list(dim1.keys()) + list(dim2.keys())):
                d1 = dim1.get(dk, 0)
                d2 = dim2.get(dk, 0)
                dimension_deltas[dk] = round(d2 - d1, 4)
            deltas[name] = {
                "overall_delta": overall_delta,
                "dimension_deltas": dimension_deltas,
            }

    return jsonify({
        "v1": {"set_id": v1_id, "version": r1.get("version", 1), "scoreboard": sb1},
        "v2": {"set_id": v2_id, "version": r2.get("version", 1), "scoreboard": sb2},
        "deltas": deltas,
    })


@campaign_bp.route('/trends', methods=['GET'])
@login_required
def trends():
    """聚合所有历史评审结果，返回时间序列数据点，用于趋势图"""
    category_filter = request.args.get('category', 'all')
    if category_filter not in ('all', 'colored_lenses', 'moodyplus'):
        return jsonify({"error": "category 必须是 'all'、'colored_lenses' 或 'moodyplus'"}), 400

    if not os.path.isdir(_RESULTS_DIR):
        return jsonify({"data_points": [], "campaign_names": [], "category_filter": category_filter})

    data_points = []
    all_campaign_names: set = set()

    for fname in os.listdir(_RESULTS_DIR):
        if not fname.endswith('.json'):
            continue
        sid = fname[:-5]
        fpath = os.path.join(_RESULTS_DIR, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                result = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        # Determine category of this result
        result_category = None
        # Check top-level category key (set during evaluate submission via task metadata)
        if result.get("category"):
            result_category = result["category"]
        # Check metadata.category
        elif isinstance(result.get("metadata"), dict) and result["metadata"].get("category"):
            result_category = result["metadata"]["category"]
        else:
            # Infer from campaigns' product_line
            sb = result.get("scoreboard", {})
            campaigns = sb.get("campaigns", [])
            product_lines = set()
            for c in campaigns:
                pl = c.get("product_line")
                if pl:
                    product_lines.add(pl)
            if len(product_lines) == 1:
                result_category = product_lines.pop()

        # Apply category filter
        if category_filter != 'all':
            if result_category and result_category != category_filter:
                continue

        # Extract timestamp
        timestamp = result.get("created_at")
        if not timestamp:
            try:
                mtime = os.path.getmtime(fpath)
                timestamp = datetime.fromtimestamp(mtime).isoformat()
            except OSError:
                continue

        # Extract campaign scores from scoreboard
        sb = result.get("scoreboard", {})
        campaigns_data = sb.get("campaigns", [])
        if not campaigns_data:
            continue

        campaign_scores = {}
        for c in campaigns_data:
            name = c.get("campaign_name", "")
            score = c.get("overall_score", 0)
            if name:
                campaign_scores[name] = score
                all_campaign_names.add(name)

        if campaign_scores:
            data_points.append({
                "set_id": sid,
                "timestamp": timestamp,
                "campaigns": campaign_scores,
            })

    # Sort by timestamp ascending
    data_points.sort(key=lambda dp: dp["timestamp"])

    return jsonify({
        "data_points": data_points,
        "campaign_names": sorted(all_campaign_names),
        "category_filter": category_filter,
    })
