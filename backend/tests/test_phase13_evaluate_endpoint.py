"""Phase 13 BUG-05: /api/campaign/evaluate 端点集成测试"""
import json
import pytest
from unittest.mock import patch, MagicMock

# conftest.py 已设置好测试环境变量
from app import create_app
from app.models.task import TaskManager


@pytest.fixture
def app():
    application = create_app()
    application.config['TESTING'] = True
    TaskManager._instance = None
    yield application


@pytest.fixture
def client(app):
    with app.test_client() as c:
        yield c


def _login(client, username="slr", password="test-pass"):
    return client.post('/api/auth/login', json={
        "username": username,
        "password": password,
    })


def test_evaluate_endpoint_accepts_evaluate_payload(client):
    """POST /evaluate 接受 EvaluatePayload 形状（campaign_id + description），返回 202"""
    _login(client)

    payload = {
        "set_id": "phase13-test-set-001",
        "campaigns": [
            {
                "campaign_id": "uuid-test-001",
                "name": "测试方案A",
                "description": "这是方案A的核心卖点",
                "image_paths": [],
            },
            {
                "campaign_id": "uuid-test-002",
                "name": "测试方案B",
                "description": "这是方案B的核心卖点",
                "image_paths": [],
            },
        ],
        "category": "colored_lenses",
    }

    # Mock the orchestrator to avoid actual LLM calls in tests
    with patch('app.api.campaign.EvaluationOrchestrator') as MockOrchestrator:
        mock_instance = MagicMock()
        MockOrchestrator.return_value = mock_instance

        resp = client.post(
            "/api/campaign/evaluate",
            data=json.dumps(payload),
            content_type="application/json",
        )

    assert resp.status_code == 202, (
        f"Expected 202, got {resp.status_code}: {resp.get_data(as_text=True)}"
    )
    data = resp.get_json()
    assert "task_id" in data
    assert "set_id" in data
