"""
Decision Market 数据模型 — prediction-market-inspired 结构
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


# 5 个子市场维度
SUB_MARKET_KEYS = [
    "thumb_stop",          # 停留吸引力
    "clarity",             # 信息清晰度
    "trust",               # 信任感
    "conversion_readiness", # 转化就绪度
    "claim_risk",          # 声称风险（高 = 差）
]

SUB_MARKET_LABELS = {
    "thumb_stop": "停留吸引力",
    "clarity": "信息清晰度",
    "trust": "信任感",
    "conversion_readiness": "转化就绪度",
    "claim_risk": "声称风险",
}


@dataclass
class SubMarketProbability:
    """单个子市场中某 campaign 的概率"""
    market_key: str
    market_label: str
    campaign_id: str
    probability: float  # 0-1, 该方案在此维度上为最优的相对概率
    raw_score: float    # 归一化前的原始分


@dataclass
class CampaignMarketView:
    """单个 campaign 的完整 market view"""
    campaign_id: str
    campaign_name: str
    win_probability: float               # 总体胜出概率 (0-1)
    sub_markets: Dict[str, float]        # market_key → probability
    rank: int
    verdict: str                         # ship / revise / kill
    spread_to_next: Optional[float]      # 与下一名的概率差距
    verdict_rationale: str               # 判定理由


@dataclass
class ProbabilityBoard:
    """完整概率面板"""
    campaigns: List[CampaignMarketView]
    spread: float                        # #1 vs #2 的概率差距
    no_clear_edge: bool                  # spread 低于阈值
    no_trade_band: float                 # 当前 no-trade 阈值
    rationale_for_uncertainty: str       # 不确定性说明
    sub_markets: List[SubMarketProbability]  # 所有子市场详情

    def to_dict(self) -> Dict[str, Any]:
        return {
            "campaigns": [
                {
                    "campaign_id": c.campaign_id,
                    "campaign_name": c.campaign_name,
                    "win_probability": round(c.win_probability, 3),
                    "sub_markets": {
                        k: round(v, 3) for k, v in c.sub_markets.items()
                    },
                    "rank": c.rank,
                    "verdict": c.verdict,
                    "spread_to_next": round(c.spread_to_next, 3) if c.spread_to_next is not None else None,
                    "verdict_rationale": c.verdict_rationale,
                }
                for c in self.campaigns
            ],
            "spread": round(self.spread, 3),
            "no_clear_edge": self.no_clear_edge,
            "no_trade_band": self.no_trade_band,
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
