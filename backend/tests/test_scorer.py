"""
Campaign Scorer 单元测试 — Phase 5: market-aware verdict + probability board
"""

import sys
import os
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.campaign import Campaign, ProductLine
from app.models.evaluation import PanelScore, PairwiseResult, Verdict
from app.models.scoreboard import DIMENSION_KEYS
from app.services.campaign_scorer import CampaignScorer
from app.services.judge_calibration import JudgeCalibration
from app.services.resolution_tracker import ResolutionTracker


def make_campaign(id: str, name: str, pl=ProductLine.COLORED) -> Campaign:
    return Campaign(
        id=id, name=name, product_line=pl,
        target_audience="test", core_message="test",
        channels=["meta"], creative_direction="test",
    )


def make_panel(persona_id, campaign_id, score, n_objections=1, obj_texts=None):
    objs = obj_texts if obj_texts else [f"obj_{i}" for i in range(n_objections)]
    return PanelScore(
        persona_id=persona_id, persona_name=f"P_{persona_id}",
        campaign_id=campaign_id, score=score,
        objections=objs,
        strengths=["str_1"], reasoning="ok",
    )


# ============================================================
# Phase 4.5 verdict tests (updated for tuple return)
# ============================================================

def test_ship_rank1_dominant():
    """#1 + 明显胜出 + 低 objection → SHIP"""
    campaigns = [
        make_campaign("a", "A"),
        make_campaign("b", "B"),
        make_campaign("c", "C"),
    ]
    panel = [
        make_panel("p1", "a", 8, n_objections=1),
        make_panel("p2", "a", 8, n_objections=1),
        make_panel("p1", "b", 6, n_objections=2),
        make_panel("p2", "b", 6, n_objections=2),
        make_panel("p1", "c", 5, n_objections=2),
        make_panel("p2", "c", 5, n_objections=2),
    ]
    pairwise = [
        PairwiseResult("a", "b", "a", [], {}),
        PairwiseResult("a", "c", "a", [], {}),
        PairwiseResult("b", "c", "b", [], {}),
    ]
    bt = {"a": 2.0, "b": 1.0, "c": 0.33}

    rankings, board = CampaignScorer().score(campaigns, panel, pairwise, bt)

    assert rankings[0].campaign_id == "a"
    assert rankings[0].verdict == Verdict.SHIP, f"Expected SHIP, got {rankings[0].verdict}"
    assert rankings[0].rank == 1
    assert board is not None
    print("  PASS: #1 dominant → SHIP + board returned")


def test_revise_rank1_high_objections():
    """#1 但 objection 密度 > 4.0 → REVISE"""
    campaigns = [
        make_campaign("a", "A"),
        make_campaign("b", "B"),
    ]
    panel = [
        make_panel("p1", "a", 7, n_objections=6),
        make_panel("p2", "a", 7, n_objections=5),
        make_panel("p1", "b", 5, n_objections=1),
        make_panel("p2", "b", 5, n_objections=1),
    ]
    pairwise = [PairwiseResult("a", "b", "a", [], {})]
    bt = {"a": 2.0, "b": 0.5}

    rankings, _ = CampaignScorer().score(campaigns, panel, pairwise, bt)

    assert rankings[0].campaign_id == "a"
    assert rankings[0].verdict == Verdict.REVISE, f"Expected REVISE, got {rankings[0].verdict}"
    print("  PASS: #1 high objections → REVISE")


def test_kill_last_all_losses():
    """末位 + 全败 → KILL"""
    campaigns = [
        make_campaign("a", "A"),
        make_campaign("b", "B"),
        make_campaign("c", "C"),
    ]
    panel = [
        make_panel("p1", "a", 7, 1),
        make_panel("p1", "b", 5, 2),
        make_panel("p1", "c", 4, 3),
    ]
    pairwise = [
        PairwiseResult("a", "b", "a", [], {}),
        PairwiseResult("a", "c", "a", [], {}),
        PairwiseResult("b", "c", "b", [], {}),
    ]
    bt = {"a": 2.0, "b": 1.0, "c": 0.1}

    rankings, _ = CampaignScorer().score(campaigns, panel, pairwise, bt)

    last = rankings[-1]
    assert last.campaign_id == "c"
    assert last.verdict == Verdict.KILL, f"Expected KILL, got {last.verdict}"
    print("  PASS: last + all losses → KILL")


