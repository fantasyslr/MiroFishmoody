"""
Phase 5.6 — readiness 门槛 + judge calibration 状态一致性测试
"""

import sys
import os
import json
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.scoreboard import ResolutionRecord
from app.services.judge_calibration import JudgeCalibration
from app.api.campaign import _parse_campaigns


def _seed_set(cal, set_id, n_campaigns, winner_id, judge_preds):
    """创建一个评审集的 predictions + resolutions"""
    persona_preds = []
    for cid_idx in range(n_campaigns):
        cid = chr(ord('a') + cid_idx)
        score = 8 if cid == winner_id else 5
        total = 8 + 5 * (n_campaigns - 1)
        persona_preds.append({
            "persona_id": "p1", "campaign_id": cid,
            "score": score, "preference": round(score / total, 4),
        })

    win_probs = {}
    for cid_idx in range(n_campaigns):
        cid = chr(ord('a') + cid_idx)
        win_probs[cid] = 0.6 if cid == winner_id else round(0.4 / (n_campaigns - 1), 3)

    cal.save_predictions(set_id, persona_preds, judge_preds, win_probs)

    for cid_idx in range(n_campaigns):
        cid = chr(ord('a') + cid_idx)
        cal.record_resolution(ResolutionRecord(
            set_id=set_id, campaign_id=cid,
            resolved_at="2026-03-13", actual_metrics={},
            predicted_win_prob=win_probs[cid],
            was_actual_winner=(cid == winner_id),
        ))


# ============================================================
# Test 1: mixed old/new data — recalibrate must return insufficient_data
# ============================================================
def test_mixed_data_recalibrate_insufficient():
    """
    7 resolved sets, only 3 with predictions.
    recalibrate() must return insufficient_data, not calibrated.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        cal = JudgeCalibration(calibration_dir=tmpdir)

        # 4 old sets — resolutions only, no predictions
        for i in range(4):
            cal.record_resolution(ResolutionRecord(
                set_id=f"old-{i}", campaign_id="a",
                resolved_at="2026-01-01", actual_metrics={},
                predicted_win_prob=0.6, was_actual_winner=True,
            ))

        # 3 new sets — with predictions
        for i in range(3):
            _seed_set(cal, f"new-{i}", 2, "a", [
                {"judge_id": "j1", "campaign_a_id": "a", "campaign_b_id": "b",
                 "winner_pick": "A", "dimensions": {}},
            ])

        result = cal.recalibrate()
        assert result["status"] == "insufficient_data", (
            f"Expected insufficient_data, got {result['status']}"
        )
        assert result["sets_with_predictions"] == 3
        assert result["resolved_sets"] == 7
        assert "3" in result["message"]
        assert "calibrated_at" in result and result["calibrated_at"] is None
        print(f"  PASS: mixed 7 resolved / 3 predictions → insufficient_data")
        print(f"    message: {result['message']}")


# ============================================================
# Test 2: 2-campaign → judge_calibration = complete everywhere
# ============================================================
def test_2_campaign_judge_complete():
    """
    All 2-campaign evals → judge_calibration = complete in recalibrate() AND meta.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        cal = JudgeCalibration(calibration_dir=tmpdir)

        for i in range(6):
            _seed_set(cal, f"duo-{i}", 2, "a", [
                {"judge_id": "j1", "campaign_a_id": "a", "campaign_b_id": "b",
                 "winner_pick": "A", "dimensions": {}},
            ])

        result = cal.recalibrate()
        assert result["status"] == "calibrated"
        assert result["judge_calibration"] == "complete"
        assert result["persona_calibration"] == "complete"
        assert result["judge_matchups_skipped"] == 0

        # Meta should also say complete
        meta = cal.get_calibration_meta()
        assert meta["judge_calibration"] == "complete"
        assert meta["persona_calibration"] == "complete"

        # Simulate what GET /calibration would return
        stats = cal.get_all_stats()
        judge_stats = [s for s in stats if s.judge_type == "judge"]
        assert len(judge_stats) > 0

        print(f"  PASS: 2-campaign → judge_calibration=complete in recalibrate + meta")


