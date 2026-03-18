"""
TDD tests for Plan 19-03 Task 2:
POST /api/campaign/evaluate validates brief_type and returns 400 on unknown values.
"""

import pytest
import json
from unittest.mock import patch, MagicMock


@pytest.fixture
def app():
    from app import create_app
    from app.models.task import TaskManager
    application = create_app()
    application.config['TESTING'] = True
    TaskManager._instance = None
    yield application


@pytest.fixture
def client(app):
    with app.test_client() as c:
        c.post('/api/auth/login', json={"username": "slr", "password": "test-pass"})
        yield c


def _minimal_campaigns():
    return [
        {"campaign_id": "c1", "name": "Campaign A", "description": "desc A"},
        {"campaign_id": "c2", "name": "Campaign B", "description": "desc B"},
    ]


class TestBriefTypeValidation:
    """API 层 brief_type 枚举校验"""

    def test_unknown_brief_type_returns_400(self, client):
        """POST /evaluate 传入未知 brief_type 返回 HTTP 400"""
        with patch('app.api.campaign.threading.Thread'), \
             patch('app.api.campaign._load_result', return_value=None):
            resp = client.post(
                '/api/campaign/evaluate',
                data=json.dumps({
                    "set_id": "test_set_400",
                    "campaigns": _minimal_campaigns(),
                    "brief_type": "invalid_xyz",
                }),
                content_type='application/json',
            )
        assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.data}"
        body = json.loads(resp.data)
        assert 'error' in body
        assert 'brief_type' in body['error'].lower() or 'brief_type' in body['error']
        assert 'invalid_xyz' in body['error']

    def test_valid_brief_type_brand_returns_202(self, client):
        """POST /evaluate 传入 brief_type='brand' 返回 202"""
        with patch('app.api.campaign.threading.Thread') as mock_thread, \
             patch('app.api.campaign._load_result', return_value=None), \
             patch('app.api.campaign._store_lock') as mock_lock:
            mock_lock.__enter__ = MagicMock(return_value=None)
            mock_lock.__exit__ = MagicMock(return_value=False)
            resp = client.post(
                '/api/campaign/evaluate',
                data=json.dumps({
                    "set_id": "test_set_202_brand",
                    "campaigns": _minimal_campaigns(),
                    "brief_type": "brand",
                }),
                content_type='application/json',
            )
        assert resp.status_code == 202, f"Expected 202, got {resp.status_code}: {resp.data}"

    def test_missing_brief_type_backward_compatible(self, client):
        """POST /evaluate 不传 brief_type 返回 202（向后兼容）"""
        with patch('app.api.campaign.threading.Thread') as mock_thread, \
             patch('app.api.campaign._load_result', return_value=None), \
             patch('app.api.campaign._store_lock') as mock_lock:
            mock_lock.__enter__ = MagicMock(return_value=None)
            mock_lock.__exit__ = MagicMock(return_value=False)
            resp = client.post(
                '/api/campaign/evaluate',
                data=json.dumps({
                    "set_id": "test_set_no_brief",
                    "campaigns": _minimal_campaigns(),
                }),
                content_type='application/json',
            )
        assert resp.status_code == 202, f"Expected 202, got {resp.status_code}: {resp.data}"

    def test_error_message_lists_valid_values(self, client):
        """400 响应体包含 brand / seeding / conversion"""
        with patch('app.api.campaign.threading.Thread'), \
             patch('app.api.campaign._load_result', return_value=None):
            resp = client.post(
                '/api/campaign/evaluate',
                data=json.dumps({
                    "set_id": "test_set_err_msg",
                    "campaigns": _minimal_campaigns(),
                    "brief_type": "unknown_xyz",
                }),
                content_type='application/json',
            )
        assert resp.status_code == 400
        body = json.loads(resp.data)
        error_msg = body.get('error', '')
        # Should mention all three valid values
        assert 'brand' in error_msg
        assert 'seeding' in error_msg
        assert 'conversion' in error_msg
