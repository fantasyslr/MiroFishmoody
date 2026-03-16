"""
Production readiness smoke test — 覆盖核心链路 + 安全修复项

链路: 登录 → 创建评审 → 查看状态 → 获取结果 → 导出 → 任务管理 → RBAC
安全: 上传路径不泄露、大文件拒绝、未登录拦截、session 失效
"""

import io
import json
import os
import pytest
from unittest.mock import patch, MagicMock

# conftest.py 已设置好测试环境变量
from app import create_app
from app.models.task import TaskManager, TaskStatus


@pytest.fixture
def app():
    application = create_app()
    application.config['TESTING'] = True
    # 重置 TaskManager 单例，避免跨测试污染
    TaskManager._instance = None
    yield application


@pytest.fixture
def client(app):
    with app.test_client() as c:
        yield c


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _login(client, username="slr", password="test-pass"):
    return client.post('/api/auth/login', json={
        "username": username,
        "password": password,
    })


def _login_as_user(client):
    return _login(client, "tester1", "test-pass")


# ──────────────────────────────────────────────
# Auth & Session
# ──────────────────────────────────────────────

class TestAuth:
    def test_login_success(self, client):
        resp = _login(client)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["username"] == "slr"
        assert data["role"] == "admin"

    def test_login_wrong_password(self, client):
        resp = _login(client, password="wrong")
        assert resp.status_code == 401

    def test_me_after_login(self, client):
        _login(client)
        resp = client.get('/api/auth/me')
        assert resp.status_code == 200
        assert resp.get_json()["username"] == "slr"

    def test_unauthenticated_access(self, client):
        resp = client.get('/api/campaign/tasks')
        assert resp.status_code == 401

    def test_logout(self, client):
        _login(client)
        resp = client.post('/api/auth/logout')
        assert resp.status_code == 200
        resp = client.get('/api/auth/me')
        assert resp.status_code == 401

    def test_session_invalidation_on_password_change(self, client):
        """验证 Fix 5: 密码变更后旧 session 失效"""
        _login(client)
        resp = client.get('/api/auth/me')
        assert resp.status_code == 200

        # 模拟密码变更（修改 USERS 字典）
        from app.auth import USERS
        old_pw = USERS["slr"]["password"]
        USERS["slr"]["password"] = "new-password-123"
        try:
            resp = client.get('/api/auth/me')
            # session 中的 _pw_ver 不再匹配，应被拒绝
            assert resp.status_code == 401
        finally:
            USERS["slr"]["password"] = old_pw


# ──────────────────────────────────────────────
# RBAC
# ──────────────────────────────────────────────

class TestRBAC:
    def test_admin_endpoint_as_user(self, client):
        """普通用户不能访问 admin_required 端点"""
        _login_as_user(client)
        resp = client.get('/api/brandiction/stats')
        assert resp.status_code == 403

    def test_admin_endpoint_as_admin(self, client):
        _login(client)
        resp = client.get('/api/brandiction/stats')
        assert resp.status_code == 200


# ──────────────────────────────────────────────
# Upload Security
# ──────────────────────────────────────────────

class TestUploadSecurity:
    def test_upload_no_path_leak(self, client):
        """验证 Fix 1: 上传响应不泄露服务器路径"""
        _login(client)
        # 生成一张真实的 1x1 PNG 图片以通过 PIL 校验
        from PIL import Image
        buf = io.BytesIO()
        Image.new('RGB', (1, 1), color='red').save(buf, format='PNG')
        buf.seek(0)
        data = {
            'file': (buf, 'test.png'),
            'set_id': 'test-set',
        }
        resp = client.post('/api/campaign/upload-image',
                           data=data, content_type='multipart/form-data')
        assert resp.status_code == 200
        body = resp.get_json()
        assert "path" not in body  # 不应有服务器路径
        assert "url" in body  # 应返回相对 URL
        assert body["url"].startswith("/api/campaign/image-file/")

    def test_upload_size_rejection(self, client):
        """验证 Fix 2: 超大文件被拒绝"""
        _login(client)
        # 6MB 的假图片
        big_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * (6 * 1024 * 1024)
        data = {
            'file': (io.BytesIO(big_data), 'big.png'),
        }
        resp = client.post('/api/campaign/upload-image',
                           data=data, content_type='multipart/form-data')
        assert resp.status_code in (400, 413)

    def test_upload_wrong_extension(self, client):
        _login(client)
        data = {
            'file': (io.BytesIO(b'not an image'), 'malware.exe'),
        }
        resp = client.post('/api/campaign/upload-image',
                           data=data, content_type='multipart/form-data')
        assert resp.status_code == 400


# ──────────────────────────────────────────────
# Health Check
# ──────────────────────────────────────────────

class TestHealth:
    def test_enhanced_health(self, client):
        resp = client.get('/health')
        assert resp.status_code == 200
        data = resp.get_json()
        assert "db" in data
        assert "disk" in data
        assert "uploads_writable" in data
        assert data["status"] in ("ok", "degraded")


