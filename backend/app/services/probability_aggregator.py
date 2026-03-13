"""
Probability Aggregator — 从 panel/pairwise/objection 信号聚合胜出概率

核心思路：
- 概率 = 模型内相对胜率，不是真实世界概率
- 聚合三路信号：BT strength, panel average, objection penalty
- 权重可配置，支持 judge calibration 覆盖
- 输出归一化到 sum=1 的概率分布

Phase 5.3 更新：
- judge_weights 真正作用于 pairwise 信号：
  按 judge_weight 加权投票重算 BT，而非使用等权 BT
"""

import os
import math
from typing import List, Dict, Optional
from collections import defaultdict

from ..utils.logger import get_logger
from ..models.campaign import Campaign
from ..models.evaluation import PanelScore, PairwiseResult

logger = get_logger('ranker.probability')

# 信号权重
W_PAIRWISE = float(os.environ.get('PROB_W_PAIRWISE', '0.45'))
W_PANEL = float(os.environ.get('PROB_W_PANEL', '0.35'))
W_OBJECTION = float(os.environ.get('PROB_W_OBJECTION', '0.20'))


def _softmax(values: Dict[str, float], temperature: float = 1.0) -> Dict[str, float]:
    """Softmax 归一化到概率分布。temperature 越低越极端。"""
    if not values:
        return {}
    max_v = max(values.values())
    exp_vals = {k: math.exp((v - max_v) / temperature) for k, v in values.items()}
    total = sum(exp_vals.values())
    if total == 0:
        n = len(values)
        return {k: 1.0 / n for k in values}
    return {k: v / total for k, v in exp_vals.items()}


class ProbabilityAggregator:
    """概率聚合器"""

    def __init__(
        self,
        judge_weights: Optional[Dict[str, float]] = None,
        persona_weights: Optional[Dict[str, float]] = None,
    ):
        self.judge_weights = judge_weights or {}
        self.persona_weights = persona_weights or {}

    def aggregate(
        self,
        campaigns: List[Campaign],
        panel_scores: List[PanelScore],
        pairwise_results: List[PairwiseResult],
        bt_scores: Dict[str, float],
    ) -> Dict[str, float]:
        """
        聚合三路信号，输出 campaign_id → win_probability (sum=1)。

        judge_weights 通过重算加权 BT 生效：
        - 如果 judge_weights 非空，从 pairwise_results.votes 重算
        - 否则使用原始 bt_scores
        """
        all_ids = [c.id for c in campaigns]
        if not all_ids:
            return {}

        # --- Signal 1: BT pairwise strength ---
        # 如果有 judge_weights，重算加权 BT
        if self.judge_weights and pairwise_results:
            weighted_bt = self._weighted_bradley_terry(all_ids, pairwise_results)
            bt_for_softmax = weighted_bt
        else:
            bt_for_softmax = {cid: bt_scores.get(cid, 1.0) for cid in all_ids}

        bt_probs = _softmax(bt_for_softmax, temperature=1.0)

        # --- Signal 2: Weighted panel average ---
        panel_by_campaign: Dict[str, List[PanelScore]] = defaultdict(list)
        for ps in panel_scores:
            panel_by_campaign[ps.campaign_id].append(ps)

        panel_signal = {}
        for cid in all_ids:
            scores = panel_by_campaign.get(cid, [])
            if not scores:
                panel_signal[cid] = 5.0
                continue
            weighted_sum = 0.0
            weight_sum = 0.0
            for s in scores:
                w = self.persona_weights.get(s.persona_id, 1.0)
                weighted_sum += s.score * w
                weight_sum += w
            panel_signal[cid] = weighted_sum / weight_sum if weight_sum > 0 else 5.0

        panel_probs = _softmax(panel_signal, temperature=2.0)

        # --- Signal 3: Objection penalty (inverted) ---
        obj_signal = {}
        for cid in all_ids:
            scores = panel_by_campaign.get(cid, [])
            if not scores:
                obj_signal[cid] = 5.0
                continue
            total_obj = sum(len(s.objections) for s in scores)
            density = total_obj / len(scores)
            obj_signal[cid] = max(0.0, 10.0 - density)

        obj_probs = _softmax(obj_signal, temperature=2.0)

        # --- Blend ---
        blended = {}
        for cid in all_ids:
            blended[cid] = (
                W_PAIRWISE * bt_probs.get(cid, 0)
                + W_PANEL * panel_probs.get(cid, 0)
                + W_OBJECTION * obj_probs.get(cid, 0)
            )

        # Re-normalize to sum=1
        total = sum(blended.values())
        if total > 0:
            return {cid: v / total for cid, v in blended.items()}
        n = len(all_ids)
        return {cid: 1.0 / n for cid in all_ids}

    def _weighted_bradley_terry(
        self,
        all_ids: List[str],
        pairwise_results: List[PairwiseResult],
        iterations: int = 20,
    ) -> Dict[str, float]:
        """
        从 pairwise_results 的 votes 重算 BT，按 judge_weight 加权。

        每个 judge 的投票贡献 = judge_weight（默认 1.0）。
        例如 calibration 后某 judge 权重 0.8，其投票贡献从 1.0 降到 0.8。
        """
        n = len(all_ids)
        wins = {i: {j: 0.0 for j in all_ids} for i in all_ids}

        for pr in pairwise_results:
            a_id = pr.campaign_a_id
            b_id = pr.campaign_b_id

            if not pr.votes:
                # 没有 per-judge votes，退回到 winner_id
                if pr.winner_id == a_id:
                    wins[a_id][b_id] += 1.0
                elif pr.winner_id == b_id:
                    wins[b_id][a_id] += 1.0
                else:
                    wins[a_id][b_id] += 0.5
                    wins[b_id][a_id] += 0.5
                continue

            for vote in pr.votes:
                judge_id = vote.get("judge_id", "")
                w = self.judge_weights.get(judge_id, 1.0)
                winner_pick = vote.get("winner", "tie")

                if winner_pick == "A":
                    wins[a_id][b_id] += w
                elif winner_pick == "B":
                    wins[b_id][a_id] += w
                else:
                    wins[a_id][b_id] += w * 0.5
                    wins[b_id][a_id] += w * 0.5

        # BT iteration
        strength = {i: 1.0 for i in all_ids}
        for _ in range(iterations):
            new_strength = {}
            for i in all_ids:
                numerator = sum(wins[i][j] for j in all_ids if j != i)
                denominator = sum(
                    (wins[i][j] + wins[j][i]) / (strength[i] + strength[j])
                    for j in all_ids if j != i
                ) if n > 1 else 1.0
                new_strength[i] = numerator / denominator if denominator > 0 else 1.0
            total = sum(new_strength.values())
            strength = {i: v / total * n for i, v in new_strength.items()}

        return strength