def test_kill_absolute_floor():
    """Panel 均分极低 → KILL 不管排名"""
    campaigns = [
        make_campaign("a", "A"),
        make_campaign("b", "B"),
    ]
    panel = [
        make_panel("p1", "a", 2, 1),
        make_panel("p1", "b", 1, 3),
    ]
    pairwise = [PairwiseResult("a", "b", "a", [], {})]
    bt = {"a": 2.0, "b": 0.5}

    rankings, _ = CampaignScorer().score(campaigns, panel, pairwise, bt)

    assert rankings[0].verdict == Verdict.KILL, f"#1 should KILL, got {rankings[0].verdict}"
    assert rankings[1].verdict == Verdict.KILL, f"#2 should KILL, got {rankings[1].verdict}"
    print("  PASS: absolute floor → both KILL")


def test_revise_middle_rank():
    """中间排名 → REVISE"""
    campaigns = [
        make_campaign("a", "A"),
        make_campaign("b", "B"),
        make_campaign("c", "C"),
        make_campaign("d", "D"),
    ]
    panel = [
        make_panel("p1", "a", 8, 1),
        make_panel("p1", "b", 6, 2),
        make_panel("p1", "c", 5, 2),
        make_panel("p1", "d", 4, 3),
    ]
    pairwise = [
        PairwiseResult("a", "b", "a", [], {}),
        PairwiseResult("a", "c", "a", [], {}),
        PairwiseResult("a", "d", "a", [], {}),
        PairwiseResult("b", "c", "b", [], {}),
        PairwiseResult("b", "d", "b", [], {}),
        PairwiseResult("c", "d", "c", [], {}),
    ]
    bt = {"a": 3.0, "b": 1.5, "c": 0.8, "d": 0.1}

    rankings, _ = CampaignScorer().score(campaigns, panel, pairwise, bt)

    assert rankings[1].verdict == Verdict.REVISE, f"#2 should REVISE, got {rankings[1].verdict}"
    assert rankings[2].verdict == Verdict.REVISE, f"#3 should REVISE, got {rankings[2].verdict}"
    print("  PASS: middle ranks → REVISE")


def test_tie_no_ship():
    """2 个方案平手 → no_clear_edge → #1 REVISE"""
    campaigns = [
        make_campaign("x", "X"),
        make_campaign("y", "Y"),
    ]
    panel = [
        make_panel("p1", "x", 7, 1),
        make_panel("p1", "y", 7, 1),
    ]
    pairwise = [PairwiseResult("x", "y", None, [], {})]
    bt = {"x": 1.0, "y": 1.0}

    rankings, board = CampaignScorer().score(campaigns, panel, pairwise, bt)

    assert rankings[0].verdict == Verdict.REVISE, f"Expected REVISE on tie, got {rankings[0].verdict}"
    print("  PASS: tie → #1 gets REVISE not SHIP")


def test_two_campaigns_clear_winner():
    """2 个方案，A 明显胜 → A=SHIP, B=KILL"""
    campaigns = [
        make_campaign("a", "A"),
        make_campaign("b", "B"),
    ]
    panel = [
        make_panel("p1", "a", 8, 1),
        make_panel("p2", "a", 7, 1),
        make_panel("p1", "b", 4, 3),
        make_panel("p2", "b", 3, 3),
    ]
    pairwise = [PairwiseResult("a", "b", "a", [], {})]
    bt = {"a": 2.0, "b": 0.5}

    rankings, _ = CampaignScorer().score(campaigns, panel, pairwise, bt)

    assert rankings[0].campaign_id == "a"
    assert rankings[0].verdict == Verdict.SHIP
    assert rankings[1].campaign_id == "b"
    assert rankings[1].verdict == Verdict.KILL
    print("  PASS: 2 campaigns, clear winner → SHIP + KILL")


# ============================================================
# Phase 5: market-layer tests
# ============================================================

def test_probability_board_completeness():
    """probability_board 包含所有必要字段"""
    campaigns = [
        make_campaign("a", "A"),
        make_campaign("b", "B"),
        make_campaign("c", "C"),
    ]
    panel = [
        make_panel("beauty_first", "a", 8, 1),
        make_panel("eye_health", "a", 7, 1),
        make_panel("beauty_first", "b", 6, 2),
        make_panel("eye_health", "b", 5, 2),
        make_panel("beauty_first", "c", 4, 3),
        make_panel("eye_health", "c", 4, 3),
    ]
    pairwise = [
        PairwiseResult("a", "b", "a", [], {}),
        PairwiseResult("a", "c", "a", [], {}),
        PairwiseResult("b", "c", "b", [], {}),
    ]
    bt = {"a": 2.0, "b": 1.0, "c": 0.5}

    rankings, board = CampaignScorer().score(campaigns, panel, pairwise, bt)

    # board 基本属性
    assert len(board.campaigns) == 3
    assert isinstance(board.lead_margin, float)
    assert isinstance(board.too_close_to_call, bool)
    assert board.confidence_threshold > 0
    assert board.rationale_for_uncertainty

    # 每个 campaign view 有 dimensions
    for cmv in board.campaigns:
        assert cmv.overall_score > 0
        assert cmv.verdict in ("ship", "revise", "kill")
        assert cmv.verdict_rationale

    # to_dict() 可序列化
    d = board.to_dict()
    assert "campaigns" in d
    assert "lead_margin" in d
    assert "too_close_to_call" in d
    print("  PASS: probability board completeness")


