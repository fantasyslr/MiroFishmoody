"""
Unit tests for ConsensusAgent — stdev-based outlier detection.
"""
import pytest
from app.models.evaluation import PanelScore
from app.services.consensus_agent import ConsensusAgent


def _make_score(persona_id: str, campaign_id: str, score: float) -> PanelScore:
    return PanelScore(
        persona_id=persona_id,
        persona_name=f"Persona {persona_id}",
        campaign_id=campaign_id,
        score=score,
        objections=[],
        strengths=[],
        reasoning="",
        dimension_scores={},
    )


class TestConsensusAgent:

    def test_suspect_flagged(self):
        """Persona with score=2 among [8, 8, 8, 2] should be flagged suspect.

        mean=6.5, stdev≈2.65, deviation(2)=4.5 > threshold=2.0 → p4 flagged
        deviation(8)=1.5 < threshold=2.0 → p1/p2/p3 not flagged
        """
        scores = [
            _make_score("p1", "c1", 8),
            _make_score("p2", "c1", 8),
            _make_score("p3", "c1", 8),
            _make_score("p4", "c1", 2),
        ]
        agent = ConsensusAgent(stdev_threshold=2.0)
        result = agent.detect(scores)

        suspects = [ps for ps in result if ps.dimension_scores.get("suspect") is True]
        assert len(suspects) == 1
        assert suspects[0].persona_id == "p4"

    def test_within_threshold_not_flagged(self):
        """Scores [7, 8, 7, 8] are tightly clustered — no suspect flags."""
        scores = [
            _make_score("p1", "c1", 7),
            _make_score("p2", "c1", 8),
            _make_score("p3", "c1", 7),
            _make_score("p4", "c1", 8),
        ]
        agent = ConsensusAgent(stdev_threshold=2.0)
        result = agent.detect(scores)

        suspects = [ps for ps in result if ps.dimension_scores.get("suspect") is True]
        assert len(suspects) == 0

    def test_single_persona_no_flag(self):
        """Single persona per campaign: stdev undefined, no flag."""
        scores = [_make_score("p1", "c1", 5)]
        agent = ConsensusAgent(stdev_threshold=2.0)
        result = agent.detect(scores)

        assert result[0].dimension_scores.get("suspect") is None

    def test_returns_same_list(self):
        """detect() mutates in-place and returns same list object."""
        scores = [
            _make_score("p1", "c1", 9),
            _make_score("p2", "c1", 2),
        ]
        agent = ConsensusAgent()
        returned = agent.detect(scores)

        assert returned is scores

    def test_multiple_campaigns_independent(self):
        """Suspect detection is per-campaign, not global."""
        scores = [
            # campaign c1: tight scores, no outlier
            _make_score("p1", "c1", 8),
            _make_score("p2", "c1", 8),
            _make_score("p3", "c1", 7),
            # campaign c2: one outlier — [8, 8, 2] mean=6.0, stdev≈3.46
            # deviation(8)=2.0 (not strictly greater), deviation(2)=4.0 → only p3 flagged
            _make_score("p1", "c2", 8),
            _make_score("p2", "c2", 8),
            _make_score("p3", "c2", 2),
        ]
        agent = ConsensusAgent(stdev_threshold=2.0)
        result = agent.detect(scores)

        suspects = [ps for ps in result if ps.dimension_scores.get("suspect") is True]
        assert len(suspects) == 1
        assert suspects[0].campaign_id == "c2"
        assert suspects[0].persona_id == "p3"
