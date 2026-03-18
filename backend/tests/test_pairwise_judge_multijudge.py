"""
Unit tests for MultiJudgeEnsemble — position-alternating multi-judge pairwise evaluator.

TDD Phase 16-01, Task 2.
"""

from unittest.mock import MagicMock, patch, call
from typing import List, Dict, Any

import pytest

from app.models.campaign import Campaign, ProductLine
from app.models.evaluation import PairwiseResult


def _make_campaign(cid: str) -> Campaign:
    c = MagicMock(spec=Campaign)
    c.id = cid
    c.name = f"Campaign {cid}"
    c.product_line = ProductLine.MOODYPLUS
    c.target_audience = "Test audience"
    c.core_message = "Test message"
    c.channels = ["xiaohongshu"]
    c.creative_direction = "Test creative"
    c.budget_range = None
    c.promo_mechanic = None
    c.kv_description = None
    c.image_paths = []
    return c


def _vote(winner: str = "A", judge_id: str = "strategist") -> Dict[str, Any]:
    return {
        "judge_id": judge_id,
        "judge_name": "策略视角",
        "winner": winner,
        "dimensions": {
            "reach_potential": winner,
            "conversion_potential": winner,
            "brand_alignment": winner,
            "risk_level": winner,
            "feasibility": winner,
        },
        "reasoning": "test reasoning",
    }


class TestMultiJudgeEnsembleImport:
    """MultiJudgeEnsemble must be importable from pairwise_judge."""

    def test_class_importable(self):
        from app.services.pairwise_judge import MultiJudgeEnsemble
        assert MultiJudgeEnsemble is not None

    def test_is_subclass_of_pairwise_judge(self):
        from app.services.pairwise_judge import MultiJudgeEnsemble, PairwiseJudge
        assert issubclass(MultiJudgeEnsemble, PairwiseJudge)


class TestAlternatingOrder:
    """Judges at even indices get (A,B); odd indices get (B,A)."""

    def test_alternating_order_calls(self):
        from app.services.pairwise_judge import MultiJudgeEnsemble

        a = _make_campaign("camp_a")
        b = _make_campaign("camp_b")

        ensemble = MultiJudgeEnsemble(llm_client=MagicMock(), num_judges=4)

        # Track which (first, second) campaign arg was passed to _safe_judge
        call_orders: List[tuple] = []

        def mock_safe_judge(first, second, judge):
            call_orders.append((first.id, second.id))
            return _vote("A", judge["id"])

        ensemble._safe_judge = mock_safe_judge

        ensemble.evaluate_pair(a, b)

        assert len(call_orders) == 4, f"Expected 4 calls, got {len(call_orders)}"
        # index 0 (even) → (A, B)
        assert call_orders[0] == ("camp_a", "camp_b"), f"idx 0 should be (A,B), got {call_orders[0]}"
        # index 1 (odd)  → (B, A)
        assert call_orders[1] == ("camp_b", "camp_a"), f"idx 1 should be (B,A), got {call_orders[1]}"
        # index 2 (even) → (A, B)
        assert call_orders[2] == ("camp_a", "camp_b"), f"idx 2 should be (A,B), got {call_orders[2]}"
        # index 3 (odd)  → (B, A)
        assert call_orders[3] == ("camp_b", "camp_a"), f"idx 3 should be (B,A), got {call_orders[3]}"


class TestVoteCount:
    """result.votes contains N entries (one per judge, after normalization)."""

    def test_vote_count_equals_num_judges(self):
        from app.services.pairwise_judge import MultiJudgeEnsemble

        a = _make_campaign("camp_a")
        b = _make_campaign("camp_b")

        for n in [3, 5, 6]:
            ensemble = MultiJudgeEnsemble(llm_client=MagicMock(), num_judges=n)
            ensemble._safe_judge = lambda first, second, judge: _vote("A", judge["id"])
            result = ensemble.evaluate_pair(a, b)
            assert len(result.votes) == n, (
                f"num_judges={n}: expected {n} votes, got {len(result.votes)}"
            )