def test_probability_sum_normalized():
    """win_probability 归一化后总和 ≈ 1.0"""
    campaigns = [
        make_campaign("a", "A"),
        make_campaign("b", "B"),
        make_campaign("c", "C"),
    ]
    panel = [
        make_panel("p1", "a", 8, 1),
        make_panel("p1", "b", 6, 2),
        make_panel("p1", "c", 4, 3),
    ]
    pairwise = [
        PairwiseResult("a", "b", "a", [], {}),
        PairwiseResult("a", "c", "a", [], {}),
        PairwiseResult("b", "c", "b", [], {}),
    ]
    bt = {"a": 2.0, "b": 1.0, "c": 0.5}

    _, board = CampaignScorer().score(campaigns, panel, pairwise, bt)

    total_prob = sum(c.overall_score for c in board.campaigns)
    assert abs(total_prob - 1.0) < 0.01, f"Probabilities sum to {total_prob}, expected ~1.0"
    print("  PASS: probability sum ≈ 1.0")


def test_no_clear_edge_when_close():
    """top two very close → too_close_to_call=True, #1 gets REVISE"""
    campaigns = [
        make_campaign("a", "A"),
        make_campaign("b", "B"),
    ]
    # Nearly identical scores + tie
    panel = [
        make_panel("p1", "a", 7.0, 1),
        make_panel("p2", "a", 7.0, 1),
        make_panel("p1", "b", 7.0, 1),
        make_panel("p2", "b", 7.0, 1),
    ]
    pairwise = [PairwiseResult("a", "b", None, [], {})]  # tie
    bt = {"a": 1.0, "b": 1.0}  # equal BT

    rankings, board = CampaignScorer().score(campaigns, panel, pairwise, bt)

    assert board.too_close_to_call, f"Expected too_close_to_call=True, spread={board.lead_margin}"
    assert rankings[0].verdict == Verdict.REVISE
    print("  PASS: close scores → no_clear_edge + REVISE")


def test_submarket_output_complete():
    """dimensions 覆盖所有 5 个维度"""
    campaigns = [
        make_campaign("a", "A"),
        make_campaign("b", "B"),
    ]
    panel = [
        make_panel("beauty_first", "a", 8, 1),
        make_panel("eye_health", "a", 7, 1),
        make_panel("price_conscious", "a", 6, 1),
        make_panel("daily_wearer", "a", 7, 1),
        make_panel("acuvue_switcher", "a", 7, 1),
        make_panel("beauty_first", "b", 5, 2),
        make_panel("eye_health", "b", 5, 2),
        make_panel("price_conscious", "b", 5, 2),
        make_panel("daily_wearer", "b", 5, 2),
        make_panel("acuvue_switcher", "b", 5, 2),
    ]
    pairwise = [PairwiseResult("a", "b", "a", [], {})]
    bt = {"a": 2.0, "b": 0.5}

    _, board = CampaignScorer().score(campaigns, panel, pairwise, bt)

    # dimensions list should have entries for all 5 keys × 2 campaigns = 10
    assert len(board.dimension_scores) == 10, f"Expected 10 dimension entries, got {len(board.dimension_scores)}"

    # Each campaign view should have all 5 dimension keys
    for cmv in board.campaigns:
        for key in DIMENSION_KEYS:
            assert key in cmv.dimension_scores, f"Missing dimension '{key}' for {cmv.campaign_id}"
    print("  PASS: sub-market output covers all 5 dimensions")


