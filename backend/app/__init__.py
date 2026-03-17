"""
Campaign Ranker Engine — Flask应用工厂
"""

import os
import warnings

warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, request, session, send_from_directory
from flask_cors import CORS

from .config import Config
from .utils.logger import setup_logger, get_logger

# 前端 build 产物目录（生产模式由 Flask 托管）
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), '../../frontend/dist')


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

    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    @app.before_request
    def log_request():
        req_logger = get_logger('ranker.request')
        req_logger.debug(f"请求: {request.method} {request.path}")

    @app.after_request
    def audit_log(response):
        """审计日志：写操作 + 导出操作记录用户、动作、IP"""
        user = session.get('user', {})
        username = user.get('username', 'anonymous')
        is_write = request.method in ('POST', 'PUT', 'DELETE')
        is_export = request.path.startswith('/api/campaign/export')

        if is_write or is_export:
            audit_logger = get_logger('ranker.audit')
            audit_logger.info(
                f"AUDIT | user={username} | {request.method} {request.path} | "
                f"status={response.status_code} | ip={request.remote_addr}"
            )
        else:
            req_logger = get_logger('ranker.request')
            req_logger.debug(f"响应: {response.status_code}")
        return response

    # 注册蓝图
    from .api import campaign_bp
    app.register_blueprint(campaign_bp, url_prefix='/api/campaign')

    from .api.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    from .api.brandiction import brandiction_bp
    app.register_blueprint(brandiction_bp, url_prefix='/api/brandiction')

    @app.route('/health')
    def health():
        """增强健康检查：DB 连通性、磁盘空间、上传目录可写性"""
        import sqlite3 as _sqlite3
        checks = {"service": "Campaign Ranker Engine"}

        # DB connectivity
        try:
            db_path = os.path.join(Config.UPLOAD_FOLDER, "tasks.db")
            conn = _sqlite3.connect(db_path, timeout=10)
            conn.execute("SELECT 1")
            conn.close()
            checks["db"] = "ok"
        except Exception as e:
            checks["db"] = f"error: {e}"

        # Uploads dir writable
        try:
            test_file = os.path.join(Config.UPLOAD_FOLDER, ".health_check")
            with open(test_file, 'w') as f:
                f.write("ok")
            os.remove(test_file)
            checks["uploads_writable"] = "ok"
        except Exception as e:
            checks["uploads_writable"] = f"error: {e}"

        # Disk space
        try:
            stat = os.statvfs(Config.UPLOAD_FOLDER)
            free_gb = round((stat.f_bavail * stat.f_frsize) / (1024 ** 3), 2)
            checks["disk_free_gb"] = free_gb
            checks["disk"] = "warning: <1GB free" if free_gb < 1.0 else "ok"
        except Exception:
            checks["disk"] = "unknown"

        overall = "ok" if all(
            v == "ok" or isinstance(v, (int, float))
            for k, v in checks.items() if k != "service"
        ) else "degraded"
        return {"status": overall, **checks}

    # 生产模式：Flask 托管前端静态文件
    dist = os.path.abspath(FRONTEND_DIST)
    if os.path.isdir(dist):
        @app.route('/assets/<path:filename>')
        def serve_assets(filename):
            return send_from_directory(os.path.join(dist, 'assets'), filename)

        @app.route('/', defaults={'path': ''})
        @app.route('/<path:path>')
        def serve_frontend(path):
            # API / health 路由已注册，不会走到这里
            file_path = os.path.join(dist, path)
            if path and os.path.isfile(file_path):
                return send_from_directory(dist, path)
            return send_from_directory(dist, 'index.html')

        if should_log_startup:
            logger.info(f"前端静态文件托管: {dist}")
    else:
        if should_log_startup:
            logger.info(f"前端 dist 目录不存在 ({dist})，仅提供 API 服务")

    if should_log_startup:
        logger.info("Campaign Ranker Engine 启动完成")

    return app
