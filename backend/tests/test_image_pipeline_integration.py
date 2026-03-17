"""Integration test: API URL image paths are resolved, not silently dropped.

Regression tests for BUG-01 (silent image dropout) and BUG-02 (high-res overflow).
"""

import base64
from io import BytesIO
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image


def test_audience_panel_resolves_api_url(tmp_path):
    """BUG-01 regression: AudiencePanel must not use os.path.exists on API URLs."""
    # Create a real image file
    img_dir = tmp_path / "abc123"
    img_dir.mkdir()
    img_path = img_dir / "photo.jpg"
    Image.new("RGB", (100, 100), "red").save(str(img_path))

    # Patch IMAGES_DIR to tmp_path so resolve_image_path finds the file
    with patch("app.utils.image_helpers.IMAGES_DIR", str(tmp_path)):
        from app.utils.image_helpers import resolve_image_path

        result = resolve_image_path("/api/campaign/image-file/abc123/photo.jpg")
        assert result is not None, "resolve_image_path returned None for valid API URL"
        assert result.endswith("photo.jpg")


def test_high_res_image_gets_resized(tmp_path):
    """BUG-02 regression: images > 1024px must be resized before base64."""
    img_path = tmp_path / "big.jpg"
    Image.new("RGB", (4000, 3000), "blue").save(str(img_path))

    from app.utils.image_helpers import image_to_base64_part

    result = image_to_base64_part(str(img_path), max_dimension=1024)
    assert result is not None, "image_to_base64_part returned None for valid image"
    assert result["type"] == "image_url"

    # Verify the base64 data decodes to a resized image
    data = result["image_url"]["url"].split(",", 1)[1]
    decoded = base64.b64decode(data)
    resized = Image.open(BytesIO(decoded))
    assert max(resized.size) <= 1024, f"Image not resized: {resized.size}"


def test_pairwise_judge_build_image_parts_resolves_url(tmp_path):
    """BUG-01 regression: _build_image_parts must resolve API URLs."""
    img_dir = tmp_path / "set1"
    img_dir.mkdir()
    img_path = img_dir / "visual.png"
    Image.new("RGB", (200, 200), "green").save(str(img_path))

    with patch("app.utils.image_helpers.IMAGES_DIR", str(tmp_path)):
        from app.services.pairwise_judge import _build_image_parts

        # Create mock campaign with API URL path
        campaign = MagicMock()
        campaign.image_paths = ["/api/campaign/image-file/set1/visual.png"]
        parts = _build_image_parts(campaign, "A")
        assert len(parts) == 1, f"Expected 1 image part, got {len(parts)}"
        assert parts[0]["type"] == "image_url"


def test_small_image_not_resized(tmp_path):
    """Small images should pass through without resize."""
    img_path = tmp_path / "small.jpg"
    Image.new("RGB", (500, 400), "yellow").save(str(img_path))

    from app.utils.image_helpers import image_to_base64_part

    result = image_to_base64_part(str(img_path), max_dimension=1024)
    assert result is not None

    data = result["image_url"]["url"].split(",", 1)[1]
    decoded = base64.b64decode(data)
    img = Image.open(BytesIO(decoded))
    # Should keep original size
    assert img.size == (500, 400)


def test_invalid_api_url_returns_none():
    """Non-API URLs should return None, not crash."""
    from app.utils.image_helpers import resolve_image_path

    assert resolve_image_path("/some/random/path.jpg") is None
    assert resolve_image_path("") is None
    assert resolve_image_path("https://example.com/image.jpg") is None