def test_claim_risk_penalty():
    """high claim risk keywords → lower claim_risk sub-market score"""
    campaigns = [
        make_campaign("risky", "Risky"),
        make_campaign("safe", "Safe"),
    ]
    # "risky" has claim risk keywords in objections
    panel = [
        make_panel("p1", "risky", 7, obj_texts=["夸张的功效声称", "不可信的临床数据", "缺乏安全背书"]),
        make_panel("p2", "risky", 7, obj_texts=["虚假宣传风险", "过度承诺"]),
        make_panel("p1", "safe", 7, obj_texts=["价格偏高"]),
        make_panel("p2", "safe", 7, obj_texts=["渠道较窄"]),
    ]
    pairwise = [PairwiseResult("risky", "safe", None, [], {})]
    bt = {"risky": 1.0, "safe": 1.0}

    _, board = CampaignScorer().score(campaigns, panel, pairwise, bt)

    # Find claim_risk sub-market probs
    risk_prob = {sm.campaign_id: sm.score for sm in board.dimension_scores if sm.dimension_key == "claim_risk"}
    assert risk_prob["risky"] < risk_prob["safe"], (
        f"Risky campaign should have lower claim_risk prob: risky={risk_prob['risky']:.3f}, safe={risk_prob['safe']:.3f}"
    )
    print("  PASS: claim risk keywords → lower claim_risk probability")


def test_resolution_record_creation():
    """resolution tracker 可以创建结算记录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cal = JudgeCalibration(calibration_dir=tmpdir)
        tracker = ResolutionTracker()
        tracker.calibration = cal

        record = tracker.resolve(
            set_id="test-set",
            winner_campaign_id="a",
            actual_metrics={"ctr": 0.03, "cvr": 0.02},
            predicted_probabilities={"a": 0.6, "b": 0.4},
            notes="test resolution",
        )

        assert record.set_id == "test-set"
        assert record.campaign_id == "a"
        assert record.predicted_win_prob == 0.6
        assert record.was_actual_winner is True

        # Verify persisted
        resolutions = cal.load_resolutions()
        assert len(resolutions) == 2  # winner + 1 loser
        winner_rec = [r for r in resolutions if r["was_actual_winner"]][0]
        assert winner_rec["predicted_win_prob"] == 0.6
        print("  PASS: resolution record created and persisted")


def test_calibration_no_history():
    """judge calibration 在无历史数据时不报错，返回空权重"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cal = JudgeCalibration(calibration_dir=tmpdir)

        judge_w, persona_w = cal.get_weights()
        assert judge_w == {}
        assert persona_w == {}

        stats = cal.get_all_stats()
        assert stats == []

        # recalibrate with no data
        result = cal.recalibrate()
        assert result["status"] == "insufficient_data"
        print("  PASS: calibration with no history → empty weights, no error")


# ============================================================
# brief_type dim_boost 混入测试 (Task 1 — 260318-ohu)
# ============================================================

def make_panel_with_dim(persona_id, campaign_id, score, dimension_scores=None, n_objections=1):
    """构造带 dimension_scores 的 PanelScore（模拟 LLM 直接输出维度分）"""
    from app.models.evaluation import PanelScore as PS
    objs = [f"obj_{i}" for i in range(n_objections)]
    ps = PS(
        persona_id=persona_id, persona_name=f"P_{persona_id}",
        campaign_id=campaign_id, score=score,
        objections=objs, strengths=["str_1"], reasoning="ok",
    )
    if dimension_scores:
        ps.dimension_scores = dimension_scores
    return ps


def test_brief_type_none_backward_compat():
    """brief_type=None 时，dim_boost 贡献为 0，行为与修复前完全一致"""
    campaigns = [make_campaign("a", "A"), make_campaign("b", "B")]
    panel = [
        make_panel("p1", "a", 8), make_panel("p2", "a", 8),
        make_panel("p1", "b", 5), make_panel("p2", "b", 5),
    ]
    pairwise = [PairwiseResult("a", "b", "a", [], {})]
    bt = {"a": 2.0, "b": 0.5}

    # brief_type=None scorer
    scorer_none = CampaignScorer(brief_type=None)
    rankings_none, _ = scorer_none.score(campaigns, panel, pairwise, bt)

    # 无 brief_type 时 a 仍然排第一
    assert rankings_none[0].campaign_id == "a", (
        f"brief_type=None: expected a first, got {rankings_none[0].campaign_id}"
    )
    print("  PASS: brief_type=None → a still ranks #1 (backward compat)")


