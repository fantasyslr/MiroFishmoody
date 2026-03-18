"""
Campaign Scoring Engine — 综合评分

输出：
- CampaignRanking (with verdict)
- ScoreBoard (overall scores, dimension scores, lead_margin, too_close_to_call)
"""

import os
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

from ..utils.logger import get_logger
from ..models.campaign import Campaign, BriefType
from ..models.evaluation import (
    PanelScore, PairwiseResult, CampaignRanking, Verdict,
)
from ..models.scoreboard import (
    ScoreBoard, CampaignScoreView, DimensionScore,
)
from .probability_aggregator import ProbabilityAggregator
from .submarket_evaluator import DimensionEvaluator
from ..models.agent_score import AgentScore

logger = get_logger('ranker.campaign_scorer')

# Verdict 参数
SHIP_WIN_RATE = float(os.environ.get('SHIP_WIN_RATE', '0.6'))
SHIP_MAX_OBJECTION_DENSITY = float(os.environ.get('SHIP_MAX_OBJECTION_DENSITY', '4.0'))
KILL_PANEL_FLOOR = float(os.environ.get('KILL_PANEL_FLOOR', '2.5'))
KILL_LOSS_RATE = float(os.environ.get('KILL_LOSS_RATE', '0.8'))

# Scoring 参数
CONFIDENCE_THRESHOLD = float(os.environ.get('CONFIDENCE_THRESHOLD', '0.10'))
SHIP_MIN_SCORE = float(os.environ.get('SHIP_MIN_SCORE', '0.35'))

# Agent score 混入权重（0-1，越大表示 agent 贡献占比越高）
AGENT_SCORE_WEIGHT = float(os.environ.get('AGENT_SCORE_WEIGHT', '0.1'))


