"""
Calibration Loop 单元测试 — Phase 5.1-5.4 闭环验证
"""

import sys
import os
import json
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.campaign import Campaign, ProductLine
from app.models.evaluation import PanelScore, PairwiseResult, Verdict
from app.services.judge_calibration import JudgeCalibration
from app.services.resolution_tracker import ResolutionTracker
from app.services.campaign_scorer import CampaignScorer


def make_campaign(id, name):
    return Campaign(
        id=id, name=name, product_line=ProductLine.COLORED,
        target_audience="test", core_message="test",
        channels=["meta"], creative_direction="test",
    )


def make_panel(persona_id, campaign_id, score, n_obj=1):
    return PanelScore(
        persona_id=persona_id, persona_name=f"P_{persona_id}",
        campaign_id=campaign_id, score=score,
        objections=[f"obj_{i}" for i in range(n_obj)],
        strengths=["str_1"], reasoning="ok",
    )


# ============================================================
# Test 1: per-persona / per-judge prediction 落盘
# ============================================================
def test_save_and_load_predictions():
    """记录 per-persona / per-judge prediction 成功落盘"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cal = JudgeCalibration(calibration_dir=tmpdir)

        persona_preds = [
            {"persona_id": "p1", "campaign_id": "a", "score": 8.0, "preference": 0.6},
            {"persona_id": "p1", "campaign_id": "b", "score": 5.0, "preference": 0.4},
            {"persona_id": "p2", "campaign_id": "a", "score": 7.0, "preference": 0.54},
            {"persona_id": "p2", "campaign_id": "b", "score": 6.0, "preference": 0.46},
        ]
        judge_preds = [
            {"judge_id": "strategist", "campaign_a_id": "a", "campaign_b_id": "b",
             "winner_pick": "A", "dimensions": {"reach_potential": "A"}},
            {"judge_id": "consumer", "campaign_a_id": "a", "campaign_b_id": "b",
             "winner_pick": "B", "dimensions": {"reach_potential": "B"}},
            {"judge_id": "brand_guardian", "campaign_a_id": "a", "campaign_b_id": "b",
             "winner_pick": "A", "dimensions": {"reach_potential": "A"}},
        ]
        win_probs = {"a": 0.65, "b": 0.35}

        cal.save_predictions("set-001", persona_preds, judge_preds, win_probs)

        loaded = cal.load_predictions("set-001")
        assert loaded is not None
        assert loaded["set_id"] == "set-001"
        assert len(loaded["persona_predictions"]) == 4
        assert len(loaded["judge_predictions"]) == 3
        assert loaded["campaign_win_probabilities"]["a"] == 0.65

        # 不存在的 set_id
        assert cal.load_predictions("nonexistent") is None

        # 验证文件确实在磁盘上
        pred_file = os.path.join(tmpdir, 'predictions', 'set-001.json')
        assert os.path.exists(pred_file)
        print("  PASS: predictions saved and loaded from disk")


# ============================================================
# Test 2: resolution 之后可读取历史样本
# ============================================================
def test_resolution_reads_history():
    """resolution 之后可正确读取历史样本"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cal = JudgeCalibration(calibration_dir=tmpdir)
        tracker = ResolutionTracker()
        tracker.calibration = cal

        # 先保存预测数据
        cal.save_predictions("set-001", [
            {"persona_id": "p1", "campaign_id": "a", "score": 8, "preference": 0.6},
            {"persona_id": "p1", "campaign_id": "b", "score": 5, "preference": 0.4},
        ], [
            {"judge_id": "j1", "campaign_a_id": "a", "campaign_b_id": "b",
             "winner_pick": "A", "dimensions": {}},
        ], {"a": 0.65, "b": 0.35})

        # 结算
        tracker.resolve(
            set_id="set-001", winner_campaign_id="a",
            actual_metrics={"ctr": 0.03},
            predicted_probabilities={"a": 0.65, "b": 0.35},
        )

        resolutions = cal.load_resolutions()
        assert len(resolutions) == 2  # winner + 1 loser
        preds = cal.load_predictions("set-001")
        assert preds is not None
        print("  PASS: resolution + predictions both readable")