# ============================================================
# Test 3: 3-campaign → judge_calibration = partial everywhere
# ============================================================
def test_3_campaign_judge_partial():
    """
    All 3-campaign evals → judge_calibration = partial in recalibrate() AND meta.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        cal = JudgeCalibration(calibration_dir=tmpdir)

        for i in range(6):
            _seed_set(cal, f"tri-{i}", 3, "a", [
                {"judge_id": "j1", "campaign_a_id": "a", "campaign_b_id": "b",
                 "winner_pick": "A", "dimensions": {}},
                {"judge_id": "j1", "campaign_a_id": "a", "campaign_b_id": "c",
                 "winner_pick": "A", "dimensions": {}},
                # B vs C — winner not involved → will be skipped
                {"judge_id": "j1", "campaign_a_id": "b", "campaign_b_id": "c",
                 "winner_pick": "B", "dimensions": {}},
            ])

        result = cal.recalibrate()
        assert result["status"] == "calibrated"
        assert "partial" in result["judge_calibration"]
        assert result["judge_matchups_skipped"] == 6

        meta = cal.get_calibration_meta()
        assert "partial" in meta["judge_calibration"]
        assert meta["persona_calibration"] == "complete"

        print(f"  PASS: 3-campaign → judge_calibration=partial in recalibrate + meta")
        print(f"    meta.judge_calibration: {meta['judge_calibration']}")


# ============================================================
# Test 4: calibration_ready always based on sets_with_predictions
# ============================================================
def test_calibration_ready_based_on_predictions():
    """calibration_ready 始终基于 sets_with_predictions，不被老评审集误导"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cal = JudgeCalibration(calibration_dir=tmpdir)

        # 10 old resolutions (no predictions)
        for i in range(10):
            cal.record_resolution(ResolutionRecord(
                set_id=f"old-{i}", campaign_id="a",
                resolved_at="2026-01-01", actual_metrics={},
                predicted_win_prob=0.6, was_actual_winner=True,
            ))

        resolutions = cal.load_resolutions()
        resolved_set_ids = set(r["set_id"] for r in resolutions)
        sets_with_preds = sum(
            1 for sid in resolved_set_ids
            if cal.load_predictions(sid) is not None
        )

        assert len(resolved_set_ids) == 10
        assert sets_with_preds == 0

        # calibration_ready should be False (0 predictions, not 10 resolved)
        api_ready = sets_with_preds >= 5
        assert api_ready is False

        # recalibrate should return insufficient
        result = cal.recalibrate()
        assert result["status"] == "insufficient_data"
        assert result["sets_with_predictions"] == 0

        # Now add 5 with predictions
        for i in range(5):
            _seed_set(cal, f"new-{i}", 2, "a", [
                {"judge_id": "j1", "campaign_a_id": "a", "campaign_b_id": "b",
                 "winner_pick": "A", "dimensions": {}},
            ])

        result2 = cal.recalibrate()
        assert result2["status"] == "calibrated"

        sets_with_preds2 = sum(
            1 for sid in set(r["set_id"] for r in cal.load_resolutions())
            if cal.load_predictions(sid) is not None
        )
        assert sets_with_preds2 >= 5
        api_ready2 = sets_with_preds2 >= 5
        assert api_ready2 is True

        print(f"  PASS: calibration_ready based on sets_with_predictions (0→False, {sets_with_preds2}→True)")


def test_parse_campaigns_rejects_duplicate_campaign_ids():
    """重复 campaign.id 应在 API 入口被拒绝，避免结果按同 key 覆盖"""
    payload = {
        "campaigns": [
            {
                "id": "dup",
                "name": "A",
                "product_line": "colored_lenses",
                "core_message": "msg-a",
            },
            {
                "id": "dup",
                "name": "B",
                "product_line": "colored_lenses",
                "core_message": "msg-b",
            },
        ]
    }

    try:
        _parse_campaigns(payload)
        assert False, "Expected duplicate campaign id to raise ValueError"
    except ValueError as e:
        assert "重复" in str(e)
        assert "dup" in str(e)
        print("  PASS: duplicate campaign ids rejected at parse time")


