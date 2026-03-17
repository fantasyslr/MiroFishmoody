"""
Tests for concurrent image analysis in ImageAnalyzer.

Verifies:
  - ThreadPoolExecutor-based concurrent image analysis
  - Semaphore-based rate limiting for LLM calls
  - Partial failure resilience
  - Configurable max_workers
"""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_llm():
    """LLM client mock that tracks concurrent call count."""
    client = MagicMock()
    client._concurrent_count = 0
    client._max_concurrent = 0
    client._lock = threading.Lock()

    def fake_multimodal_json(**kwargs):
        with client._lock:
            client._concurrent_count += 1
            if client._concurrent_count > client._max_concurrent:
                client._max_concurrent = client._concurrent_count
        # Simulate LLM latency
        time.sleep(0.1)
        with client._lock:
            client._concurrent_count -= 1
        return {
            "creative_style": "studio",
            "product_visibility": 8,
            "human_presence": "full_face",
            "text_density": 4,
            "visual_claim_focus": "aesthetic",
            "aesthetic_tone": "premium",
            "trust_signal_strength": 7,
            "promo_intensity": 3,
            "premium_vs_mass": "premium",
            "visual_hooks": ["eye_closeup"],
            "visual_risks": [],
            "summary": "test image",
        }

    client.chat_multimodal_json = MagicMock(side_effect=fake_multimodal_json)
    client.chat_json = MagicMock(return_value={
        "creative_style": "studio",
        "product_visibility": 8,
        "summary": "aggregated",
        "consistency_score": 8,
        "dominant_creative_strategy": "premium focus",
    })
    return client


class TestConcurrentAnalysis:
    """Test concurrent image analysis behavior."""

    @patch("app.services.image_analyzer.image_to_base64_part")
    @patch("app.services.image_analyzer.resolve_image_path")
    def test_concurrent_execution(self, mock_resolve, mock_b64, mock_llm):
        """3 images should be analyzed concurrently (all futures submitted before any completes)."""
        from app.services.image_analyzer import ImageAnalyzer

        mock_resolve.return_value = "/fake/path.jpg"
        mock_b64.return_value = {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,abc"}}

        analyzer = ImageAnalyzer(llm_client=mock_llm, max_workers=3)

        start = time.monotonic()
        result = analyzer.analyze_plan_images(["/img1.jpg", "/img2.jpg", "/img3.jpg"])
        elapsed = time.monotonic() - start

        # If serial: 3 * 0.1s = 0.3s minimum. Concurrent should be ~0.1s.
        # Use 0.25s as threshold to allow some overhead.
        assert elapsed < 0.25, f"Expected concurrent execution but took {elapsed:.2f}s (serial would be >=0.3s)"
        assert result is not None

    @patch("app.services.image_analyzer.image_to_base64_part")
    @patch("app.services.image_analyzer.resolve_image_path")
    def test_semaphore_limits_concurrency(self, mock_resolve, mock_b64, mock_llm):
        """With max_workers=2 and 4 images, never more than 2 simultaneous LLM calls."""
        from app.services.image_analyzer import ImageAnalyzer

        mock_resolve.return_value = "/fake/path.jpg"
        mock_b64.return_value = {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,abc"}}

        analyzer = ImageAnalyzer(llm_client=mock_llm, max_workers=2)
        analyzer.analyze_plan_images([f"/img{i}.jpg" for i in range(4)])

        assert mock_llm._max_concurrent <= 2, (
            f"Semaphore should limit to 2 but saw {mock_llm._max_concurrent} concurrent calls"
        )

    @patch("app.services.image_analyzer.image_to_base64_part")
    @patch("app.services.image_analyzer.resolve_image_path")
    def test_partial_failure_returns_results(self, mock_resolve, mock_b64, mock_llm):
        """One failing image should not abort others — partial results returned."""
        from app.services.image_analyzer import ImageAnalyzer

        mock_resolve.return_value = "/fake/path.jpg"
        mock_b64.return_value = {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,abc"}}

        call_count = 0

        def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("LLM explosion")
            return {
                "creative_style": "studio",
                "product_visibility": 8,
                "summary": "ok",
            }

        mock_llm.chat_multimodal_json = MagicMock(side_effect=side_effect)

        analyzer = ImageAnalyzer(llm_client=mock_llm, max_workers=3)
        result = analyzer.analyze_plan_images(["/a.jpg", "/b.jpg", "/c.jpg"])

        # Should still get a result (aggregated from 2 successful images)
        assert result is not None

    def test_max_workers_default_and_configurable(self, mock_llm):
        """max_workers defaults to 3 and is configurable via __init__."""
        from app.services.image_analyzer import ImageAnalyzer

        default = ImageAnalyzer(llm_client=mock_llm)
        assert default.max_workers == 3

        custom = ImageAnalyzer(llm_client=mock_llm, max_workers=5)
        assert custom.max_workers == 5

    def test_has_semaphore(self, mock_llm):
        """ImageAnalyzer instance has a threading.Semaphore."""
        from app.services.image_analyzer import ImageAnalyzer

        analyzer = ImageAnalyzer(llm_client=mock_llm, max_workers=2)
        assert hasattr(analyzer, "_semaphore")
        assert isinstance(analyzer._semaphore, threading.Semaphore)
