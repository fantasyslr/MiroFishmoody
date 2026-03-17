"""
Shared image utility functions for the Campaign Ranker Engine.

Provides:
- resolve_image_path: API URL to disk path resolution with security checks
- image_to_base64_part: Image to base64 OpenAI Vision content part with optional resize
"""

import base64
import logging
import os
from io import BytesIO
from typing import Any, Dict, Optional

from PIL import Image
from werkzeug.utils import secure_filename

from app.config import Config

logger = logging.getLogger(__name__)

IMAGES_DIR = os.path.join(Config.UPLOAD_FOLDER, "images")


def resolve_image_path(image_url: str) -> Optional[str]:
    """
    Convert /api/campaign/image-file/{set_id}/{filename} URL to disk path.

    Security:
    - Only accepts /api/campaign/image-file/ prefix URLs
    - Uses werkzeug.secure_filename to sanitize set_id and filename
    - Uses os.path.realpath containment check within IMAGES_DIR

    Returns disk path if file exists, else None.
    """
    prefix = "/api/campaign/image-file/"
    if not image_url.startswith(prefix):
        return None

    remainder = image_url[len(prefix):]
    parts = remainder.split("/", 1)
    if len(parts) != 2:
        return None

    set_id_raw, filename_raw = parts

    # Sanitize with secure_filename to block ../ traversal
    set_id = secure_filename(set_id_raw)
    filename = secure_filename(filename_raw)
    if not set_id or not filename:
        return None

    path = os.path.join(IMAGES_DIR, set_id, filename)

    # realpath containment: resolved path must be within IMAGES_DIR
    real_path = os.path.realpath(path)
    real_images_dir = os.path.realpath(IMAGES_DIR)
    if not real_path.startswith(real_images_dir + os.sep):
        logger.warning(f"Path traversal attempt blocked: {image_url} -> {real_path}")
        return None

    if os.path.isfile(real_path):
        return real_path
    return None


def image_to_base64_part(
    file_path: str, max_dimension: int = 1024
) -> Optional[Dict[str, Any]]:
    """
    Read an image file and convert to OpenAI Vision content part.

    If the image's max dimension exceeds max_dimension, resize it down
    (preserving aspect ratio) before encoding.

    Returns:
        {"type": "image_url", "image_url": {"url": "data:{mime};base64,{data}"}}
        or None on error.
    """
    try:
        img = Image.open(file_path)
        width, height = img.size

        # Determine MIME from file extension
        ext = file_path.rsplit(".", 1)[-1].lower()
        if ext in ("jpg", "jpeg"):
            mime = "image/jpeg"
            save_format = "JPEG"
        elif ext == "png":
            mime = "image/png"
            save_format = "PNG"
        elif ext == "gif":
            mime = "image/gif"
            save_format = "GIF"
        elif ext == "webp":
            mime = "image/webp"
            save_format = "WEBP"
        else:
            mime = f"image/{ext}"
            save_format = ext.upper()

        if max(width, height) > max_dimension:
            # Resize preserving aspect ratio
            img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)
            buf = BytesIO()
            img.save(buf, format=save_format, quality=85)
            data = base64.b64encode(buf.getvalue()).decode()
        else:
            # No resize needed -- read raw bytes
            with open(file_path, "rb") as f:
                data = base64.b64encode(f.read()).decode()

        return {
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{data}"},
        }
    except Exception as e:
        logger.warning(f"Failed to read image {file_path}: {e}")
        return None
