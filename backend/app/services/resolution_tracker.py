"""
Resolution Tracker — 赛后结算入口

最小骨架：
- 接收真实投放结果
- 创建 ResolutionRecord
- 存储到 calibration
- 预留 recalibrate 触发
"""

from typing import Dict, Optional
from datetime import datetime

from ..utils.logger import get_logger
from ..models.scoreboard import ResolutionRecord
from .judge_calibration import JudgeCalibration

logger = get_logger('ranker.resolution')


class ResolutionTracker:
    """赛后结算追踪器"""

    def __init__(self):
        self.calibration = JudgeCalibration()

    def resolve(
        self,
        set_id: str,
        winner_campaign_id: str,
        actual_metrics: Dict[str, float],
        predicted_probabilities: Dict[str, float],
        notes: str = "",
    ) -> ResolutionRecord:
        """
        记录一次赛后结算。

        Args:
            set_id: 评审集 ID
            winner_campaign_id: 实际胜出的 campaign ID
            actual_metrics: 真实指标 {ctr, hold_rate, lpv, cvr, ...}
            predicted_probabilities: 评审时的 win_probability {campaign_id: prob}
            notes: 备注

        Returns:
            ResolutionRecord
        """
        predicted_prob = predicted_probabilities.get(winner_campaign_id, 0)

        record = ResolutionRecord(
            set_id=set_id,
            campaign_id=winner_campaign_id,
            resolved_at=datetime.now().isoformat(),
            actual_metrics=actual_metrics,
            predicted_win_prob=predicted_prob,
            was_actual_winner=True,
            notes=notes,
        )

        self.calibration.record_resolution(record)

        # 同时记录非胜出方案
        for cid, prob in predicted_probabilities.items():
            if cid != winner_campaign_id:
                loser_record = ResolutionRecord(
                    set_id=set_id,
                    campaign_id=cid,
                    resolved_at=datetime.now().isoformat(),
                    actual_metrics={},
                    predicted_win_prob=prob,
                    was_actual_winner=False,
                    notes=notes,
                )
                self.calibration.record_resolution(loser_record)

        logger.info(
            f"Resolution: set={set_id}, winner={winner_campaign_id}, "
            f"predicted_prob={predicted_prob:.3f}"
        )

        return record

    def get_resolution_ready_fields(self) -> Dict[str, str]:
        """返回结算需要的字段说明"""
        return {
            "ctr": "Click-Through Rate (点击率)",
            "hold_rate": "Hold Rate (页面停留率)",
            "lpv": "Landing Page Views (落地页浏览量)",
            "cvr": "Conversion Rate (转化率)",
            "roas": "Return on Ad Spend (可选，仅供参考)",
            "aov": "Average Order Value (可选)",
        }
