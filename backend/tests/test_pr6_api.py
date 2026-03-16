"""
Brandiction PR6 — Request-Level API Tests

覆盖所有 18 个 brandiction 端点的 HTTP 行为：
  - 认证强制（login_required / admin_required）
  - JSON 解析和参数校验
  - 成功路径返回值结构
  - 错误响应（400 / 401 / 403 / 404）
"""

import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.services.brandiction_store import BrandictionStore


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

def _make_app():
    """创建测试用 Flask app，使用临时数据库"""
    BrandictionStore._reset_instance()
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    app = create_app()
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'

    # Force BrandictionStore to use temp db
    BrandictionStore._reset_instance()
    with app.app_context():
        store = BrandictionStore(db_path=db_path)

    return app, db_path


def _cleanup(db_path):
    BrandictionStore._reset_instance()
    try:
        os.unlink(db_path)
    except OSError:
        pass


def _user_session(client):
    """Set a normal user session"""
    from app.auth import _password_version
    with client.session_transaction() as sess:
        sess['user'] = {"username": "tester1", "display_name": "Tester1", "role": "user", "_pw_ver": _password_version("tester1")}


def _admin_session(client):
    """Set an admin user session"""
    from app.auth import _password_version
    with client.session_transaction() as sess:
        sess['user'] = {"username": "slr", "display_name": "Liren", "role": "admin", "_pw_ver": _password_version("slr")}


# ------------------------------------------------------------------
# Auth enforcement: 401 without session, 403 for non-admin
# ------------------------------------------------------------------

