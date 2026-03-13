"""
数据模型模块
"""

from .task import TaskManager, TaskStatus
from .campaign import Campaign, CampaignSet, ProductLine
from .evaluation import (
    Verdict, PanelScore, PairwiseResult, CampaignRanking, EvaluationResult,
)
from .scoreboard import (
    ScoreBoard, CampaignScoreView, DimensionScore,
    ResolutionRecord, JudgePerformanceStats,
)

__all__ = [
    'TaskManager', 'TaskStatus',
    'Campaign', 'CampaignSet', 'ProductLine',
    'Verdict', 'PanelScore', 'PairwiseResult', 'CampaignRanking', 'EvaluationResult',
    'ScoreBoard', 'CampaignScoreView', 'DimensionScore',
    'ResolutionRecord', 'JudgePerformanceStats',
]