def test_resolve_rejects_duplicate_set_id():
    """同一个 set_id 不允许重复结算"""
    import tempfile
    from unittest.mock import patch
    from app import create_app
    from app.services.judge_calibration import JudgeCalibration as RealJC
    from app.api import campaign as campaign_api

    app = create_app()
    with app.app_context():
        with tempfile.TemporaryDirectory() as tmpdir:
            cal = RealJC(calibration_dir=tmpdir)
            old_results_dir = campaign_api._RESULTS_DIR
            old_store = dict(campaign_api._evaluation_store)

            campaign_api._RESULTS_DIR = os.path.join(tmpdir, 'results')
            os.makedirs(campaign_api._RESULTS_DIR, exist_ok=True)

            result_data = {
                "set_id": "resolve-dup-test",
                "rankings": [],
                "scoreboard": {
                    "campaigns": [
                        {"campaign_id": "a", "overall_score": 0.6},
                        {"campaign_id": "b", "overall_score": 0.4},
                    ]
                },
            }
            campaign_api._save_result("resolve-dup-test", result_data)
            campaign_api._evaluation_store["resolve-dup-test"] = result_data

            # Patch JudgeCalibration 在 campaign API 模块中，使其始终使用临时目录
            with patch('app.api.campaign.JudgeCalibration', lambda **kw: cal):
                # 同时 patch ResolutionTracker 使其也用同一个 calibration
                with patch('app.api.campaign.ResolutionTracker') as MockRT:
                    from app.services.resolution_tracker import ResolutionTracker as RealRT
                    real_tracker = RealRT()
                    real_tracker.calibration = cal
                    MockRT.return_value = real_tracker

                    client = app.test_client()
                    with client.session_transaction() as sess:
                        sess['user'] = {"username": "tester", "display_name": "Tester"}

                    resp1 = client.post('/api/campaign/resolve', json={
                        "set_id": "resolve-dup-test",
                        "winner_campaign_id": "a",
                        "actual_metrics": {"ctr": 0.03},
                    })
                    assert resp1.status_code == 200, f"First resolve failed: {resp1.get_json()}"

                    resp2 = client.post('/api/campaign/resolve', json={
                        "set_id": "resolve-dup-test",
                        "winner_campaign_id": "b",
                        "actual_metrics": {"ctr": 0.01},
                    })
                    assert resp2.status_code == 409, (
                        f"Expected 409 for duplicate resolve, got {resp2.status_code}: {resp2.get_json()}"
                    )
                    body2 = resp2.get_json()
                    assert "已结算" in body2["error"]
                    print("  PASS: duplicate resolve rejected with 409")

            campaign_api._RESULTS_DIR = old_results_dir
            campaign_api._evaluation_store.clear()
            campaign_api._evaluation_store.update(old_store)


def test_evaluate_rejects_duplicate_set_id():
    """用户传入已存在的 set_id 应返回 409，不覆盖已有结果"""
    import tempfile
    from app import create_app
    from app.api import campaign as campaign_api

    app = create_app()
    with app.app_context():
        with tempfile.TemporaryDirectory() as tmpdir:
            old_results_dir = campaign_api._RESULTS_DIR
            old_store = dict(campaign_api._evaluation_store)
            campaign_api._RESULTS_DIR = tmpdir

            # 预存一个已有结果
            existing = {"set_id": "existing-set", "rankings": [{"rank": 1}]}
            campaign_api._save_result("existing-set", existing)

            try:
                client = app.test_client()
                with client.session_transaction() as sess:
                    sess['user'] = {"username": "tester", "display_name": "Tester"}
                resp = client.post('/api/campaign/evaluate', json={
                    "set_id": "existing-set",
                    "campaigns": [
                        {"name": "A", "core_message": "msg-a", "product_line": "colored_lenses"},
                        {"name": "B", "core_message": "msg-b", "product_line": "colored_lenses"},
                    ],
                })
                assert resp.status_code == 409, (
                    f"Expected 409, got {resp.status_code}: {resp.get_json()}"
                )
                assert "已存在" in resp.get_json()["error"]

                # 验证磁盘结果未被覆盖
                loaded = campaign_api._load_result("existing-set")
                assert loaded == existing, "Existing result should not be overwritten"
                print("  PASS: evaluate rejects duplicate set_id with 409")
            finally:
                campaign_api._RESULTS_DIR = old_results_dir
                campaign_api._evaluation_store.clear()
                campaign_api._evaluation_store.update(old_store)


def test_evaluate_rejects_duplicate_set_id_in_memory():
    """set_id 在内存中存在时也应被拒绝"""
    from app import create_app
    from app.api import campaign as campaign_api

    app = create_app()
    with app.app_context():
        old_store = dict(campaign_api._evaluation_store)
        campaign_api._evaluation_store["mem-set"] = {"set_id": "mem-set"}

        try:
            client = app.test_client()
            with client.session_transaction() as sess:
                sess['user'] = {"username": "tester", "display_name": "Tester"}
            resp = client.post('/api/campaign/evaluate', json={
                "set_id": "mem-set",
                "campaigns": [
                    {"name": "A", "core_message": "msg-a", "product_line": "colored_lenses"},
                    {"name": "B", "core_message": "msg-b", "product_line": "colored_lenses"},
                ],
            })
            assert resp.status_code == 409
            print("  PASS: evaluate rejects set_id found in memory store")
        finally:
            campaign_api._evaluation_store.clear()
            campaign_api._evaluation_store.update(old_store)