# ============================================================
# Test 3: recalibrate 样本不足时返回明确状态
# ============================================================
def test_recalibrate_insufficient():
    """recalibrate 在样本不足时返回明确状态"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cal = JudgeCalibration(calibration_dir=tmpdir)

        # 只创建 2 个结算（需要 5 个）
        for i in range(2):
            from app.models.scoreboard import ResolutionRecord
            cal.record_resolution(ResolutionRecord(
                set_id=f"set-{i:03d}", campaign_id="a",
                resolved_at="2026-01-01", actual_metrics={},
                predicted_win_prob=0.6, was_actual_winner=True,
            ))

        result = cal.recalibrate()
        assert result["status"] == "insufficient_data"
        assert result["stats_count"] == 0
        assert result["resolved_sets"] == 2
        assert "calibrated_at" in result
        assert result["calibrated_at"] is None
        print("  PASS: recalibrate insufficient → clear status")


# ============================================================
# Test 4: recalibrate 生成 judge_stats.json
# ============================================================
def test_recalibrate_generates_stats():
    """recalibrate 在伪造足够样本时会生成 judge_stats.json"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cal = JudgeCalibration(calibration_dir=tmpdir)

        # 创建 6 个评审集，每个有预测 + 结算
        for i in range(6):
            set_id = f"set-{i:03d}"

            # 方案 A 总是 winner，persona p1 正确预测高分
            # persona p2 总是给 A 低分（错误预测）
            cal.save_predictions(set_id, [
                {"persona_id": "p1", "campaign_id": "a", "score": 8, "preference": 0.62},
                {"persona_id": "p1", "campaign_id": "b", "score": 5, "preference": 0.38},
                {"persona_id": "p2", "campaign_id": "a", "score": 4, "preference": 0.36},
                {"persona_id": "p2", "campaign_id": "b", "score": 7, "preference": 0.64},
            ], [
                # strategist 总是选 A（正确）
                {"judge_id": "strategist", "campaign_a_id": "a", "campaign_b_id": "b",
                 "winner_pick": "A", "dimensions": {}},
                # consumer 总是选 B（错误）
                {"judge_id": "consumer", "campaign_a_id": "a", "campaign_b_id": "b",
                 "winner_pick": "B", "dimensions": {}},
            ], {"a": 0.65, "b": 0.35})

            # A 是赢家
            from app.models.scoreboard import ResolutionRecord
            cal.record_resolution(ResolutionRecord(
                set_id=set_id, campaign_id="a",
                resolved_at="2026-01-01", actual_metrics={"ctr": 0.03},
                predicted_win_prob=0.65, was_actual_winner=True,
            ))
            cal.record_resolution(ResolutionRecord(
                set_id=set_id, campaign_id="b",
                resolved_at="2026-01-01", actual_metrics={},
                predicted_win_prob=0.35, was_actual_winner=False,
            ))

        result = cal.recalibrate()
        assert result["status"] == "calibrated", f"Expected calibrated, got {result}"
        assert result["stats_count"] > 0
        assert result["calibrated_at"] is not None

        # 验证 judge_stats.json 文件存在
        stats_file = os.path.join(tmpdir, 'judge_stats.json')
        assert os.path.exists(stats_file), "judge_stats.json not created"

        with open(stats_file) as f:
            stats_data = json.load(f)
        assert len(stats_data) > 0

        # 验证 p1 (accurate) 比 p2 (inaccurate) 有更好的 Brier score
        p1_stat = next(s for s in stats_data if s["judge_id"] == "p1")
        p2_stat = next(s for s in stats_data if s["judge_id"] == "p2")
        assert p1_stat["brier_score"] < p2_stat["brier_score"], (
            f"p1 (accurate) should have lower Brier: "
            f"p1={p1_stat['brier_score']}, p2={p2_stat['brier_score']}"
        )

        # 验证 strategist (always correct) vs consumer (always wrong)
        strat = next(s for s in stats_data if s["judge_id"] == "strategist")
        cons = next(s for s in stats_data if s["judge_id"] == "consumer")
        assert strat["brier_score"] < cons["brier_score"], (
            f"strategist should have lower Brier: "
            f"strat={strat['brier_score']}, cons={cons['brier_score']}"
        )

        print(f"  PASS: recalibrate generated {len(stats_data)} stats")
        print(f"    p1 brier={p1_stat['brier_score']:.4f}, p2 brier={p2_stat['brier_score']:.4f}")
        print(f"    strategist brier={strat['brier_score']:.4f}, consumer brier={cons['brier_score']:.4f}")


