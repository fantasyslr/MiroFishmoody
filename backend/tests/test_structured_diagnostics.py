"""
Tests for ImageAnalyzer structured diagnostics output.

Verifies that analyze_single_image returns diagnostics with issues[] and
recommendations[], and that compute_visual_score remains backward compatible.
"""

import pytest
from unittest.mock import MagicMock

from app.services.image_analyzer import ImageAnalyzer, compute_visual_score


def _base_analysis_result():
    """A complete mock LLM response including the new diagnostics field."""
    return {
        "creative_style": "editorial",
        "product_visibility": 7,
        "human_presence": "full_face",
        "text_density": 4,
        "visual_claim_focus": "aesthetic",
        "aesthetic_tone": "premium",
        "trust_signal_strength": 6,
        "promo_intensity": 3,
        "premium_vs_mass": "premium",
        "visual_hooks": ["眼部特写", "对比图"],
        "visual_risks": ["文字过多"],
        "summary": "高质量美妆素材",
        "diagnostics": {
            "issues": [
                {
                    "category": "visual_quality",
                    "severity": "medium",
                    "description": "图片轻微过曝"
                },
                {
                    "category": "brand_alignment",
                    "severity": "low",
                    "description": "品牌 logo 不够突出"
                },
            ],
            "recommendations": [
                {
                    "category": "visual_quality",
                    "action": "调整曝光补偿，增加对比度",
                    "priority": "medium"
                },
                {
                    "category": "brand_alignment",
                    "action": "放大品牌 logo 至画面 5% 以上",
                    "priority": "low"
                },
            ],
        },
    }


class TestStructuredDiagnostics:
    """Tests for structured diagnostics in ImageAnalyzer output."""

    def test_single_image_has_diagnostics_key(self):
        """Single image analysis returns dict with 'diagnostics' key."""
        mock_llm = MagicMock()
        mock_llm.chat_multimodal_json.return_value = _base_analysis_result()

        analyzer = ImageAnalyzer(llm_client=mock_llm)

        with pytest.MonkeyPatch.context() as m:
            m.setattr("app.services.image_analyzer.resolve_image_path", lambda p: p)
            m.setattr("app.services.image_analyzer.image_to_base64_part", lambda p: {"type": "image_url", "image_url": {"url": "data:image/png;base64,fake"}})
            result = analyzer.analyze_single_image("test.png")

        assert result is not None
        assert "diagnostics" in result
        assert "issues" in result["diagnostics"]
        assert "recommendations" in result["diagnostics"]

    def test_issue_fields(self):
        """Each issue has category, severity, description."""
        mock_llm = MagicMock()
        mock_llm.chat_multimodal_json.return_value = _base_analysis_result()

        analyzer = ImageAnalyzer(llm_client=mock_llm)

        with pytest.MonkeyPatch.context() as m:
            m.setattr("app.services.image_analyzer.resolve_image_path", lambda p: p)
            m.setattr("app.services.image_analyzer.image_to_base64_part", lambda p: {"type": "image_url", "image_url": {"url": "data:image/png;base64,fake"}})
            result = analyzer.analyze_single_image("test.png")

        issues = result["diagnostics"]["issues"]
        assert len(issues) >= 1
        for issue in issues:
            assert "category" in issue
            assert "severity" in issue
            assert issue["severity"] in ("high", "medium", "low")
            assert "description" in issue

    def test_recommendation_fields(self):
        """Each recommendation has category, action, priority."""
        mock_llm = MagicMock()
        mock_llm.chat_multimodal_json.return_value = _base_analysis_result()

        analyzer = ImageAnalyzer(llm_client=mock_llm)

        with pytest.MonkeyPatch.context() as m:
            m.setattr("app.services.image_analyzer.resolve_image_path", lambda p: p)
            m.setattr("app.services.image_analyzer.image_to_base64_part", lambda p: {"type": "image_url", "image_url": {"url": "data:image/png;base64,fake"}})
            result = analyzer.analyze_single_image("test.png")

        recs = result["diagnostics"]["recommendations"]
        assert len(recs) >= 1
        for rec in recs:
            assert "category" in rec
            assert "action" in rec
            assert "priority" in rec
            assert rec["priority"] in ("high", "medium", "low")

    def test_aggregated_profile_includes_diagnostics(self):
        """Multi-image aggregation includes merged diagnostics."""
        single_result = _base_analysis_result()
        agg_result = {
            **_base_analysis_result(),
            "consistency_score": 8,
            "dominant_creative_strategy": "高端美妆路线",
        }

        mock_llm = MagicMock()
        mock_llm.chat_multimodal_json.return_value = single_result
        mock_llm.chat_json.return_value = agg_result

        analyzer = ImageAnalyzer(llm_client=mock_llm)

        with pytest.MonkeyPatch.context() as m:
            m.setattr("app.services.image_analyzer.resolve_image_path", lambda p: p)
            m.setattr("app.services.image_analyzer.image_to_base64_part", lambda p: {"type": "image_url", "image_url": {"url": "data:image/png;base64,fake"}})
            result = analyzer.analyze_plan_images(["img1.png", "img2.png"])

        assert result is not None
        assert "diagnostics" in result
        assert "issues" in result["diagnostics"]
        assert "recommendations" in result["diagnostics"]

    def test_compute_visual_score_backward_compatible(self):
        """compute_visual_score works with and without diagnostics field."""
        # With diagnostics
        profile_with = _base_analysis_result()
        score_with = compute_visual_score(profile_with)
        assert 0.0 <= score_with <= 1.0

        # Without diagnostics (legacy profile)
        profile_without = {k: v for k, v in _base_analysis_result().items() if k != "diagnostics"}
        score_without = compute_visual_score(profile_without)
        assert 0.0 <= score_without <= 1.0

        # Scores should be identical since diagnostics doesn't affect scoring
        assert score_with == score_without