class CampaignScorer:
    """综合评分引擎"""

    def __init__(
        self,
        judge_weights: Dict[str, float] = None,
        persona_weights: Dict[str, float] = None,
        brief_type: Optional[BriefType] = None,
    ):
        self.prob_aggregator = ProbabilityAggregator(
            judge_weights=judge_weights,
            persona_weights=persona_weights,
        )
        self.dimension_eval = DimensionEvaluator()
        self.brief_type = brief_type

    def score(
        self,
        campaigns: List[Campaign],
        panel_scores: List[PanelScore],
        pairwise_results: List[PairwiseResult],
        bt_scores: Dict[str, float],
        agent_scores: Optional[List[AgentScore]] = None,
    ) -> Tuple[List[CampaignRanking], ScoreBoard]:
        """
        综合评分，输出 (rankings, scoreboard)。
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

        # --- Overall scores ---
        scores = self.prob_aggregator.aggregate(
            campaigns, panel_scores, pairwise_results, bt_scores,
        )

        # --- Agent score contribution (optional) ---
        if agent_scores:
            agent_by_campaign: Dict[str, List[AgentScore]] = defaultdict(list)
            for a in agent_scores:
                agent_by_campaign[a.campaign_id].append(a)
            for cid, a_list in agent_by_campaign.items():
                if cid not in scores:
                    continue
                total_weight = sum(a.weight for a in a_list)
                if total_weight <= 0:
                    continue
                weighted_contrib = sum(a.score * a.weight for a in a_list) / total_weight
                scores[cid] = (
                    scores[cid] * (1.0 - AGENT_SCORE_WEIGHT)
                    + weighted_contrib * AGENT_SCORE_WEIGHT
                )

        # --- Dimension scores ---
        dimension_results = self.dimension_eval.evaluate(
            campaigns, panel_scores, brief_type=self.brief_type
        )

        # 按 campaign 分组维度得分
        dim_by_campaign: Dict[str, Dict[str, float]] = defaultdict(dict)
        for ds in dimension_results:
            dim_by_campaign[ds.campaign_id][ds.dimension_key] = ds.score

        # --- 排序 by overall_score ---
        sorted_ids = sorted(all_ids, key=lambda cid: scores.get(cid, 0), reverse=True)

        # --- Lead margin ---
        sorted_scores = [scores.get(cid, 0) for cid in sorted_ids]
        lead_margin = (sorted_scores[0] - sorted_scores[1]) if len(sorted_scores) >= 2 else 1.0
        too_close_to_call = lead_margin < CONFIDENCE_THRESHOLD

        # --- Verdict ---
        rankings = []
        score_views = []

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
            overall_score = scores.get(cid, 0)
            win_rate = wins / total_matchups if total_matchups > 0 else 0
            loss_rate = losses / total_matchups if total_matchups > 0 else 0

            # Lead margin to next
            if rank < n:
                next_cid = sorted_ids[rank]  # rank is 1-based, index is rank
                lead_margin_to_next = overall_score - scores.get(next_cid, 0)
            else:
                lead_margin_to_next = None

            verdict, rationale = self._decide_verdict(
                rank=rank, n=n,
                win_rate=win_rate, loss_rate=loss_rate,
                panel_avg=panel_avg, obj_density=obj_density,
                overall_score=overall_score, lead_margin=lead_margin,
                too_close_to_call=too_close_to_call,
            )

            rankings.append(CampaignRanking(
                campaign_id=cid,
                campaign_name=campaign_map[cid].name,
                rank=rank,
                composite_score=overall_score * 10,  # scale to 0-10 for backward compat
                panel_avg=panel_avg,
                pairwise_wins=wins,
                pairwise_losses=losses,
                verdict=verdict,
                top_objections=top_obj,
                top_strengths=top_str,
            ))

            score_views.append(CampaignScoreView(
                campaign_id=cid,
                campaign_name=campaign_map[cid].name,
                overall_score=overall_score,
                dimension_scores=dict(dim_by_campaign.get(cid, {})),
                rank=rank,
                verdict=verdict.value,
                lead_margin_to_next=lead_margin_to_next,
                verdict_rationale=rationale,
            ))

        # --- Uncertainty rationale ---
        if too_close_to_call:
            rationale_uncertainty = (
                f"前两名得分差距仅 {lead_margin:.1%}，低于置信阈值 {CONFIDENCE_THRESHOLD:.0%}。"
                f"建议进一步优化方案或收集更多信号后再做决策。"
            )
        else:
            rationale_uncertainty = (
                f"排名第一的方案得分领先 {lead_margin:.1%}，具有一定优势。"
            )

        board = ScoreBoard(
            campaigns=score_views,
            lead_margin=lead_margin,
            too_close_to_call=too_close_to_call,
            confidence_threshold=CONFIDENCE_THRESHOLD,
            rationale_for_uncertainty=rationale_uncertainty,
            dimension_scores=dimension_results,
        )

        return rankings, board

    @staticmethod
    def _decide_verdict(
        rank: int, n: int,
        win_rate: float, loss_rate: float,
        panel_avg: float, obj_density: float,
        overall_score: float, lead_margin: float,
        too_close_to_call: bool,
    ) -> Tuple[Verdict, str]:
        """
        Verdict 决策:
        - 新增 lead_margin / overall_score 条件
        - too_close_to_call 时 #1 只能 REVISE
        """
        # KILL: 绝对分过低
        if panel_avg < KILL_PANEL_FLOOR:
            return Verdict.KILL, f"Panel 均分 {panel_avg:.1f} 低于下限 {KILL_PANEL_FLOOR}"

        # KILL: 末位 + 持续败北
        if rank == n and loss_rate >= KILL_LOSS_RATE:
            return Verdict.KILL, f"末位且败率 {loss_rate:.0%} ≥ {KILL_LOSS_RATE:.0%}"

        # SHIP 条件: 排名第一 + 有明确优势 + 胜率足够
        if rank == 1:
            if too_close_to_call:
                return Verdict.REVISE, (
                    f"排名第一但与第二名差距仅 {lead_margin:.1%}，"
                    f"低于置信阈值 {CONFIDENCE_THRESHOLD:.0%}，建议优化后再 ship"
                )
            if win_rate < SHIP_WIN_RATE:
                return Verdict.REVISE, f"排名第一但 pairwise 胜率仅 {win_rate:.0%}"
            if obj_density > SHIP_MAX_OBJECTION_DENSITY:
                return Verdict.REVISE, f"排名第一但 objection 密度 {obj_density:.1f} 过高"
            if overall_score < SHIP_MIN_SCORE:
                return Verdict.REVISE, f"排名第一但 overall score {overall_score:.1%} 偏低"
            return Verdict.SHIP, (
                f"排名第一，得分 {overall_score:.1%}，领先 {lead_margin:.1%}，"
                f"pairwise 胜率 {win_rate:.0%}"
            )

        return Verdict.REVISE, f"排名 #{rank}，有优化空间"
