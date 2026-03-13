"""
API路由模块
"""

from flask import Blueprint

campaign_bp = Blueprint('campaign', __name__)

from . import campaign  # noqa: E402, F401
