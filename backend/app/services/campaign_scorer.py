"""
Campaign Scoring Engine — market-aware 综合评分

输出：
- CampaignRanking (with verdict)
- ProbabilityBoard (win probabilities, sub-markets, spread, no_clear_edge)
"""

import os
from typing import List, Dict, Tuple
from collections import defaultdict

from ..utils.logger import get_logger
from ..models.campaign import Campaign
from ..models.evaluation import (
    PanelScore, PairwiseResult, CampaignRanking, Verdict,
)
from ..models.market import (
    ProbabilityBoard, CampaignMarketView, SubMarketProbability,
)
from .probability_aggregator import ProbabilityAggregator
from .submarket_evaluator import SubMarketEvaluator

logger = get_logger('ranker.campaign_scorer')

# Verdict 参数
SHIP_WIN_RATE = float(os.environ.get('SHIP_WIN_RATE', '0.6'))
SHIP_MAX_OBJECTION_DENSITY = float(os.environ.get('SHIP_MAX_OBJECTION_DENSITY', '4.0'))
KILL_PANEL_FLOOR = float(os.environ.get('KILL_PANEL_FLOOR', '2.5'))
KILL_LOSS_RATE = float(os.environ.get('KILL_LOSS_RATE', '0.8'))

# Market 参数
NO_TRADE_BAND = float(os.environ.get('NO_TRADE_BAND', '0.10'))
SHIP_MIN_PROBABILITY = float(os.environ.get('SHIP_MIN_PROBABILITY', '0.35'))


