"""
Judge Calibration Framework — 校准 judge/persona 权重

完整闭环：
1. 评审阶段：save_predictions() 持久化 per-persona/per-judge 原始预测
2. 结算阶段：record_resolution() 记录真实赢家
3. 校准阶段：recalibrate() 对比预测 vs 真实，计算 Brier/log-loss，更新权重
4. 下次评审：get_weights() 读取校准后权重，影响评分聚合

数据存储：
- predictions/{set_id}.json — 每次评审的原始预测
- resolutions.jsonl — 结算记录
- judge_stats.json — 校准统计 + 权重
"""

import math
import json
import os
from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from datetime import datetime

from ..utils.logger import get_logger
from ..models.market import JudgePerformanceStats, ResolutionRecord

logger = get_logger('ranker.calibration')

# 校准数据存储路径
CALIBRATION_DIR = os.path.join(os.path.dirname(__file__), '../../uploads/calibration')

# 最低结算数要求
MIN_RESOLUTIONS = 5


class JudgeCalibration:
    """Judge/Persona 校准引擎"""

    def __init__(self, calibration_dir: str = CALIBRATION_DIR):
        self.calibration_dir = calibration_dir
        os.makedirs(self.calibration_dir, exist_ok=True)
        self._predictions_dir = os.path.join(self.calibration_dir, 'predictions')
        os.makedirs(self._predictions_dir, exist_ok=True)

    # ================================================================
    # Phase 5.1: 持久化 per-persona / per-judge 预测
    # ================================================================

    def save_predictions(
        self,
        set_id: str,
        persona_predictions: List[Dict],
        judge_predictions: List[Dict],
        campaign_win_probabilities: Dict[str, float],
    ) -> None:
        """
        持久化一次评审的原始预测数据。

        Args:
            set_id: 评审集 ID
            persona_predictions: [
                {persona_id, campaign_id, score, preference}
            ]
                preference = score / sum(scores_for_this_persona) 归一化
            judge_predictions: [
                {judge_id, campaign_a_id, campaign_b_id, winner_pick, dimensions}
            ]
            campaign_win_probabilities: {campaign_id: probability}
        """
        path = os.path.join(self._predictions_dir, f'{set_id}.json')
        data = {
            "set_id": set_id,
            "saved_at": datetime.now().isoformat(),
            "persona_predictions": persona_predictions,
            "judge_predictions": judge_predictions,
            "campaign_win_probabilities": campaign_win_probabilities,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(
            f"Predictions saved: set={set_id}, "
            f"persona={len(persona_predictions)}, judge={len(judge_predictions)}"
        )

    def load_predictions(self, set_id: str) -> Optional[Dict]:
        """加载某次评审的预测数据"""
        path = os.path.join(self._predictions_dir, f'{set_id}.json')
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # ================================================================
    # 权重获取
    # ================================================================

    def get_weights(self) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        获取当前 judge 和 persona 权重。
        有校准历史时基于 Brier score 计算权重。
        无历史数据时返回空 dict（意味着全部使用默认均等权重）。
        """
        stats = self._load_stats()
        if not stats:
            return {}, {}

        judge_weights = {}
        persona_weights = {}

        for stat in stats:
            if stat.brier_score is not None and stat.total_predictions > 0:
                weight = 1.0 / (1.0 + stat.brier_score)
            else:
                weight = 1.0

            if stat.judge_type == "judge":
                judge_weights[stat.judge_id] = weight
            elif stat.judge_type == "persona":
                persona_weights[stat.judge_id] = weight

        return judge_weights, persona_weights

    def get_all_stats(self) -> List[JudgePerformanceStats]:
        """获取所有 judge/persona 的校准统计"""
        return self._load_stats()

    # ================================================================
    # 结算记录
    # ================================================================

    def record_resolution(self, record: ResolutionRecord) -> None:
        """记录一次赛后结算"""
        path = os.path.join(self.calibration_dir, 'resolutions.jsonl')
        entry = {
            "set_id": record.set_id,
            "campaign_id": record.campaign_id,
            "resolved_at": record.resolved_at,
            "actual_metrics": record.actual_metrics,
            "predicted_win_prob": record.predicted_win_prob,
            "was_actual_winner": record.was_actual_winner,
            "notes": record.notes,
        }
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        logger.info(f"Resolution recorded: set={record.set_id}, campaign={record.campaign_id}")

    def load_resolutions(self) -> List[Dict]:
        """加载所有结算记录"""
        path = os.path.join(self.calibration_dir, 'resolutions.jsonl')
        if not os.path.exists(path):
            return []
        records = []
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    # ================================================================
    # Phase 5.2: 真正的 recalibrate
    # ================================================================

    def recalibrate(self) -> Dict:
        """
        基于历史结算 + 历史预测数据重新校准所有 judge/persona。

        算法：
        1. 找到所有已结算的 set_id（去重）
        2. 对每个 set_id 加载 predictions
        3. 对每个 persona：
           - 取该 persona 对各 campaign 的 preference（归一化评分）
           - actual outcome = 1 if campaign is winner, else 0
           - 收集 (prediction, outcome) 对
        4. 对每个 judge：
           - 取该 judge 对每个 matchup 的投票
           - 如果 judge 选了 A，prediction = 1.0 for A winning this matchup
           - actual = 1 if A was the set winner side, else 0
           - 收集 (prediction, outcome) 对
        5. 计算 Brier score, log loss, calibration buckets
        6. 权重 = 1 / (1 + brier_score)
        7. 保存 judge_stats.json

        Returns:
            {
                "status": "calibrated" | "insufficient_data" | "no_predictions",
                "stats_count": int,
                "resolved_sets": int,
                "message": str,
                "calibrated_at": str | None,
            }
        """
        resolutions = self.load_resolutions()

        # 找有 resolution 的 unique set_ids
        resolved_sets = {}
        for r in resolutions:
            sid = r["set_id"]
            if sid not in resolved_sets:
                resolved_sets[sid] = {"winner": None, "campaigns": []}
            resolved_sets[sid]["campaigns"].append(r["campaign_id"])
            if r.get("was_actual_winner"):
                resolved_sets[sid]["winner"] = r["campaign_id"]

        # 统计有预测数据的评审集数（这是真正的门槛）
        sets_with_preds_count = sum(
            1 for sid in resolved_sets
            if self.load_predictions(sid) is not None
        )

        if sets_with_preds_count < MIN_RESOLUTIONS:
            if len(resolved_sets) >= MIN_RESOLUTIONS and sets_with_preds_count < MIN_RESOLUTIONS:
                msg = (
                    f"已有 {len(resolved_sets)} 个评审集结算，"
                    f"但仅 {sets_with_preds_count} 个有预测数据。"
                    f"还需 {MIN_RESOLUTIONS - sets_with_preds_count} 个有预测数据的评审集"
                )
            else:
                msg = (
                    f"需要至少 {MIN_RESOLUTIONS} 个有预测数据的评审集，"
                    f"当前 {sets_with_preds_count} 个"
                )
            logger.info(f"校准条件不足: {msg}")
            return {
                "status": "insufficient_data",
                "stats_count": 0,
                "resolved_sets": len(resolved_sets),
                "sets_with_predictions": sets_with_preds_count,
                "message": msg,
                "calibrated_at": None,
            }

        # 收集每个 persona/judge 的 (prediction, outcome) 对
        persona_samples: Dict[str, Dict] = defaultdict(
            lambda: {"predictions": [], "outcomes": []}
        )
        judge_samples: Dict[str, Dict] = defaultdict(
            lambda: {"predictions": [], "outcomes": []}
        )

        sets_with_predictions = 0
        judge_matchups_used = 0
        judge_matchups_skipped = 0

        for set_id, info in resolved_sets.items():
            winner_id = info["winner"]
            if not winner_id:
                continue

            preds = self.load_predictions(set_id)
            if not preds:
                logger.debug(f"set={set_id} 无预测数据，跳过")
                continue

            sets_with_predictions += 1

            # --- Persona calibration (完整覆盖) ---
            for pp in preds.get("persona_predictions", []):
                persona_id = pp["persona_id"]
                campaign_id = pp["campaign_id"]
                preference = pp.get("preference", 0.5)
                is_winner = campaign_id == winner_id
                persona_samples[persona_id]["predictions"].append(preference)
                persona_samples[persona_id]["outcomes"].append(is_winner)

            # --- Judge calibration (partial: 只覆盖包含 set winner 的 matchup) ---
            for jp in preds.get("judge_predictions", []):
                judge_id = jp["judge_id"]
                a_id = jp["campaign_a_id"]
                b_id = jp["campaign_b_id"]
                winner_pick = jp.get("winner_pick", "tie")

                if winner_pick == "A":
                    judge_prob_a = 1.0
                elif winner_pick == "B":
                    judge_prob_a = 0.0
                else:
                    judge_prob_a = 0.5

                # actual: did A end up being the set winner?
                if winner_id == a_id:
                    actual_a = True
                elif winner_id == b_id:
                    actual_a = False
                else:
                    # winner 不在此 matchup 中 → 无法确定 ground truth → 跳过
                    judge_matchups_skipped += 1
                    continue

                judge_matchups_used += 1
                judge_samples[judge_id]["predictions"].append(judge_prob_a)
                judge_samples[judge_id]["outcomes"].append(actual_a)

        if sets_with_predictions == 0:
            logger.info("所有已结算评审集都没有预测数据，无法校准")
            return {
                "status": "no_predictions",
                "stats_count": 0,
                "resolved_sets": len(resolved_sets),
                "message": "已结算评审集没有保存预测数据（Phase 5.1 之前的评审）",
                "calibrated_at": None,
            }

        # --- 计算校准指标 ---
        all_stats = []

        for persona_id, samples in persona_samples.items():
            preds = samples["predictions"]
            outcomes = samples["outcomes"]
            if not preds:
                continue
            brier = self.compute_brier_score(preds, outcomes)
            ll = self.compute_log_loss(preds, outcomes)
            buckets = self.calibration_buckets(preds, outcomes)
            weight = 1.0 / (1.0 + brier)

            all_stats.append(JudgePerformanceStats(
                judge_id=persona_id,
                judge_type="persona",
                total_predictions=len(preds),
                brier_score=brier,
                log_loss=ll,
                calibration_buckets=buckets,
                weight=weight,
            ))

        for judge_id, samples in judge_samples.items():
            preds = samples["predictions"]
            outcomes = samples["outcomes"]
            if not preds:
                continue
            brier = self.compute_brier_score(preds, outcomes)
            ll = self.compute_log_loss(preds, outcomes)
            buckets = self.calibration_buckets(preds, outcomes)
            weight = 1.0 / (1.0 + brier)

            all_stats.append(JudgePerformanceStats(
                judge_id=judge_id,
                judge_type="judge",
                total_predictions=len(preds),
                brier_score=brier,
                log_loss=ll,
                calibration_buckets=buckets,
                weight=weight,
            ))

        # --- 计算 judge calibration 覆盖率 ---
        persona_count = sum(1 for s in all_stats if s.judge_type == "persona")
        judge_count = sum(1 for s in all_stats if s.judge_type == "judge")
        total_judge_matchups = judge_matchups_used + judge_matchups_skipped

        judge_note = (
            "complete" if judge_matchups_skipped == 0
            else (
                f"partial — 仅校准包含 set winner 的 matchup "
                f"({judge_matchups_used}/{total_judge_matchups}, "
                f"跳过 {judge_matchups_skipped} 个无 ground truth 的 matchup)"
            )
        )

        # 保存
        self._save_stats(all_stats)
        now = datetime.now().isoformat()
        self._save_calibration_meta(
            now, len(resolved_sets), sets_with_predictions,
            judge_calibration=judge_note,
            persona_calibration="complete",
        )

        logger.info(
            f"校准完成: persona={persona_count}, judge={judge_count} ({judge_note}), "
            f"基于 {sets_with_predictions}/{len(resolved_sets)} 个有预测数据的评审集"
        )

        return {
            "status": "calibrated",
            "stats_count": len(all_stats),
            "resolved_sets": len(resolved_sets),
            "sets_with_predictions": sets_with_predictions,
            "persona_calibration": "complete",
            "judge_calibration": judge_note,
            "judge_matchups_used": judge_matchups_used,
            "judge_matchups_skipped": judge_matchups_skipped,
            "message": (
                f"校准完成，{persona_count} persona (complete) + "
                f"{judge_count} judge ({judge_note})，"
                f"基于 {sets_with_predictions} 个评审集"
            ),
            "calibrated_at": now,
        }

    # ================================================================
    # 校准元数据
    # ================================================================

    def get_calibration_meta(self) -> Dict:
        """获取上次校准的元数据"""
        path = os.path.join(self.calibration_dir, 'calibration_meta.json')
        if not os.path.exists(path):
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_calibration_meta(
        self, calibrated_at: str, resolved_sets: int, sets_with_predictions: int,
        judge_calibration: str = "not_run",
        persona_calibration: str = "not_run",
    ) -> None:
        path = os.path.join(self.calibration_dir, 'calibration_meta.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({
                "last_calibrated_at": calibrated_at,
                "resolved_sets": resolved_sets,
                "sets_with_predictions": sets_with_predictions,
                "judge_calibration": judge_calibration,
                "persona_calibration": persona_calibration,
            }, f, ensure_ascii=False, indent=2)

    # ================================================================
    # 静态工具方法
    # ================================================================

    @staticmethod
    def compute_brier_score(
        predictions: List[float],
        outcomes: List[bool],
    ) -> float:
        """Brier Score = (1/N) * sum((p_i - o_i)^2)"""
        if not predictions:
            return 0.0
        n = len(predictions)
        return sum(
            (p - (1.0 if o else 0.0)) ** 2
            for p, o in zip(predictions, outcomes)
        ) / n

    @staticmethod
    def compute_log_loss(
        predictions: List[float],
        outcomes: List[bool],
        eps: float = 1e-7,
    ) -> float:
        """Log Loss = -(1/N) * sum(o*log(p) + (1-o)*log(1-p))"""
        if not predictions:
            return 0.0
        n = len(predictions)
        total = 0.0
        for p, o in zip(predictions, outcomes):
            p_clipped = max(eps, min(1 - eps, p))
            if o:
                total -= math.log(p_clipped)
            else:
                total -= math.log(1 - p_clipped)
        return total / n

    @staticmethod
    def calibration_buckets(
        predictions: List[float],
        outcomes: List[bool],
        n_buckets: int = 5,
    ) -> Dict[str, Dict[str, float]]:
        """按预测概率分桶，计算 predicted_avg vs actual_avg"""
        if not predictions:
            return {}
        buckets: Dict[str, list] = {}
        step = 1.0 / n_buckets
        for p, o in zip(predictions, outcomes):
            bucket_idx = min(int(p / step), n_buckets - 1)
            lo = round(bucket_idx * step, 2)
            hi = round((bucket_idx + 1) * step, 2)
            key = f"{lo}-{hi}"
            if key not in buckets:
                buckets[key] = {"preds": [], "outcomes": []}
            buckets[key]["preds"].append(p)
            buckets[key]["outcomes"].append(1.0 if o else 0.0)

        result = {}
        for key, data in sorted(buckets.items()):
            preds = data["preds"]
            outs = data["outcomes"]
            result[key] = {
                "predicted_avg": round(sum(preds) / len(preds), 4),
                "actual_avg": round(sum(outs) / len(outs), 4),
                "count": len(preds),
            }
        return result

    # ================================================================
    # 内部存储
    # ================================================================

    def _load_stats(self) -> List[JudgePerformanceStats]:
        path = os.path.join(self.calibration_dir, 'judge_stats.json')
        if not os.path.exists(path):
            return []
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [
            JudgePerformanceStats(**item)
            for item in data
        ]

    def _save_stats(self, stats: List[JudgePerformanceStats]) -> None:
        path = os.path.join(self.calibration_dir, 'judge_stats.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump([s.to_dict() for s in stats], f, ensure_ascii=False, indent=2)