def test_run_evaluation_fails_on_empty_panel():
    """panel_scores 为空时 _run_evaluation 应 fail task"""
    from unittest.mock import patch, MagicMock
    from app.api import campaign as campaign_api
    from app.models.campaign import Campaign, CampaignSet, ProductLine

    campaigns = [
        Campaign(id="a", name="A", product_line=ProductLine.COLORED,
                 target_audience="t", core_message="m", channels=[], creative_direction=""),
        Campaign(id="b", name="B", product_line=ProductLine.COLORED,
                 target_audience="t", core_message="m", channels=[], creative_direction=""),
    ]
    cs = CampaignSet(set_id="fail-panel", campaigns=campaigns, context="", created_at="now")
    task_id = campaign_api.task_manager.create_task("campaign_evaluation")

    # Mock LLMClient so it doesn't need a real key
    mock_llm = MagicMock()
    # Mock AudiencePanel.evaluate_all to return empty (simulating all LLM calls failing)
    with patch('app.api.campaign.LLMClient', return_value=mock_llm):
        with patch('app.api.campaign.AudiencePanel') as MockPanel:
            MockPanel.return_value.evaluate_all.return_value = []
            campaign_api._run_evaluation(task_id, cs)

    task = campaign_api.task_manager.get_task(task_id)
    assert task.status.value == "failed", f"Expected failed, got {task.status.value}"
    assert "Panel" in task.error
    assert "全部失败" in task.error
    print(f"  PASS: empty panel_scores → task failed: {task.error}")


def test_run_evaluation_fails_on_empty_pairwise():
    """pairwise_results 为空时 _run_evaluation 应 fail task"""
    from unittest.mock import patch, MagicMock
    from app.api import campaign as campaign_api
    from app.models.campaign import Campaign, CampaignSet, ProductLine
    from app.models.evaluation import PanelScore

    campaigns = [
        Campaign(id="a", name="A", product_line=ProductLine.COLORED,
                 target_audience="t", core_message="m", channels=[], creative_direction=""),
        Campaign(id="b", name="B", product_line=ProductLine.COLORED,
                 target_audience="t", core_message="m", channels=[], creative_direction=""),
    ]
    cs = CampaignSet(set_id="fail-pairwise", campaigns=campaigns, context="", created_at="now")
    task_id = campaign_api.task_manager.create_task("campaign_evaluation")

    # Panel returns valid scores, but pairwise returns empty
    fake_panel = [
        PanelScore("p1", "P1", "a", 7.0, ["obj"], ["str"], "ok"),
        PanelScore("p1", "P1", "b", 5.0, ["obj"], ["str"], "ok"),
    ]
    mock_llm = MagicMock()
    with patch('app.api.campaign.LLMClient', return_value=mock_llm):
        with patch('app.api.campaign.AudiencePanel') as MockPanel:
            MockPanel.return_value.evaluate_all.return_value = fake_panel
            with patch('app.api.campaign.PairwiseJudge') as MockJudge:
                MockJudge.return_value.evaluate_all.return_value = ([], {})
                campaign_api._run_evaluation(task_id, cs)

    task = campaign_api.task_manager.get_task(task_id)
    assert task.status.value == "failed", f"Expected failed, got {task.status.value}"
    assert "Pairwise" in task.error
    assert "全部失败" in task.error
    print(f"  PASS: empty pairwise_results → task failed: {task.error}")


if __name__ == "__main__":
    print("=== Phase 5.6 Tests ===")
    test_mixed_data_recalibrate_insufficient()
    test_2_campaign_judge_complete()
    test_3_campaign_judge_partial()
    test_calibration_ready_based_on_predictions()
    test_parse_campaigns_rejects_duplicate_campaign_ids()
    test_resolve_rejects_duplicate_set_id()
    test_evaluate_rejects_duplicate_set_id()
    test_evaluate_rejects_duplicate_set_id_in_memory()
    test_run_evaluation_fails_on_empty_panel()
    test_run_evaluation_fails_on_empty_pairwise()
    print("\nALL PHASE 5.6 TESTS PASSED")