def test_brief_type_brand_emotional_wins():
    """brief_type=brand 时，高情感共鸣方案 overall_score > 高转化方案"""
    campaigns = [
        make_campaign("emotional", "高定情绪大片"),
        make_campaign("promo", "明星同款快转化"),
    ]
    # 情感方案在 emotional_resonance 维度得高分，促销方案在 conversion_readiness 得高分
    panel = [
        make_panel_with_dim("p1", "emotional", 7, {
            "thumb_stop": 7, "clarity": 6, "trust": 6,
            "conversion_readiness": 4, "claim_risk": 7,
            "emotional_resonance": 9,  # 情感高分
        }),
        make_panel_with_dim("p2", "emotional", 7, {
            "thumb_stop": 7, "clarity": 6, "trust": 6,
            "conversion_readiness": 4, "claim_risk": 7,
            "emotional_resonance": 9,
        }),
        make_panel_with_dim("p1", "promo", 7, {
            "thumb_stop": 6, "clarity": 7, "trust": 5,
            "conversion_readiness": 9, "claim_risk": 5,  # 转化高分
            "emotional_resonance": 3,  # 情感低分
        }),
        make_panel_with_dim("p2", "promo", 7, {
            "thumb_stop": 6, "clarity": 7, "trust": 5,
            "conversion_readiness": 9, "claim_risk": 5,
            "emotional_resonance": 3,
        }),
    ]
    pairwise = [PairwiseResult("emotional", "promo", None, [], {})]  # 平局（纯依赖维度分）
    bt = {"emotional": 1.0, "promo": 1.0}  # 相等 BT，排名完全靠维度信号

    from app.models.campaign import BriefType
    scorer_brand = CampaignScorer(brief_type=BriefType.BRAND)
    rankings, board = scorer_brand.score(campaigns, panel, pairwise, bt)

    emotional_score = next(c.overall_score for c in board.campaigns if c.campaign_id == "emotional")
    promo_score = next(c.overall_score for c in board.campaigns if c.campaign_id == "promo")

    assert emotional_score > promo_score, (
        f"brief_type=brand: emotional_score={emotional_score:.4f} should > promo_score={promo_score:.4f}"
    )
    assert rankings[0].campaign_id == "emotional", (
        f"brief_type=brand: expected emotional first, got {rankings[0].campaign_id}"
    )
    print(f"  PASS: brief_type=brand → emotional wins ({emotional_score:.4f} > {promo_score:.4f})")


def test_brief_type_conversion_wins():
    """brief_type=conversion 时，高转化方案 overall_score > 情感化方案"""
    campaigns = [
        make_campaign("promo", "高转化促销"),
        make_campaign("brand_ad", "品牌情感片"),
    ]
    panel = [
        make_panel_with_dim("p1", "promo", 7, {
            "thumb_stop": 6, "clarity": 8, "trust": 6,
            "conversion_readiness": 9, "claim_risk": 6,  # 转化高
            "emotional_resonance": 3,
        }),
        make_panel_with_dim("p2", "promo", 7, {
            "thumb_stop": 6, "clarity": 8, "trust": 6,
            "conversion_readiness": 9, "claim_risk": 6,
            "emotional_resonance": 3,
        }),
        make_panel_with_dim("p1", "brand_ad", 7, {
            "thumb_stop": 7, "clarity": 5, "trust": 6,
            "conversion_readiness": 3, "claim_risk": 7,  # 转化低
            "emotional_resonance": 9,
        }),
        make_panel_with_dim("p2", "brand_ad", 7, {
            "thumb_stop": 7, "clarity": 5, "trust": 6,
            "conversion_readiness": 3, "claim_risk": 7,
            "emotional_resonance": 9,
        }),
    ]
    pairwise = [PairwiseResult("promo", "brand_ad", None, [], {})]
    bt = {"promo": 1.0, "brand_ad": 1.0}

    from app.models.campaign import BriefType
    scorer_conv = CampaignScorer(brief_type=BriefType.CONVERSION)
    rankings, board = scorer_conv.score(campaigns, panel, pairwise, bt)

    promo_score = next(c.overall_score for c in board.campaigns if c.campaign_id == "promo")
    brand_score = next(c.overall_score for c in board.campaigns if c.campaign_id == "brand_ad")

    assert promo_score > brand_score, (
        f"brief_type=conversion: promo_score={promo_score:.4f} should > brand_score={brand_score:.4f}"
    )
    assert rankings[0].campaign_id == "promo", (
        f"brief_type=conversion: expected promo first, got {rankings[0].campaign_id}"
    )
    print(f"  PASS: brief_type=conversion → promo wins ({promo_score:.4f} > {brand_score:.4f})")


if __name__ == "__main__":
    print("=== Scorer Verdict Tests (Phase 4.5) ===")
    test_ship_rank1_dominant()
    test_revise_rank1_high_objections()
    test_kill_last_all_losses()
    test_kill_absolute_floor()
    test_revise_middle_rank()
    test_tie_no_ship()
    test_two_campaigns_clear_winner()

    print("\n=== Market Layer Tests (Phase 5) ===")
    test_probability_board_completeness()
    test_probability_sum_normalized()
    test_no_clear_edge_when_close()
    test_submarket_output_complete()
    test_claim_risk_penalty()
    test_resolution_record_creation()
    test_calibration_no_history()

    print("\nALL TESTS PASSED")
