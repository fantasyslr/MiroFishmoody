"""
评审结果数据模型
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    """Ship / Revise / Kill 判定"""
    SHIP = "ship"
    REVISE = "revise"
    KILL = "kill"


@dataclass
class PanelScore:
    """单个 persona 对单个 campaign 的评分"""
    persona_id: str
    persona_name: str
    campaign_id: str
    score: float            # 1-10
    objections: List[str]
    strengths: List[str]
    reasoning: str
    dimension_scores: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PairwiseResult:
    """一对 campaign 的对决结果"""
    campaign_a_id: str
    campaign_b_id: str
    winner_id: Optional[str]  # None = tie
    votes: List[Dict[str, Any]]  # 每个 judge 的投票详情
    dimensions: Dict[str, str]   # 各维度胜负
    position_swap_consistent: bool = True  # 正反序结果是否一致
    swap_votes: List[Dict[str, Any]] = field(default_factory=list)  # 反序投票详情


@dataclass
class CampaignRanking:
    """单个 campaign 的综合排名"""
    campaign_id: str
    campaign_name: str
    rank: int
    composite_score: float
    panel_avg: float
    pairwise_wins: int
    pairwise_losses: int
    verdict: Verdict
    top_objections: List[str]
    top_strengths: List[str]


@dataclass
class EvaluationResult:
    """完整评审结果"""
    set_id: str
    rankings: List[CampaignRanking]
    panel_scores: List[PanelScore]
    pairwise_results: List[PairwiseResult]
    summary: str
    assumptions: List[str]
    confidence_notes: List[str]
    scoreboard: Optional[Dict[str, Any]] = None
    resolution_ready_fields: Optional[Dict[str, str]] = None
    visual_diagnostics: Optional[Dict[str, Any]] = None  # campaign_id -> {issues, recommendations}

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "set_id": self.set_id,
            "rankings": [
                {
                    "campaign_id": r.campaign_id,
                    "campaign_name": r.campaign_name,
                    "rank": r.rank,
                    "composite_score": round(r.composite_score, 2),
                    "panel_avg": round(r.panel_avg, 2),
                    "pairwise_wins": r.pairwise_wins,
                    "pairwise_losses": r.pairwise_losses,
                    "verdict": r.verdict.value,
                    "top_objections": r.top_objections,
                    "top_strengths": r.top_strengths,
                }
                for r in self.rankings
            ],
            "panel_scores": [
                {
                    "persona_id": ps.persona_id,
                    "persona_name": ps.persona_name,
                    "campaign_id": ps.campaign_id,
                    "score": ps.score,
                    "objections": ps.objections,
                    "strengths": ps.strengths,
                    "reasoning": ps.reasoning,
                    "dimension_scores": ps.dimension_scores,
                }
                for ps in self.panel_scores
            ],
            "pairwise_results": [
                {
                    "campaign_a_id": pr.campaign_a_id,
                    "campaign_b_id": pr.campaign_b_id,
                    "winner_id": pr.winner_id,
                    "votes": pr.votes,
                    "dimensions": pr.dimensions,
                    "position_swap_consistent": pr.position_swap_consistent,
                    "swap_votes": pr.swap_votes,
                }
                for pr in self.pairwise_results
            ],
            "summary": self.summary,
            "assumptions": self.assumptions,
            "confidence_notes": self.confidence_notes,
        }
        if self.scoreboard is not None:
            result["scoreboard"] = self.scoreboard
        if self.resolution_ready_fields is not None:
            result["resolution_ready_fields"] = self.resolution_ready_fields
        if self.visual_diagnostics is not None:
            result["visual_diagnostics"] = self.visual_diagnostics
        return result
