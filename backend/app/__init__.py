"""
Campaign Ranker Engine — Flask应用工厂
"""

import os
import warnings

warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, request
from flask_cors import CORS

from .config import Config
from .utils.logger import setup_logger, get_logger


def create_app(config_class=Config):
    """Flask应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False

    logger = setup_logger('ranker')

    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process

    if should_log_startup:
        logger.info("=" * 50)
        logger.info("Campaign Ranker Engine 启动中...")
        logger.info("=" * 50)

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    @app.before_request
    def log_request():
        req_logger = get_logger('ranker.request')
        req_logger.debug(f"请求: {request.method} {request.path}")

    @app.after_request
    def log_response(response):
        req_logger = get_logger('ranker.request')
        req_logger.debug(f"响应: {response.status_code}")
        return response

    # 注册蓝图
    from .api import campaign_bp
    app.register_blueprint(campaign_bp, url_prefix='/api/campaign')

    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'Campaign Ranker Engine'}

    if should_log_startup:
        logger.info("Campaign Ranker Engine 启动完成")

    return app