# ──────────────────────────────────────────────
# Task Management
# ──────────────────────────────────────────────

class TestTaskManagement:
    def test_task_cancel(self, client, app):
        """验证任务取消端点"""
        _login(client)
        with app.app_context():
            tm = TaskManager()
            task_id = tm.create_task("campaign_evaluation", metadata={"set_id": "cancel-test"})
            tm.update_task(task_id, status=TaskStatus.PROCESSING)

        resp = client.post(f'/api/campaign/tasks/{task_id}/cancel')
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "cancelled"

    def test_task_retry(self, client, app):
        """验证任务重试端点"""
        _login(client)
        with app.app_context():
            tm = TaskManager()
            task_id = tm.create_task("campaign_evaluation", metadata={"set_id": "retry-test"})
            tm.fail_task(task_id, "test failure")

        resp = client.post(f'/api/campaign/tasks/{task_id}/retry')
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "retry_ready"

    def test_cancel_completed_task_rejected(self, client, app):
        """已完成任务不能取消"""
        _login(client)
        with app.app_context():
            tm = TaskManager()
            task_id = tm.create_task("campaign_evaluation", metadata={"set_id": "done-test"})
            tm.complete_task(task_id, {"ok": True})

        resp = client.post(f'/api/campaign/tasks/{task_id}/cancel')
        assert resp.status_code == 400

    def test_retry_non_failed_rejected(self, client, app):
        """非失败任务不能重试"""
        _login(client)
        with app.app_context():
            tm = TaskManager()
            task_id = tm.create_task("campaign_evaluation", metadata={"set_id": "pending-test"})

        # 先取消使之变成 FAILED 之外的状态 — 不行，create 后是 PENDING
        # PENDING 任务取消后变 FAILED，所以我们测试 COMPLETED
        with app.app_context():
            tm = TaskManager()
            tm.complete_task(task_id, {"ok": True})

        resp = client.post(f'/api/campaign/tasks/{task_id}/retry')
        assert resp.status_code == 400


# ──────────────────────────────────────────────
# Task Recovery After Restart
# ──────────────────────────────────────────────

class TestTaskRecovery:
    def test_processing_task_recovered_on_load(self, app):
        """验证 Fix 4: 服务重启后 PROCESSING 任务标记为 FAILED"""
        with app.app_context():
            tm = TaskManager()
            task_id = tm.create_task("campaign_evaluation", metadata={"set_id": "restart-test"})
            tm.update_task(task_id, status=TaskStatus.PROCESSING, message="运行中")

            # 模拟重启：销毁单例，重新实例化
            TaskManager._instance = None
            tm2 = TaskManager()
            task = tm2.get_task(task_id)
            assert task is not None
            assert task.status == TaskStatus.FAILED
            assert "服务重启" in task.error


# ──────────────────────────────────────────────
# Evaluation Flow (with mocked LLM)
# ──────────────────────────────────────────────

class TestEvaluationFlow:
    @patch('app.services.evaluation_orchestrator.LLMClient')
    @patch('app.services.evaluation_orchestrator.AudiencePanel')
    @patch('app.services.evaluation_orchestrator.PairwiseJudge')
    @patch('app.services.evaluation_orchestrator.CampaignScorer')
    @patch('app.services.evaluation_orchestrator.SummaryGenerator')
    def test_submit_and_check_status(self, mock_summary, mock_scorer,
                                      mock_judge, mock_panel, mock_llm, client):
        """提交评审 → 查询状态（异步线程，只测提交接口）"""
        _login(client)
        payload = {
            "campaigns": [
                {"name": "Campaign A", "core_message": "message A", "product_line": "colored_lenses"},
                {"name": "Campaign B", "core_message": "message B", "product_line": "colored_lenses"},
            ],
            "set_id": "smoke-eval-test",
        }
        resp = client.post('/api/campaign/evaluate', json=payload)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "task_id" in data
        assert data["set_id"] == "smoke-eval-test"

        # 查询状态
        resp = client.get(f'/api/campaign/evaluate/status/{data["task_id"]}')
        assert resp.status_code == 200

    def test_duplicate_set_id_rejected(self, client, app):
        """重复 set_id 被拒绝"""
        _login(client)

        # 预植入一个结果
        from app.api.campaign import _evaluation_store
        _evaluation_store["dup-test"] = {"dummy": True}

        payload = {
            "campaigns": [
                {"name": "A", "core_message": "msg", "product_line": "colored_lenses"},
                {"name": "B", "core_message": "msg", "product_line": "colored_lenses"},
            ],
            "set_id": "dup-test",
        }
        resp = client.post('/api/campaign/evaluate', json=payload)
        assert resp.status_code == 409

        # 清理
        _evaluation_store.pop("dup-test", None)

    def test_export_requires_auth(self, client):
        """导出需要登录"""
        resp = client.get('/api/campaign/export/any-id')
        assert resp.status_code == 401
