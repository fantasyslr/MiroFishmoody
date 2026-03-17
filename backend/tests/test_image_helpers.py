"""
Tests for backend/app/utils/image_helpers.py

Covers:
- resolve_image_path: API URL -> disk path conversion with security checks
- image_to_base64_part: base64 encoding with optional resize
"""

import base64
import json
import os
from io import BytesIO
from unittest.mock import patch

import pytest
from PIL import Image


# ---------------------------------------------------------------------------
# resolve_image_path tests
# ---------------------------------------------------------------------------


class TestResolveImagePath:
    """Tests for resolve_image_path()."""

    def _make_image_file(self, tmp_path, set_id, filename):
        """Helper: create a dummy file at IMAGES_DIR/set_id/filename."""
        d = tmp_path / set_id
        d.mkdir(parents=True, exist_ok=True)
        f = d / filename
        f.write_bytes(b"\xff\xd8fake-jpeg-data")
        return str(f)

    def test_valid_url_existing_file(self, tmp_path):
        """Valid API URL pointing to an existing file returns disk path."""
        from app.utils.image_helpers import resolve_image_path

        self._make_image_file(tmp_path, "abc123", "photo.jpg")
        with patch("app.utils.image_helpers.IMAGES_DIR", str(tmp_path)):
            result = resolve_image_path("/api/campaign/image-file/abc123/photo.jpg")
        assert result is not None
        assert result.endswith("abc123/photo.jpg")

    def test_valid_url_nonexistent_file(self, tmp_path):
        """Valid API URL but file does not exist on disk returns None."""
        from app.utils.image_helpers import resolve_image_path

        with patch("app.utils.image_helpers.IMAGES_DIR", str(tmp_path)):
            result = resolve_image_path("/api/campaign/image-file/abc123/photo.jpg")
        assert result is None

    def test_non_api_url_returns_none(self, tmp_path):
        """Non-API URL prefix returns None."""
        from app.utils.image_helpers import resolve_image_path

        with patch("app.utils.image_helpers.IMAGES_DIR", str(tmp_path)):
            result = resolve_image_path("/some/random/path.jpg")
        assert result is None

    def test_path_traversal_blocked(self, tmp_path):
        """Path traversal attempt returns None."""
        from app.utils.image_helpers import resolve_image_path

        with patch("app.utils.image_helpers.IMAGES_DIR", str(tmp_path)):
            result = resolve_image_path(
                "/api/campaign/image-file/../../../etc/passwd"
            )
        assert result is None

    def test_empty_string_returns_none(self, tmp_path):
        """Empty string returns None."""
        from app.utils.image_helpers import resolve_image_path

        with patch("app.utils.image_helpers.IMAGES_DIR", str(tmp_path)):
            result = resolve_image_path("")
        assert result is None

    def test_missing_filename_returns_none(self, tmp_path):
        """URL with only set_id and no filename returns None."""
        from app.utils.image_helpers import resolve_image_path

        with patch("app.utils.image_helpers.IMAGES_DIR", str(tmp_path)):
            result = resolve_image_path("/api/campaign/image-file/abc123")
        assert result is None


# ---------------------------------------------------------------------------
# image_to_base64_part tests
# ---------------------------------------------------------------------------


def _create_test_image(path, width, height, fmt="JPEG"):
    """Create a real image file with given dimensions."""
    img = Image.new("RGB", (width, height), color=(128, 64, 32))
    img.save(str(path), format=fmt)
    return str(path)


class TestImageToBase64Part:
    """Tests for image_to_base64_part()."""

    def test_large_image_resized(self, tmp_path):
        """2048x1536 JPEG is resized so max dimension is 1024."""
        from app.utils.image_helpers import image_to_base64_part

        fpath = _create_test_image(tmp_path / "big.jpg", 2048, 1536)
        result = image_to_base64_part(fpath)
        assert result is not None
        # Decode and check dimensions
        data_url = result["image_url"]["url"]
        b64_data = data_url.split(",", 1)[1]
        img = Image.open(BytesIO(base64.b64decode(b64_data)))
        assert max(img.size) == 1024

    def test_small_image_not_resized(self, tmp_path):
        """800x600 JPEG is returned at original dimensions."""
        from app.utils.image_helpers import image_to_base64_part

        fpath = _create_test_image(tmp_path / "small.jpg", 800, 600)
        result = image_to_base64_part(fpath)
        assert result is not None
        data_url = result["image_url"]["url"]
        b64_data = data_url.split(",", 1)[1]
        img = Image.open(BytesIO(base64.b64decode(b64_data)))
        assert img.size == (800, 600)

    def test_nonexistent_path_returns_none(self):
        """Nonexistent file path returns None."""
        from app.utils.image_helpers import image_to_base64_part

        result = image_to_base64_part("/nonexistent/path/image.jpg")
        assert result is None

    def test_return_dict_structure(self, tmp_path):
        """Return dict has correct keys and data URL prefix."""
        from app.utils.image_helpers import image_to_base64_part

        fpath = _create_test_image(tmp_path / "test.jpg", 100, 100)
        result = image_to_base64_part(fpath)
        assert result["type"] == "image_url"
        assert result["image_url"]["url"].startswith("data:image/")

    def test_png_image_mime(self, tmp_path):
        """PNG image produces data:image/png MIME type."""
        from app.utils.image_helpers import image_to_base64_part

        fpath = _create_test_image(tmp_path / "test.png", 200, 200, fmt="PNG")
        result = image_to_base64_part(fpath)
        assert result is not None
        assert result["image_url"]["url"].startswith("data:image/png")

    def test_large_png_resized(self, tmp_path):
        """Large PNG is also resized correctly."""
        from app.utils.image_helpers import image_to_base64_part

        fpath = _create_test_image(tmp_path / "big.png", 3000, 2000, fmt="PNG")
        result = image_to_base64_part(fpath, max_dimension=512)
        assert result is not None
        data_url = result["image_url"]["url"]
        b64_data = data_url.split(",", 1)[1]
        img = Image.open(BytesIO(base64.b64decode(b64_data)))
        assert max(img.size) == 512