class CampaignScorer:
    """Market-aware 综合评分引擎"""

    def __init__(
        self,
        judge_weights: Dict[str, float] = None,
        persona_weights: Dict[str, float] = None,
    ):
        self.prob_aggregator = ProbabilityAggregator(
            judge_weights=judge_weights,
            persona_weights=persona_weights,
        )
        self.submarket_eval = SubMarketEvaluator()

    def score(
        self,
        campaigns: List[Campaign],
        panel_scores: List[PanelScore],
        pairwise_results: List[PairwiseResult],
        bt_scores: Dict[str, float],
    ) -> Tuple[List[CampaignRanking], ProbabilityBoard]:
        """
        综合评分，输出 (rankings, probability_board)。
        """
        campaign_map = {c.id: c for c in campaigns}
        n = len(campaigns)
        total_matchups = n - 1
        all_ids = [c.id for c in campaigns]

        # --- 基础统计 ---
        panel_by_campaign: Dict[str, List[PanelScore]] = defaultdict(list)
        for ps in panel_scores:
            panel_by_campaign[ps.campaign_id].append(ps)

        panel_avgs = {}
        for cid, scores in panel_by_campaign.items():
            panel_avgs[cid] = sum(s.score for s in scores) / len(scores)

        wins_count: Dict[str, int] = defaultdict(int)
        losses_count: Dict[str, int] = defaultdict(int)
        for pr in pairwise_results:
            if pr.winner_id:
                wins_count[pr.winner_id] += 1
                loser = pr.campaign_b_id if pr.winner_id == pr.campaign_a_id else pr.campaign_a_id
                losses_count[loser] += 1

        objection_density: Dict[str, float] = {}
        for cid, scores in panel_by_campaign.items():
            total_obj = sum(len(s.objections) for s in scores)
            objection_density[cid] = total_obj / len(scores) if scores else 0

        # --- Win probabilities ---
        win_probs = self.prob_aggregator.aggregate(
            campaigns, panel_scores, pairwise_results, bt_scores,
        )

        # --- Sub-markets ---
        sub_market_results = self.submarket_eval.evaluate(campaigns, panel_scores)

        # 按 campaign 分组子市场概率
        sub_by_campaign: Dict[str, Dict[str, float]] = defaultdict(dict)
        for sm in sub_market_results:
            sub_by_campaign[sm.campaign_id][sm.market_key] = sm.probability

        # --- 排序 by win_probability ---
        sorted_ids = sorted(all_ids, key=lambda cid: win_probs.get(cid, 0), reverse=True)

        # --- Spread ---
        sorted_probs = [win_probs.get(cid, 0) for cid in sorted_ids]
        spread = (sorted_probs[0] - sorted_probs[1]) if len(sorted_probs) >= 2 else 1.0
        no_clear_edge = spread < NO_TRADE_BAND

        # --- Verdict (market-aware) ---
        rankings = []
        market_views = []

        for rank, cid in enumerate(sorted_ids, 1):
            scores_for = panel_by_campaign.get(cid, [])
            all_objections = [o for s in scores_for for o in s.objections]
            all_strengths = [si for s in scores_for for si in s.strengths]
            top_obj = list(dict.fromkeys(all_objections))[:3]
            top_str = list(dict.fromkeys(all_strengths))[:3]

            wins = wins_count.get(cid, 0)
            losses = losses_count.get(cid, 0)
            panel_avg = panel_avgs.get(cid, 0)
            obj_density = objection_density.get(cid, 0)
            win_prob = win_probs.get(cid, 0)
            win_rate = wins / total_matchups if total_matchups > 0 else 0
            loss_rate = losses / total_matchups if total_matchups > 0 else 0

            # Spread to next
            if rank < n:
                next_cid = sorted_ids[rank]  # rank is 1-based, index is rank
                spread_to_next = win_prob - win_probs.get(next_cid, 0)
            else:
                spread_to_next = None

            verdict, rationale = self._decide_verdict(
                rank=rank, n=n,
                win_rate=win_rate, loss_rate=loss_rate,
                panel_avg=panel_avg, obj_density=obj_density,
                win_prob=win_prob, spread=spread,
                no_clear_edge=no_clear_edge,
            )

            rankings.append(CampaignRanking(
                campaign_id=cid,
                campaign_name=campaign_map[cid].name,
                rank=rank,
                composite_score=win_prob * 10,  # scale to 0-10 for backward compat
                panel_avg=panel_avg,
                pairwise_wins=wins,
                pairwise_losses=losses,
                verdict=verdict,
                top_objections=top_obj,
                top_strengths=top_str,
            ))

            market_views.append(CampaignMarketView(
                campaign_id=cid,
                campaign_name=campaign_map[cid].name,
                win_probability=win_prob,
                sub_markets=dict(sub_by_campaign.get(cid, {})),
                rank=rank,
                verdict=verdict.value,
                spread_to_next=spread_to_next,
                verdict_rationale=rationale,
            ))

        # --- Uncertainty rationale ---
        if no_clear_edge:
            rationale_uncertainty = (
                f"前两名概率差距仅 {spread:.1%}，低于 no-trade 阈值 {NO_TRADE_BAND:.0%}。"
                f"建议进一步优化方案或收集更多信号后再做决策。"
            )
        else:
            rationale_uncertainty = (
                f"排名第一的方案概率领先 {spread:.1%}，具有一定优势。"
            )

        board = ProbabilityBoard(
            campaigns=market_views,
            spread=spread,
            no_clear_edge=no_clear_edge,
            no_trade_band=NO_TRADE_BAND,
            rationale_for_uncertainty=rationale_uncertainty,
            sub_markets=sub_market_results,
        )

        return rankings, board

    @staticmethod
    def _decide_verdict(
        rank: int, n: int,
        win_rate: float, loss_rate: float,
        panel_avg: float, obj_density: float,
        win_prob: float, spread: float,
        no_clear_edge: bool,
    ) -> Tuple[Verdict, str]:
        """
        Market-aware verdict:
        - 新增 spread / win_prob 条件
        - no_clear_edge 时 #1 只能 REVISE
        """
        # KILL: 绝对分过低
        if panel_avg < KILL_PANEL_FLOOR:
            return Verdict.KILL, f"Panel 均分 {panel_avg:.1f} 低于下限 {KILL_PANEL_FLOOR}"

        # KILL: 末位 + 持续败北
        if rank == n and loss_rate >= KILL_LOSS_RATE:
            return Verdict.KILL, f"末位且败率 {loss_rate:.0%} ≥ {KILL_LOSS_RATE:.0%}"

        # SHIP 条件: 排名第一 + 有明确优势 + 胜率足够
        if rank == 1:
            if no_clear_edge:
                return Verdict.REVISE, (
                    f"排名第一但与第二名差距仅 {spread:.1%}，"
                    f"低于 no-trade 阈值 {NO_TRADE_BAND:.0%}，建议优化后再 ship"
                )
            if win_rate < SHIP_WIN_RATE:
                return Verdict.REVISE, f"排名第一但 pairwise 胜率仅 {win_rate:.0%}"
            if obj_density > SHIP_MAX_OBJECTION_DENSITY:
                return Verdict.REVISE, f"排名第一但 objection 密度 {obj_density:.1f} 过高"
            if win_prob < SHIP_MIN_PROBABILITY:
                return Verdict.REVISE, f"排名第一但 win probability {win_prob:.1%} 偏低"
            return Verdict.SHIP, (
                f"排名第一，概率 {win_prob:.1%}，领先 {spread:.1%}，"
                f"pairwise 胜率 {win_rate:.0%}"
            )

        return Verdict.REVISE, f"排名 #{rank}，有优化空间"