class TestAuthEnforcement:
    """验证每个端点的认证要求"""

    def test_import_history_requires_admin(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                # 未登录 → 401
                r = c.post('/api/brandiction/import-history', json={"interventions": []})
                assert r.status_code == 401

                # 普通用户 → 403
                _user_session(c)
                r = c.post('/api/brandiction/import-history', json={"interventions": []})
                assert r.status_code == 403

                # 管理员 → 200
                _admin_session(c)
                r = c.post('/api/brandiction/import-history', json={"interventions": []})
                assert r.status_code == 200
        finally:
            _cleanup(db)

    def test_import_csv_requires_admin(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                r = c.post('/api/brandiction/import-csv?type=interventions',
                           data="col1,col2", content_type='text/plain')
                assert r.status_code == 401

                _user_session(c)
                r = c.post('/api/brandiction/import-csv?type=interventions',
                           data="col1,col2", content_type='text/plain')
                assert r.status_code == 403
        finally:
            _cleanup(db)

    def test_list_runs_requires_login(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                r = c.get('/api/brandiction/history')
                assert r.status_code == 401

                _user_session(c)
                r = c.get('/api/brandiction/history')
                assert r.status_code == 200
        finally:
            _cleanup(db)

    def test_signals_requires_login(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                r = c.get('/api/brandiction/signals')
                assert r.status_code == 401

                _user_session(c)
                r = c.get('/api/brandiction/signals')
                assert r.status_code == 200
        finally:
            _cleanup(db)

    def test_competitor_events_requires_admin(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                # 未登录 → 401
                r = c.get('/api/brandiction/competitor-events')
                assert r.status_code == 401

                # 普通用户 → 403
                _user_session(c)
                r = c.get('/api/brandiction/competitor-events')
                assert r.status_code == 403

                # 管理员 → 200
                _admin_session(c)
                r = c.get('/api/brandiction/competitor-events')
                assert r.status_code == 200
        finally:
            _cleanup(db)

    def test_stats_requires_admin(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                r = c.get('/api/brandiction/stats')
                assert r.status_code == 401

                _user_session(c)
                r = c.get('/api/brandiction/stats')
                assert r.status_code == 403

                _admin_session(c)
                r = c.get('/api/brandiction/stats')
                assert r.status_code == 200
        finally:
            _cleanup(db)

    def test_brand_state_requires_login(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                r = c.get('/api/brandiction/brand-state')
                assert r.status_code == 401

                _user_session(c)
                r = c.get('/api/brandiction/brand-state')
                assert r.status_code == 200
        finally:
            _cleanup(db)

    def test_brand_state_latest_requires_login(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                r = c.get('/api/brandiction/brand-state/latest')
                assert r.status_code == 401
        finally:
            _cleanup(db)

    def test_brand_state_build_requires_admin(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                r = c.post('/api/brandiction/brand-state/build',
                           json={"as_of_date": "2025-06-01"})
                assert r.status_code == 401

                _user_session(c)
                r = c.post('/api/brandiction/brand-state/build',
                           json={"as_of_date": "2025-06-01"})
                assert r.status_code == 403
        finally:
            _cleanup(db)

    def test_replay_requires_admin(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                r = c.post('/api/brandiction/replay', json={})
                assert r.status_code == 401

                _user_session(c)
                r = c.post('/api/brandiction/replay', json={})
                assert r.status_code == 403
        finally:
            _cleanup(db)

    def test_predict_requires_login(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                r = c.post('/api/brandiction/predict', json={"theme": "science"})
                assert r.status_code == 401
        finally:
            _cleanup(db)

    def test_probability_board_requires_login(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                r = c.post('/api/brandiction/probability-board',
                           json={"plans": [{"theme": "science"}]})
                assert r.status_code == 401
        finally:
            _cleanup(db)

    def test_backtest_requires_admin(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                r = c.post('/api/brandiction/backtest', json={})
                assert r.status_code == 401

                _user_session(c)
                r = c.post('/api/brandiction/backtest', json={})
                assert r.status_code == 403
        finally:
            _cleanup(db)

    def test_simulate_requires_login(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                r = c.post('/api/brandiction/simulate',
                           json={"steps": [{"theme": "science"}]})
                assert r.status_code == 401
        finally:
            _cleanup(db)

    def test_compare_scenarios_requires_login(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                r = c.post('/api/brandiction/compare-scenarios',
                           json={"scenarios": [{"name": "a", "steps": [{"theme": "science"}]}]})
                assert r.status_code == 401
        finally:
            _cleanup(db)


# ------------------------------------------------------------------
# Input validation: 400 on bad input
# ------------------------------------------------------------------

class TestInputValidation:
    def test_import_history_empty_body(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _admin_session(c)
                r = c.post('/api/brandiction/import-history',
                           data='', content_type='application/json')
                assert r.status_code == 400
        finally:
            _cleanup(db)

    def test_import_csv_missing_type(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _admin_session(c)
                r = c.post('/api/brandiction/import-csv',
                           data="col1,col2", content_type='text/plain')
                assert r.status_code == 400
                assert "type" in r.get_json()["error"]
        finally:
            _cleanup(db)

    def test_import_csv_invalid_type(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _admin_session(c)
                r = c.post('/api/brandiction/import-csv?type=invalid',
                           data="col1,col2", content_type='text/plain')
                assert r.status_code == 400
        finally:
            _cleanup(db)

    def test_import_csv_empty_body(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _admin_session(c)
                r = c.post('/api/brandiction/import-csv?type=interventions',
                           data='', content_type='text/plain')
                assert r.status_code == 400
        finally:
            _cleanup(db)

    def test_brand_state_build_missing_date(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _admin_session(c)
                r = c.post('/api/brandiction/brand-state/build', json={})
                assert r.status_code == 400
                assert "as_of_date" in r.get_json()["error"]
        finally:
            _cleanup(db)

    def test_predict_empty_body(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.post('/api/brandiction/predict',
                           data='', content_type='application/json')
                assert r.status_code == 400
        finally:
            _cleanup(db)

    def test_predict_missing_theme(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.post('/api/brandiction/predict', json={"budget": 50000})
                assert r.status_code == 400
                assert "theme" in r.get_json()["error"]
        finally:
            _cleanup(db)

    def test_predict_whitespace_theme(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.post('/api/brandiction/predict', json={"theme": "   "})
                assert r.status_code == 400
        finally:
            _cleanup(db)

    def test_probability_board_missing_plans(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.post('/api/brandiction/probability-board', json={})
                assert r.status_code == 400
                assert "plans" in r.get_json()["error"]
        finally:
            _cleanup(db)

    def test_probability_board_empty_plans(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.post('/api/brandiction/probability-board', json={"plans": []})
                assert r.status_code == 400
        finally:
            _cleanup(db)

    def test_probability_board_plan_missing_theme(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.post('/api/brandiction/probability-board',
                           json={"plans": [{"budget": 50000}]})
                assert r.status_code == 400
                assert "theme" in r.get_json()["error"]
        finally:
            _cleanup(db)

    def test_simulate_missing_steps(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.post('/api/brandiction/simulate', json={})
                assert r.status_code == 400
                assert "steps" in r.get_json()["error"]
        finally:
            _cleanup(db)

    def test_simulate_empty_steps(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.post('/api/brandiction/simulate', json={"steps": []})
                assert r.status_code == 400
        finally:
            _cleanup(db)

    def test_simulate_step_missing_theme(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.post('/api/brandiction/simulate',
                           json={"steps": [{"budget": 50000}]})
                assert r.status_code == 400
                assert "theme" in r.get_json()["error"]
        finally:
            _cleanup(db)

    def test_compare_scenarios_missing(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.post('/api/brandiction/compare-scenarios', json={})
                assert r.status_code == 400
                assert "scenarios" in r.get_json()["error"]
        finally:
            _cleanup(db)

    def test_compare_scenarios_empty(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.post('/api/brandiction/compare-scenarios',
                           json={"scenarios": []})
                assert r.status_code == 400
        finally:
            _cleanup(db)


# ------------------------------------------------------------------
# Success paths: verify response structure
# ------------------------------------------------------------------

class TestSuccessPaths:
    def _seed_data(self, app):
        """Seed test data via API"""
        with app.test_client() as c:
            _admin_session(c)
            c.post('/api/brandiction/import-history', json={
                "interventions": [
                    {
                        "intervention_id": "iv-test-1",
                        "run_id": "run-1",
                        "product_line": "moodyplus",
                        "date_start": "2025-06-01",
                        "date_end": "2025-06-30",
                        "theme": "science",
                        "channel_mix": ["bilibili", "wechat"],
                        "budget": 50000,
                        "audience_segment": "general",
                    }
                ],
                "outcomes": [
                    {
                        "outcome_id": "oc-test-1",
                        "intervention_id": "iv-test-1",
                        "brand_lift": 0.15,
                        "comment_sentiment": 0.4,
                        "ctr": 0.05,
                    }
                ],
                "signals": [
                    {
                        "signal_id": "sig-test-1",
                        "date": "2025-05-01",
                        "dimension": "science_credibility",
                        "value": 0.6,
                    },
                    {
                        "signal_id": "sig-test-2",
                        "date": "2025-05-15",
                        "dimension": "comfort_trust",
                        "value": 0.5,
                    }
                ],
                "competitor_events": [
                    {
                        "event_id": "ev-test-1",
                        "date": "2025-06-15",
                        "competitor": "acuvue",
                        "event_type": "price_cut",
                        "impact_estimate": "medium",
                    }
                ],
            })

    def test_import_history_response(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _admin_session(c)
                r = c.post('/api/brandiction/import-history', json={
                    "interventions": [
                        {"intervention_id": "iv1", "run_id": "r1", "theme": "science"}
                    ],
                })
                assert r.status_code == 200
                data = r.get_json()
                assert "imported" in data
                assert data["imported"]["interventions"] == 1
                assert "errors" in data
                assert "warnings" in data
        finally:
            _cleanup(db)

    def test_import_csv_interventions(self):
        app, db = _make_app()
        try:
            csv = "intervention_id,run_id,theme\niv-csv-1,r1,science\niv-csv-2,r1,beauty"
            with app.test_client() as c:
                _admin_session(c)
                r = c.post('/api/brandiction/import-csv?type=interventions',
                           data=csv, content_type='text/plain')
                assert r.status_code == 200
                data = r.get_json()
                assert data["imported"]["interventions"] == 2
        finally:
            _cleanup(db)

    def test_list_runs(self):
        app, db = _make_app()
        try:
            self._seed_data(app)
            with app.test_client() as c:
                _user_session(c)
                r = c.get('/api/brandiction/history')
                assert r.status_code == 200
                data = r.get_json()
                assert "run_ids" in data
                assert "count" in data
                assert "run-1" in data["run_ids"]
        finally:
            _cleanup(db)

    def test_get_history_by_run_id(self):
        app, db = _make_app()
        try:
            self._seed_data(app)
            with app.test_client() as c:
                _user_session(c)
                r = c.get('/api/brandiction/history/run-1')
                assert r.status_code == 200
                data = r.get_json()
                assert data["run_id"] == "run-1"
                assert data["intervention_count"] == 1
                assert len(data["items"]) == 1
                item = data["items"][0]
                assert "intervention" in item
                assert "outcomes" in item
                assert "evidence" in item
        finally:
            _cleanup(db)

    def test_get_history_not_found(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.get('/api/brandiction/history/nonexistent')
                assert r.status_code == 404
        finally:
            _cleanup(db)

    def test_list_signals(self):
        app, db = _make_app()
        try:
            self._seed_data(app)
            with app.test_client() as c:
                _user_session(c)
                r = c.get('/api/brandiction/signals')
                assert r.status_code == 200
                data = r.get_json()
                assert "signals" in data
                assert "count" in data
                assert data["count"] == 2
        finally:
            _cleanup(db)

    def test_list_signals_with_filter(self):
        app, db = _make_app()
        try:
            self._seed_data(app)
            with app.test_client() as c:
                _user_session(c)
                r = c.get('/api/brandiction/signals?dimension=science_credibility')
                assert r.status_code == 200
                data = r.get_json()
                assert data["count"] == 1
        finally:
            _cleanup(db)

    def test_competitor_events(self):
        app, db = _make_app()
        try:
            self._seed_data(app)
            with app.test_client() as c:
                _admin_session(c)
                r = c.get('/api/brandiction/competitor-events')
                assert r.status_code == 200
                data = r.get_json()
                assert data["count"] == 1
                assert data["events"][0]["competitor"] == "acuvue"
        finally:
            _cleanup(db)

    def test_stats(self):
        app, db = _make_app()
        try:
            self._seed_data(app)
            with app.test_client() as c:
                _admin_session(c)
                r = c.get('/api/brandiction/stats')
                assert r.status_code == 200
                data = r.get_json()
                assert data["interventions_count"] == 1
                assert data["outcomes_count"] == 1
                assert data["signals_count"] == 2
                assert data["competitor_events_count"] == 1
                assert "market_coverage" in data
                assert "platform_coverage" in data
                assert "weakest_dimensions" in data
        finally:
            _cleanup(db)

    def test_brand_state_list(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.get('/api/brandiction/brand-state')
                assert r.status_code == 200
                data = r.get_json()
                assert "states" in data
                assert "count" in data
        finally:
            _cleanup(db)

    def test_brand_state_latest_empty(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.get('/api/brandiction/brand-state/latest')
                assert r.status_code == 404
        finally:
            _cleanup(db)

    def test_brand_state_build(self):
        app, db = _make_app()
        try:
            self._seed_data(app)
            with app.test_client() as c:
                _admin_session(c)
                r = c.post('/api/brandiction/brand-state/build',
                           json={"as_of_date": "2025-06-01"})
                assert r.status_code == 200
                data = r.get_json()
                assert "state_id" in data
                assert "perception" in data
                assert "science_credibility" in data["perception"]
        finally:
            _cleanup(db)

    def test_replay(self):
        app, db = _make_app()
        try:
            self._seed_data(app)
            with app.test_client() as c:
                _admin_session(c)
                r = c.post('/api/brandiction/replay', json={})
                assert r.status_code == 200
                data = r.get_json()
                assert "states" in data
                assert "count" in data
                assert data["count"] >= 2  # initial + at least 1 intervention
        finally:
            _cleanup(db)

    def test_predict(self):
        app, db = _make_app()
        try:
            self._seed_data(app)
            with app.test_client() as c:
                _user_session(c)
                r = c.post('/api/brandiction/predict',
                           json={"theme": "science", "budget": 50000})
                assert r.status_code == 200
                data = r.get_json()
                assert "current_state" in data
                assert "predicted_state" in data
                assert "delta" in data
                assert "confidence" in data
                assert "reasoning" in data
                assert "similar_interventions" in data
        finally:
            _cleanup(db)

    def test_probability_board(self):
        app, db = _make_app()
        try:
            self._seed_data(app)
            with app.test_client() as c:
                _user_session(c)
                r = c.post('/api/brandiction/probability-board',
                           json={"plans": [
                               {"theme": "science", "budget": 50000},
                               {"theme": "beauty", "budget": 30000},
                           ]})
                assert r.status_code == 200
                data = r.get_json()
                assert "current_state" in data
                assert "paths" in data
                assert len(data["paths"]) == 2
                assert "recommendation" in data
                for path in data["paths"]:
                    assert "predicted_delta" in path
                    assert "dimension_impacts" in path
                    assert "confidence" in path
        finally:
            _cleanup(db)

    def test_backtest(self):
        app, db = _make_app()
        try:
            self._seed_data(app)
            with app.test_client() as c:
                _admin_session(c)
                r = c.post('/api/brandiction/backtest', json={})
                assert r.status_code == 200
                data = r.get_json()
                assert "total_interventions" in data
                assert "tested" in data
                assert "mean_absolute_error" in data
                assert "per_dimension_mae" in data
                assert "details" in data
        finally:
            _cleanup(db)

    def test_simulate(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.post('/api/brandiction/simulate',
                           json={"steps": [
                               {"theme": "science", "budget": 50000},
                               {"theme": "comfort", "budget": 30000},
                           ]})
                assert r.status_code == 200
                data = r.get_json()
                assert "scenario_id" in data
                assert "initial_state" in data
                assert "timeline" in data
                assert len(data["timeline"]) == 2
                assert "final_state" in data
                assert "cumulative_delta" in data
                assert "steps_count" in data
                assert data["steps_count"] == 2
        finally:
            _cleanup(db)

    def test_compare_scenarios(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.post('/api/brandiction/compare-scenarios',
                           json={"scenarios": [
                               {"name": "A", "steps": [{"theme": "science"}]},
                               {"name": "B", "steps": [{"theme": "beauty"}]},
                           ]})
                assert r.status_code == 200
                data = r.get_json()
                assert "current_state" in data
                assert "scenarios" in data
                assert len(data["scenarios"]) == 2
                assert "recommendation" in data
                for sc in data["scenarios"]:
                    assert "name" in sc
                    assert "score" in sc
                    assert "rank" in sc
        finally:
            _cleanup(db)


# ------------------------------------------------------------------
# Query parameter handling
# ------------------------------------------------------------------

class TestQueryParams:
    def test_signals_date_range(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _admin_session(c)
                c.post('/api/brandiction/import-history', json={
                    "signals": [
                        {"signal_id": "s1", "date": "2025-01-01",
                         "dimension": "science_credibility", "value": 0.3},
                        {"signal_id": "s2", "date": "2025-06-01",
                         "dimension": "science_credibility", "value": 0.7},
                    ]
                })

                _user_session(c)
                r = c.get('/api/brandiction/signals?date_from=2025-05-01')
                data = r.get_json()
                assert data["count"] == 1
                assert data["signals"][0]["signal_id"] == "s2"
        finally:
            _cleanup(db)

    def test_brand_state_with_segment(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.get('/api/brandiction/brand-state?audience_segment=young_female')
                assert r.status_code == 200
                data = r.get_json()
                assert data["count"] == 0  # no data for this segment
        finally:
            _cleanup(db)

    def test_competitor_events_date_range(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _admin_session(c)
                c.post('/api/brandiction/import-history', json={
                    "competitor_events": [
                        {"event_id": "e1", "date": "2025-01-15",
                         "competitor": "acuvue", "impact_estimate": "high"},
                        {"event_id": "e2", "date": "2025-06-15",
                         "competitor": "bausch", "impact_estimate": "low"},
                    ]
                })

                r = c.get('/api/brandiction/competitor-events?date_from=2025-06-01')
                data = r.get_json()
                assert data["count"] == 1
                assert data["events"][0]["competitor"] == "bausch"
        finally:
            _cleanup(db)

    def test_predict_with_audience_segment(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.post('/api/brandiction/predict',
                           json={"theme": "science", "audience_segment": "young_female"})
                assert r.status_code == 200
        finally:
            _cleanup(db)

    def test_simulate_with_product_line(self):
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.post('/api/brandiction/simulate',
                           json={
                               "steps": [{"theme": "science"}],
                               "product_line": "colored_lenses",
                           })
                assert r.status_code == 200
        finally:
            _cleanup(db)


# ------------------------------------------------------------------
# Partial success / error: compare-scenarios with mixed input
# ------------------------------------------------------------------

class TestPartialSuccess:
    def test_compare_scenarios_mixed_valid_invalid(self):
        """一条合法 + 一条非法（空 steps）→ 200，合法有结果，非法带 error"""
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.post('/api/brandiction/compare-scenarios',
                           json={"scenarios": [
                               {"name": "valid", "steps": [{"theme": "science"}]},
                               {"name": "invalid", "steps": []},
                           ]})
                assert r.status_code == 200
                data = r.get_json()
                assert len(data["scenarios"]) == 2

                valid = [s for s in data["scenarios"] if s["name"] == "valid"][0]
                invalid = [s for s in data["scenarios"] if s["name"] == "invalid"][0]

                # 合法的有完整结果
                assert "score" in valid
                assert "rank" in valid
                assert "final_state" in valid
                assert "error" not in valid

                # 非法的有 error，无 score
                assert "error" in invalid
                assert "score" not in invalid
        finally:
            _cleanup(db)

    def test_compare_scenarios_all_valid_still_works(self):
        """全部合法时不受混合逻辑影响"""
        app, db = _make_app()
        try:
            with app.test_client() as c:
                _user_session(c)
                r = c.post('/api/brandiction/compare-scenarios',
                           json={"scenarios": [
                               {"name": "A", "steps": [{"theme": "science"}]},
                               {"name": "B", "steps": [{"theme": "beauty"}]},
                           ]})
                assert r.status_code == 200
                data = r.get_json()
                for sc in data["scenarios"]:
                    assert "error" not in sc
                    assert "rank" in sc
        finally:
            _cleanup(db)
