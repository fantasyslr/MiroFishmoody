"""
Tests for devil's advocate judge perspective and dissent flag.

Plan 16-03: TDD RED phase — these tests should FAIL before implementation.
"""

import pytest
from unittest.mock import MagicMock, patch
from app.services.pairwise_judge import (
    DEVIL_ADVOCATE_PERSPECTIVE,
    JUDGE_PERSPECTIVES,
    PairwiseJudge,
    MultiJudgeEnsemble,
)


class TestDevilAdvocatePerspective:
    def test_devil_advocate_perspective_exists(self):
        """DEVIL_ADVOCATE_PERSPECTIVE must exist and have required keys."""
        assert DEVIL_ADVOCATE_PERSPECTIVE is not None
        assert DEVIL_ADVOCATE_PERSPECTIVE["id"] == "devil_advocate"
        assert DEVIL_ADVOCATE_PERSPECTIVE["name"] == "品牌怀疑者"
        assert "system_prompt" in DEVIL_ADVOCATE_PERSPECTIVE
        assert len(DEVIL_ADVOCATE_PERSPECTIVE["system_prompt"]) > 20

    def test_devil_advocate_not_in_judge_perspectives(self):
        """DEVIL_ADVOCATE_PERSPECTIVE is separate from JUDGE_PERSPECTIVES."""
        ids = [j["id"] for j in JUDGE_PERSPECTIVES]
        assert "devil_advocate" not in ids


class TestDissentFlag:
    def _make_campaign(self, cid="c1", name="方案A"):
        from app.models.campaign import Campaign, ProductLine
        return Campaign(
            id=cid,
            name=name,
            product_line=ProductLine.COLORED,
            target_audience="年轻女性",
            core_message="自然好看",
            channels=["小红书"],
            creative_direction="日系清新",
        )

    def test_dissent_flag_in_devil_vote(self):
        """judge_pair with devil's advocate judge must return dissent=True."""
        mock_llm = MagicMock()
        mock_llm.chat_json.return_value = {
            "winner": "A",
            "dimensions": {
                "reach_potential": "A",
                "conversion_potential": "A",
                "brand_alignment": "A",
                "risk_level": "A",
                "feasibility": "A",
            },
            "reasoning": "方案A更差",
        }
        judge = PairwiseJudge(llm_client=mock_llm)
        a = self._make_campaign("c1", "方案A")
        b = self._make_campaign("c2", "方案B")

        result = judge.judge_pair(a, b, DEVIL_ADVOCATE_PERSPECTIVE)

        assert result["dissent"] is True

    def test_non_devil_votes_no_dissent(self):
        """Non-devil-advocate judges must have dissent=False (or absent)."""
        mock_llm = MagicMock()
        mock_llm.chat_json.return_value = {
            "winner": "A",
            "dimensions": {
                "reach_potential": "A",
                "conversion_potential": "A",
                "brand_alignment": "A",
                "risk_level": "A",
                "feasibility": "A",
            },
            "reasoning": "理由",
        }
        judge = PairwiseJudge(llm_client=mock_llm)
        a = self._make_campaign("c1", "方案A")
        b = self._make_campaign("c2", "方案B")

        for perspective in JUDGE_PERSPECTIVES:
            result = judge.judge_pair(a, b, perspective)
            # dissent must be False or absent for non-devil judges
            assert result.get("dissent", False) is False, (
                f"Judge {perspective['id']} should not have dissent=True"
            )

    def test_flip_vote_preserves_dissent(self):
        """_flip_vote() on a vote with dissent=True must preserve dissent=True."""
        vote = {
            "judge_id": "devil_advocate",
            "judge_name": "品牌怀疑者",
            "winner": "A",
            "dimensions": {
                "reach_potential": "A",
                "conversion_potential": "B",
                "brand_alignment": "tie",
                "risk_level": "A",
                "feasibility": "B",
            },
            "reasoning": "怀疑一切",
            "dissent": True,
        }
        flipped = PairwiseJudge._flip_vote(vote)

        # dissent must be preserved
        assert flipped["dissent"] is True
        # winner and dimensions must be flipped
        assert flipped["winner"] == "B"
        assert flipped["dimensions"]["reach_potential"] == "B"
        assert flipped["dimensions"]["conversion_potential"] == "A"
        assert flipped["dimensions"]["brand_alignment"] == "tie"

    def test_flip_vote_preserves_dissent_false(self):
        """_flip_vote() on a vote with dissent=False must preserve dissent=False."""
        vote = {
            "judge_id": "strategist",
            "judge_name": "策略视角",
            "winner": "B",
            "dimensions": {
                "reach_potential": "B",
                "conversion_potential": "A",
                "brand_alignment": "B",
                "risk_level": "tie",
                "feasibility": "A",
            },
            "reasoning": "策略分析",
            "dissent": False,
        }
        flipped = PairwiseJudge._flip_vote(vote)
        assert flipped.get("dissent", False) is False


class TestMultiJudgeEnsembleIncludesDevil:
    def _make_ensemble(self):
        mock_llm = MagicMock()
        return MultiJudgeEnsemble(llm_client=mock_llm)

    def test_ensemble_includes_devil_advocate_perspective(self):
        """MultiJudgeEnsemble must include DEVIL_ADVOCATE_PERSPECTIVE in perspectives."""
        ensemble = self._make_ensemble()
        perspective_ids = [p["id"] for p in ensemble._perspectives]
        assert "devil_advocate" in perspective_ids

    def test_ensemble_perspectives_has_all_judges(self):
        """MultiJudgeEnsemble._perspectives must include all JUDGE_PERSPECTIVES plus devil."""
        ensemble = self._make_ensemble()
        perspective_ids = set(p["id"] for p in ensemble._perspectives)
        for jp in JUDGE_PERSPECTIVES:
            assert jp["id"] in perspective_ids
        assert "devil_advocate" in perspective_ids
