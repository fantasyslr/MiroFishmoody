"""
Tests for PairwiseJudge position-swap debiasing.

Verifies that evaluate_pair runs each judge twice (normal + swapped order)
and correctly flags position_swap_consistent in PairwiseResult.
"""

import pytest
from unittest.mock import MagicMock, patch, call

from app.models.campaign import Campaign, ProductLine
from app.models.evaluation import PairwiseResult
from app.services.pairwise_judge import PairwiseJudge


def _make_campaign(cid: str, name: str = "Test") -> Campaign:
    """Create a minimal Campaign for testing."""
    return Campaign(
        id=cid,
        name=name,
        product_line=ProductLine.COLORED,
        target_audience="18-25 女性",
        core_message="测试核心信息",
        channels=["小红书"],
        creative_direction="测试方向",
    )


def _mock_judge_response(winner: str, dims: dict = None):
    """Helper to create a mock LLM judge response."""
    return {
        "winner": winner,
        "dimensions": dims or {
            "reach_potential": winner,
            "conversion_potential": winner,
            "brand_alignment": "tie",
            "risk_level": winner,
            "feasibility": "tie",
        },
        "reasoning": "Test reasoning",
    }


class TestPositionSwapDebiasing:
    """Tests for position-swap debiasing in PairwiseJudge."""

    def test_evaluate_pair_calls_judge_twice_per_judge(self):
        """evaluate_pair calls judge_pair twice per judge (A,B then B,A),
        producing 6 total calls for 3 judges."""
        mock_llm = MagicMock()
        mock_llm.chat_json.return_value = _mock_judge_response("A")

        judge = PairwiseJudge(llm_client=mock_llm)
        a = _make_campaign("camp_a", "Campaign A")
        b = _make_campaign("camp_b", "Campaign B")

        result = judge.evaluate_pair(a, b)

        # 3 judges x 2 orderings = 6 total LLM calls
        assert mock_llm.chat_json.call_count == 6
        # Normal votes: 3, swap votes: 3
        assert len(result.votes) == 3
        assert len(result.swap_votes) == 3

    def test_consistent_winner_flagged_true(self):
        """When both orderings agree on winner, position_swap_consistent=True."""
        mock_llm = MagicMock()
        # Normal order: all say A wins
        # Swapped order: all say A wins (which means "B" in swapped labels, flipped back to A)
        # When swapped, judge sees (B, A). If judge says "A" that means B in original.
        # For consistency: judge should say "B" in swapped round (= A in original).
        call_count = {"n": 0}
        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] <= 3:
                # Normal round: A wins
                return _mock_judge_response("A")
            else:
                # Swapped round: judge says "B" (= original A wins, since args are swapped)
                return _mock_judge_response("B")
        mock_llm.chat_json.side_effect = side_effect

        judge = PairwiseJudge(llm_client=mock_llm)
        a = _make_campaign("camp_a", "Campaign A")
        b = _make_campaign("camp_b", "Campaign B")

        result = judge.evaluate_pair(a, b)

        assert result.position_swap_consistent is True
        assert result.winner_id == "camp_a"

    def test_inconsistent_winner_flagged_false(self):
        """When orderings disagree, position_swap_consistent=False."""
        mock_llm = MagicMock()
        call_count = {"n": 0}
        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] <= 3:
                # Normal round: A wins
                return _mock_judge_response("A")
            else:
                # Swapped round: judge says "A" (= original B wins after flip)
                return _mock_judge_response("A")
        mock_llm.chat_json.side_effect = side_effect

        judge = PairwiseJudge(llm_client=mock_llm)
        a = _make_campaign("camp_a", "Campaign A")
        b = _make_campaign("camp_b", "Campaign B")

        result = judge.evaluate_pair(a, b)

        assert result.position_swap_consistent is False
        # Winner should still be based on normal round
        assert result.winner_id == "camp_a"

    def test_evaluate_all_return_type_unchanged(self):
        """evaluate_all still returns Tuple[List[PairwiseResult], Dict[str, float]]."""
        mock_llm = MagicMock()
        mock_llm.chat_json.return_value = _mock_judge_response("A")

        judge = PairwiseJudge(llm_client=mock_llm)
        camps = [_make_campaign(f"c{i}", f"Camp {i}") for i in range(3)]

        results, bt_scores = judge.evaluate_all(camps, max_workers=1)

        assert isinstance(results, list)
        assert all(isinstance(r, PairwiseResult) for r in results)
        assert isinstance(bt_scores, dict)
        assert len(results) == 3  # C(3,2) = 3 pairs

    def test_winner_flipping_logic_for_swapped_round(self):
        """Swapped round: when judge says 'A' it means original B won (labels swapped)."""
        mock_llm = MagicMock()
        call_count = {"n": 0}
        def side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] <= 3:
                # Normal: B wins
                return _mock_judge_response("B")
            else:
                # Swapped: judge says "A" (args are B,A so "A" means B in original = same winner)
                return _mock_judge_response("A")
        mock_llm.chat_json.side_effect = side_effect

        judge = PairwiseJudge(llm_client=mock_llm)
        a = _make_campaign("camp_a", "Campaign A")
        b = _make_campaign("camp_b", "Campaign B")

        result = judge.evaluate_pair(a, b)

        # Both rounds agree B wins
        assert result.position_swap_consistent is True
        assert result.winner_id == "camp_b"
