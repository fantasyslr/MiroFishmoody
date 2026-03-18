"""
ConsensusAgent — 跨人格评分离群值检测

对每个 campaign 计算跨人格评分的标准差。
偏离均值超过 stdev_threshold 的人格评分标记 suspect=True。
"""
import statistics
from typing import List
from collections import defaultdict

from ..models.evaluation import PanelScore
from ..utils.logger import get_logger

logger = get_logger('ranker.consensus_agent')

CONSENSUS_STDEV_THRESHOLD = 2.0  # same scale as controversy badge


class ConsensusAgent:
    """Detects outlier persona scores via cross-persona stdev analysis."""

    def __init__(self, stdev_threshold: float = CONSENSUS_STDEV_THRESHOLD):
        self.stdev_threshold = stdev_threshold

    def detect(self, panel_scores: List[PanelScore]) -> List[PanelScore]:
        """Mark outlier scores with suspect=True in dimension_scores.

        Groups scores by campaign_id, computes stdev per campaign,
        flags any persona score > stdev_threshold from mean.
        Mutates panel_scores in-place and returns the same list.
        """
        # Group by campaign
        by_campaign: dict = defaultdict(list)
        for ps in panel_scores:
            by_campaign[ps.campaign_id].append(ps)

        for campaign_id, scores in by_campaign.items():
            if len(scores) < 2:
                continue  # stdev undefined for single observation

            values = [ps.score for ps in scores]
            mean = statistics.mean(values)
            stdev = statistics.stdev(values)

            for ps in scores:
                deviation = abs(ps.score - mean)
                if deviation > self.stdev_threshold:
                    ps.dimension_scores["suspect"] = True
                    logger.info(
                        f"Suspect score: persona={ps.persona_id} "
                        f"campaign={campaign_id} score={ps.score:.1f} "
                        f"mean={mean:.1f} stdev={stdev:.2f}"
                    )

        return panel_scores
