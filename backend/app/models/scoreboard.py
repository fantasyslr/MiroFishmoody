"""
ScoreBoard 数据模型 — 评分面板结构
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


# 5 个评分维度
DIMENSION_KEYS = [
    "thumb_stop",          # 停留吸引力
    "clarity",             # 信息清晰度
    "trust",               # 信任感
    "conversion_readiness", # 转化就绪度
    "claim_risk",          # 声称风险（高 = 差）
]

DIMENSION_LABELS = {
    "thumb_stop": "停留吸引力",
    "clarity": "信息清晰度",
    "trust": "信任感",
    "conversion_readiness": "转化就绪度",
    "claim_risk": "声称风险",
}


@dataclass
class DimensionScore:
    """单个维度中某 campaign 的得分"""
    dimension_key: str
    dimension_label: str
    campaign_id: str
    score: float  # 0-1, 该方案在此维度上为最优的相对得分
    raw_score: float    # 归一化前的原始分


@dataclass
class CampaignScoreView:
    """单个 campaign 的完整 score view"""
    campaign_id: str
    campaign_name: str
    overall_score: float               # 总体得分 (0-1)
    dimension_scores: Dict[str, float]  # dimension_key → score
    rank: int
    verdict: str                         # ship / revise / kill
    lead_margin_to_next: Optional[float]  # 与下一名的得分差距
    verdict_rationale: str               # 判定理由


@dataclass
class ScoreBoard:
    """完整评分面板"""
    campaigns: List[CampaignScoreView]
    lead_margin: float                    # #1 vs #2 的得分差距
    too_close_to_call: bool               # lead_margin 低于阈值
    confidence_threshold: float           # 当前置信阈值
    rationale_for_uncertainty: str       # 不确定性说明
    dimension_scores: List[DimensionScore]  # 所有维度详情

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaigns": [
                {
                    "campaign_id": c.campaign_id,
                    "campaign_name": c.campaign_name,
                    "overall_score": round(c.overall_score, 3),
                    "dimension_scores": {
                        k: round(v, 3) for k, v in c.dimension_scores.items()
                    },
                    "rank": c.rank,
                    "verdict": c.verdict,
                    "lead_margin_to_next": round(c.lead_margin_to_next, 3) if c.lead_margin_to_next is not None else None,
                    "verdict_rationale": c.verdict_rationale,
                }
                for c in self.campaigns
            ],
            "lead_margin": round(self.lead_margin, 3),
            "too_close_to_call": self.too_close_to_call,
            "confidence_threshold": self.confidence_threshold,
            "rationale_for_uncertainty": self.rationale_for_uncertainty,
        }


@dataclass
class ResolutionRecord:
    """赛后结算记录"""
    set_id: str
    campaign_id: str
    resolved_at: str
    actual_metrics: Dict[str, float]   # ctr, hold_rate, lpv, cvr, etc.
    predicted_win_prob: float
    was_actual_winner: bool
    notes: str = ""


@dataclass
class JudgePerformanceStats:
    """单个 judge/persona 的校准统计"""
    judge_id: str
    judge_type: str                     # "persona" | "judge"
    total_predictions: int
    brier_score: Optional[float]        # lower is better
    log_loss: Optional[float]
    calibration_buckets: Dict[str, Dict[str, float]]  # "0.0-0.2" → {predicted_avg, actual_avg, count}
    weight: float = 1.0                 # 当前权重

    def to_dict(self) -> Dict[str, Any]:
        return {
            "judge_id": self.judge_id,
            "judge_type": self.judge_type,
            "total_predictions": self.total_predictions,
            "brier_score": round(self.brier_score, 4) if self.brier_score is not None else None,
            "log_loss": round(self.log_loss, 4) if self.log_loss is not None else None,
            "calibration_buckets": self.calibration_buckets,
            "weight": round(self.weight, 3),
        }