class TestMajorityWinner:
    """Winner determined by majority across all normalized votes."""

    def test_majority_a_wins(self):
        from app.services.pairwise_judge import MultiJudgeEnsemble

        a = _make_campaign("camp_a")
        b = _make_campaign("camp_b")

        ensemble = MultiJudgeEnsemble(llm_client=MagicMock(), num_judges=5)
        vote_seq = ["A", "A", "A", "B", "B"]  # 3 for A, 2 for B

        call_count = [0]

        def mock_safe_judge(first, second, judge):
            idx = call_count[0]
            call_count[0] += 1
            raw_winner = vote_seq[idx]
            # For odd-index calls (swapped order), we need to un-flip:
            # The mock returns a vote in terms of the first/second args.
            # MultiJudgeEnsemble will flip odd-index votes.
            # We want the *normalized* result to be vote_seq[idx],
            # so for odd-index (swapped), we pre-flip so after _flip_vote it becomes vote_seq[idx].
            return _vote(raw_winner, judge["id"])

        ensemble._safe_judge = mock_safe_judge

        result = ensemble.evaluate_pair(a, b)

        # 3 votes normalized to A, 2 to B (after flipping odd-index) → A wins
        a_wins = sum(1 for v in result.votes if v["winner"] == "A")
        b_wins = sum(1 for v in result.votes if v["winner"] == "B")
        assert a_wins > b_wins, f"Expected A majority: a={a_wins}, b={b_wins}"
        assert result.winner_id == a.id, f"Expected winner camp_a, got {result.winner_id}"

    def test_majority_b_wins(self):
        from app.services.pairwise_judge import MultiJudgeEnsemble

        a = _make_campaign("camp_a")
        b = _make_campaign("camp_b")

        ensemble = MultiJudgeEnsemble(llm_client=MagicMock(), num_judges=5)

        # All 5 normalized votes for B
        call_count = [0]

        def mock_safe_judge(first, second, judge):
            idx = call_count[0]
            call_count[0] += 1
            # Even-index: (A, B) order. Return "B" (i.e. original B wins) — no flip needed.
            # Odd-index: (B, A) order. _flip_vote will flip A→B, B→A.
            #   We want normalized "B" wins, so raw must say "A" (which after flip → "B").
            if idx % 2 == 1:
                return _vote("A", judge["id"])  # raw "A" in (B,A) → flipped to "B"
            return _vote("B", judge["id"])

        ensemble._safe_judge = mock_safe_judge

        result = ensemble.evaluate_pair(a, b)
        assert result.winner_id == b.id, f"Expected winner camp_b, got {result.winner_id}"


class TestSameSignature:
    """MultiJudgeEnsemble.evaluate_all has same signature as PairwiseJudge.evaluate_all."""

    def test_evaluate_all_accepts_campaigns_and_max_workers(self):
        from app.services.pairwise_judge import MultiJudgeEnsemble

        ensemble = MultiJudgeEnsemble(llm_client=MagicMock(), num_judges=2)

        a = _make_campaign("c1")
        b = _make_campaign("c2")

        # Patch evaluate_pair to avoid LLM calls
        ensemble._safe_judge = lambda first, second, judge: _vote("A", judge["id"])

        # Should accept campaigns list and max_workers kwarg without TypeError
        results, bt_scores = ensemble.evaluate_all([a, b], max_workers=2)

        assert isinstance(results, list)
        assert isinstance(bt_scores, dict)
        assert len(results) == 1  # C(2,2) = 1 pair


class TestPositionField:
    """Each vote should carry a 'position' field indicating normal or swapped."""

    def test_votes_have_position_field(self):
        from app.services.pairwise_judge import MultiJudgeEnsemble

        a = _make_campaign("camp_a")
        b = _make_campaign("camp_b")

        ensemble = MultiJudgeEnsemble(llm_client=MagicMock(), num_judges=4)
        ensemble._safe_judge = lambda first, second, judge: _vote("A", judge["id"])

        result = ensemble.evaluate_pair(a, b)

        for i, vote in enumerate(result.votes):
            assert "position" in vote, f"Vote {i} missing 'position' field"
            expected_pos = "normal" if i % 2 == 0 else "swapped"
            assert vote["position"] == expected_pos, (
                f"Vote {i} position={vote['position']}, expected {expected_pos}"
            )