# ============================================================
# Test 5: get_weights() 在有 stats 时返回非空权重
# ============================================================
def test_get_weights_after_calibration():
    """get_weights() 在有 stats 时返回非空权重"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cal = JudgeCalibration(calibration_dir=tmpdir)

        # 先执行 test 4 的 setup
        for i in range(6):
            set_id = f"set-{i:03d}"
            cal.save_predictions(set_id, [
                {"persona_id": "p1", "campaign_id": "a", "score": 8, "preference": 0.62},
                {"persona_id": "p1", "campaign_id": "b", "score": 5, "preference": 0.38},
            ], [
                {"judge_id": "strategist", "campaign_a_id": "a", "campaign_b_id": "b",
                 "winner_pick": "A", "dimensions": {}},
            ], {"a": 0.65, "b": 0.35})

            from app.models.scoreboard import ResolutionRecord
            cal.record_resolution(ResolutionRecord(
                set_id=set_id, campaign_id="a",
                resolved_at="2026-01-01", actual_metrics={},
                predicted_win_prob=0.65, was_actual_winner=True,
            ))
            cal.record_resolution(ResolutionRecord(
                set_id=set_id, campaign_id="b",
                resolved_at="2026-01-01", actual_metrics={},
                predicted_win_prob=0.35, was_actual_winner=False,
            ))

        cal.recalibrate()

        judge_w, persona_w = cal.get_weights()
        assert len(persona_w) > 0, "persona_weights should be non-empty after calibration"
        assert len(judge_w) > 0, "judge_weights should be non-empty after calibration"
        assert all(w > 0 for w in persona_w.values())
        assert all(w > 0 for w in judge_w.values())
        print(f"  PASS: get_weights returns persona={persona_w}, judge={judge_w}")


# ============================================================
# Test 6: 新权重会实际影响 scorer/probability 输出
# ============================================================
def test_weights_affect_scoring():
    """新权重会实际影响一次 scorer/probability 输出"""
    campaigns = [
        make_campaign("a", "A"),
        make_campaign("b", "B"),
    ]

    # panel: p1 和 p2 有相反偏好
    panel = [
        make_panel("p1", "a", 8, 1),  # p1 偏好 A
        make_panel("p1", "b", 4, 3),
        make_panel("p2", "a", 4, 3),  # p2 偏好 B
        make_panel("p2", "b", 8, 1),
    ]

    # pairwise: j1 选 A, j2 选 B, j3 选 A → A wins
    pairwise = [PairwiseResult("a", "b", "a", [
        {"judge_id": "j1", "winner": "A", "dimensions": {}, "reasoning": ""},
        {"judge_id": "j2", "winner": "B", "dimensions": {}, "reasoning": ""},
        {"judge_id": "j3", "winner": "A", "dimensions": {}, "reasoning": ""},
    ], {})]
    bt = {"a": 1.5, "b": 0.5}

    # Baseline: 无权重
    scorer_base = CampaignScorer()
    _, board_base = scorer_base.score(campaigns, panel, pairwise, bt)
    prob_a_base = next(c.overall_score for c in board_base.campaigns if c.campaign_id == "a")

    # With weights: 大幅提高 p2 权重（偏好 B），大幅提高 j2 权重（选 B）
    scorer_w = CampaignScorer(
        judge_weights={"j1": 0.3, "j2": 2.0, "j3": 0.3},
        persona_weights={"p1": 0.3, "p2": 2.0},
    )
    _, board_w = scorer_w.score(campaigns, panel, pairwise, bt)
    prob_a_weighted = next(c.overall_score for c in board_w.campaigns if c.campaign_id == "a")

    # A's probability should decrease when B-favoring judges/personas are weighted up
    assert prob_a_weighted < prob_a_base, (
        f"Weighting B-favoring judges should reduce A's prob: "
        f"base={prob_a_base:.3f}, weighted={prob_a_weighted:.3f}"
    )
    diff = prob_a_base - prob_a_weighted
    assert diff > 0.01, f"Difference too small to be meaningful: {diff:.4f}"

    print(f"  PASS: weights affect scoring (A prob: {prob_a_base:.3f} → {prob_a_weighted:.3f}, delta={diff:.3f})")


# ============================================================
# Test 7: calibration_no_history 不报错
# ============================================================
def test_calibration_no_history():
    """calibration 在无历史数据时不报错"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cal = JudgeCalibration(calibration_dir=tmpdir)

        judge_w, persona_w = cal.get_weights()
        assert judge_w == {}
        assert persona_w == {}
        assert cal.get_all_stats() == []
        assert cal.load_resolutions() == []

        result = cal.recalibrate()
        assert result["status"] == "insufficient_data"
        assert result["resolved_sets"] == 0

        meta = cal.get_calibration_meta()
        assert meta == {} or meta.get("last_calibrated_at") is None
        print("  PASS: calibration with no history → safe defaults")


if __name__ == "__main__":
    print("=== Calibration Loop Tests (Phase 5.1-5.4) ===")
    test_save_and_load_predictions()
    test_resolution_reads_history()
    test_recalibrate_insufficient()
    test_recalibrate_generates_stats()
    test_get_weights_after_calibration()
    test_weights_affect_scoring()
    test_calibration_no_history()
    print("\nALL CALIBRATION TESTS PASSED")
