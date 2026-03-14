"""
Brandiction PR4 — 渠道效能加权、预算缩放、竞品事件影响、回测验证
"""

import sys
import os
import tempfile
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.brand_state import (
    BrandState,
    PerceptionVector,
    PERCEPTION_DIMENSIONS,
)
from app.models.brandiction import (
    HistoricalIntervention,
    HistoricalOutcomeWindow,
    BrandSignalSnapshot,
    CompetitorEvent,
)
from app.services.brandiction_store import BrandictionStore
from app.services.brand_state_engine import (
    BrandStateEngine,
    THEME_DIM_MAP,
    CHANNEL_EFFECTIVENESS,
    COMPETITOR_IMPACT_MAP,
    BUDGET_BASELINE,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

def _fresh_store():
    BrandictionStore._reset_instance()
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = BrandictionStore(db_path=path)
    return store, path


def _cleanup(store, path):
    BrandictionStore._reset_instance()
    try:
        os.unlink(path)
    except OSError:
        pass


# ------------------------------------------------------------------
# Theme config externalization
# ------------------------------------------------------------------

class TestThemeConfig:
    def test_theme_dim_map_is_module_level(self):
        """theme_dim_map 应该是模块级常量，不是硬编码在方法里"""
        assert isinstance(THEME_DIM_MAP, dict)
        assert "science" in THEME_DIM_MAP
        assert THEME_DIM_MAP["science"] == "science_credibility"
        assert THEME_DIM_MAP["kol"] == "social_proof"

    def test_all_mapped_dims_are_valid(self):
        """所有映射目标都是合法的感知维度"""
        for theme, dim in THEME_DIM_MAP.items():
            assert dim in PERCEPTION_DIMENSIONS, f"{theme} maps to invalid dim {dim}"


# ------------------------------------------------------------------
# Channel effectiveness scaling
# ------------------------------------------------------------------

class TestChannelScaling:
    def test_no_channel_mix_is_identity(self):
        """无渠道时 delta 不变"""
        engine = BrandStateEngine.__new__(BrandStateEngine)
        delta = {"science_credibility": 0.05, "social_proof": 0.02}
        result = engine._apply_channel_scaling(delta, None)
        assert result == delta

    def test_empty_channel_mix_is_identity(self):
        engine = BrandStateEngine.__new__(BrandStateEngine)
        delta = {"science_credibility": 0.05}
        result = engine._apply_channel_scaling(delta, [])
        assert result == delta

    def test_single_channel_amplifies(self):
        """bilibili 应放大 science_credibility（1.4x）"""
        engine = BrandStateEngine.__new__(BrandStateEngine)
        delta = {d: 0.0 for d in PERCEPTION_DIMENSIONS}
        delta["science_credibility"] = 0.10
        result = engine._apply_channel_scaling(delta, ["bilibili"])
        expected = 0.10 * CHANNEL_EFFECTIVENESS["bilibili"]["science_credibility"]
        assert abs(result["science_credibility"] - expected) < 1e-6

    def test_single_channel_dampens(self):
        """douyin 应抑制 science_credibility（0.8x）"""
        engine = BrandStateEngine.__new__(BrandStateEngine)
        delta = {d: 0.0 for d in PERCEPTION_DIMENSIONS}
        delta["science_credibility"] = 0.10
        result = engine._apply_channel_scaling(delta, ["douyin"])
        expected = 0.10 * CHANNEL_EFFECTIVENESS["douyin"]["science_credibility"]
        assert abs(result["science_credibility"] - expected) < 1e-6

    def test_multi_channel_averages(self):
        """多渠道取效能系数平均"""
        engine = BrandStateEngine.__new__(BrandStateEngine)
        delta = {d: 0.0 for d in PERCEPTION_DIMENSIONS}
        delta["science_credibility"] = 0.10

        # bilibili=1.4, douyin=0.8 → avg=1.1
        result = engine._apply_channel_scaling(delta, ["bilibili", "douyin"])
        bili_eff = CHANNEL_EFFECTIVENESS["bilibili"]["science_credibility"]
        douyin_eff = CHANNEL_EFFECTIVENESS["douyin"]["science_credibility"]
        expected = 0.10 * (bili_eff + douyin_eff) / 2
        assert abs(result["science_credibility"] - expected) < 1e-6

    def test_unknown_channel_uses_1x(self):
        """未知渠道系数为 1.0"""
        engine = BrandStateEngine.__new__(BrandStateEngine)
        delta = {d: 0.0 for d in PERCEPTION_DIMENSIONS}
        delta["social_proof"] = 0.10
        result = engine._apply_channel_scaling(delta, ["unknown_channel"])
        assert abs(result["social_proof"] - 0.10) < 1e-6

    def test_channel_case_insensitive(self):
        """渠道名大小写不敏感"""
        engine = BrandStateEngine.__new__(BrandStateEngine)
        delta = {d: 0.0 for d in PERCEPTION_DIMENSIONS}
        delta["social_proof"] = 0.10
        r1 = engine._apply_channel_scaling(delta, ["Douyin"])
        r2 = engine._apply_channel_scaling(delta, ["douyin"])
        assert abs(r1["social_proof"] - r2["social_proof"]) < 1e-6

    def test_channel_scaling_in_compute_impact(self):
        """compute_intervention_impact 中渠道缩放生效"""
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)
            iv_bili = HistoricalIntervention(
                "iv1", "r1", theme="science", channel_mix=["bilibili"],
            )
            iv_douyin = HistoricalIntervention(
                "iv2", "r1", theme="science", channel_mix=["douyin"],
            )
            d_bili = engine.compute_intervention_impact(iv_bili, [])
            d_douyin = engine.compute_intervention_impact(iv_douyin, [])
            # bilibili science_credibility 效能 > douyin
            assert d_bili["science_credibility"] > d_douyin["science_credibility"]
        finally:
            _cleanup(store, path)


# ------------------------------------------------------------------
# Budget scaling
# ------------------------------------------------------------------

class TestBudgetScaling:
    def test_no_budget_is_identity(self):
        engine = BrandStateEngine.__new__(BrandStateEngine)
        delta = {"science_credibility": 0.05}
        result = engine._apply_budget_scaling(delta, None)
        assert result == delta

    def test_zero_budget_is_identity(self):
        engine = BrandStateEngine.__new__(BrandStateEngine)
        delta = {"science_credibility": 0.05}
        result = engine._apply_budget_scaling(delta, 0)
        assert result == delta

    def test_baseline_budget_multiplier_is_1(self):
        """50000 基准预算时 multiplier = log2(2) = 1.0"""
        engine = BrandStateEngine.__new__(BrandStateEngine)
        delta = {"science_credibility": 0.10}
        result = engine._apply_budget_scaling(delta, BUDGET_BASELINE)
        expected = 0.10 * math.log2(BUDGET_BASELINE / BUDGET_BASELINE + 1)
        assert abs(result["science_credibility"] - expected) < 1e-6

    def test_higher_budget_amplifies(self):
        """更大预算 → 更大影响"""
        engine = BrandStateEngine.__new__(BrandStateEngine)
        delta = {"science_credibility": 0.10}
        r_50k = engine._apply_budget_scaling(dict(delta), BUDGET_BASELINE)
        r_200k = engine._apply_budget_scaling(dict(delta), 200000)
        assert r_200k["science_credibility"] > r_50k["science_credibility"]

    def test_diminishing_returns(self):
        """边际递减：从 50k→100k 的增幅 > 100k→150k"""
        engine = BrandStateEngine.__new__(BrandStateEngine)
        delta = {"science_credibility": 0.10}
        r_50 = engine._apply_budget_scaling(dict(delta), 50000)
        r_100 = engine._apply_budget_scaling(dict(delta), 100000)
        r_150 = engine._apply_budget_scaling(dict(delta), 150000)
        gain_50_100 = r_100["science_credibility"] - r_50["science_credibility"]
        gain_100_150 = r_150["science_credibility"] - r_100["science_credibility"]
        assert gain_50_100 > gain_100_150, "should show diminishing returns"

    def test_small_budget_dampens(self):
        """小预算应打折"""
        engine = BrandStateEngine.__new__(BrandStateEngine)
        delta = {"science_credibility": 0.10}
        r_5k = engine._apply_budget_scaling(dict(delta), 5000)
        r_50k = engine._apply_budget_scaling(dict(delta), 50000)
        assert r_5k["science_credibility"] < r_50k["science_credibility"]

    def test_budget_scaling_clamped(self):
        """极端预算不应导致 multiplier 超出 [0.3, 2.0]"""
        engine = BrandStateEngine.__new__(BrandStateEngine)
        delta = {"science_credibility": 0.10}
        # 极大预算
        r_huge = engine._apply_budget_scaling(dict(delta), 100_000_000)
        assert r_huge["science_credibility"] <= 0.20 + 1e-6  # 0.10 * 2.0
        # 极小预算
        r_tiny = engine._apply_budget_scaling(dict(delta), 1)
        assert r_tiny["science_credibility"] >= 0.03 - 1e-6  # 0.10 * 0.3

    def test_budget_in_compute_impact(self):
        """compute_intervention_impact 中预算缩放生效"""
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)
            iv_low = HistoricalIntervention(
                "iv1", "r1", theme="science", budget=10000,
            )
            iv_high = HistoricalIntervention(
                "iv2", "r1", theme="science", budget=200000,
            )
            d_low = engine.compute_intervention_impact(iv_low, [])
            d_high = engine.compute_intervention_impact(iv_high, [])
            assert d_high["science_credibility"] > d_low["science_credibility"]
        finally:
            _cleanup(store, path)


# ------------------------------------------------------------------
# Competitor event integration
# ------------------------------------------------------------------

class TestCompetitorIntegration:
    def test_no_competitor_events_no_pressure(self):
        """无竞品事件时 competitor_pressure 不变"""
        result = BrandStateEngine._compute_competitor_pressure(
            "2025-06-01", "2025-06-30", [],
        )
        assert result == {}

    def test_single_event_in_window(self):
        """窗口内一个 high-impact 竞品事件"""
        ev = CompetitorEvent("ev1", "2025-06-15", "acuvue",
                             event_type="new_launch", impact_estimate="high")
        result = BrandStateEngine._compute_competitor_pressure(
            "2025-06-01", "2025-06-30", [ev],
        )
        assert "competitor_pressure" in result
        assert abs(result["competitor_pressure"] - COMPETITOR_IMPACT_MAP["high"]) < 1e-4

    def test_event_outside_window_ignored(self):
        """窗口外的事件不应影响"""
        ev = CompetitorEvent("ev1", "2025-07-15", "acuvue",
                             event_type="price_cut", impact_estimate="high")
        result = BrandStateEngine._compute_competitor_pressure(
            "2025-06-01", "2025-06-30", [ev],
        )
        assert result == {}

    def test_multiple_events_stack(self):
        """多个竞品事件叠加"""
        events = [
            CompetitorEvent("ev1", "2025-06-10", "acuvue", impact_estimate="high"),
            CompetitorEvent("ev2", "2025-06-20", "bausch", impact_estimate="medium"),
        ]
        result = BrandStateEngine._compute_competitor_pressure(
            "2025-06-01", "2025-06-30", events,
        )
        expected = COMPETITOR_IMPACT_MAP["high"] + COMPETITOR_IMPACT_MAP["medium"]
        assert abs(result["competitor_pressure"] - expected) < 1e-4

    def test_pressure_capped_at_015(self):
        """竞品压力上限 0.15"""
        events = [
            CompetitorEvent(f"ev{i}", "2025-06-15", "comp", impact_estimate="high")
            for i in range(10)
        ]
        result = BrandStateEngine._compute_competitor_pressure(
            "2025-06-01", "2025-06-30", events,
        )
        assert result["competitor_pressure"] <= 0.15 + 1e-6

    def test_no_date_start_returns_empty(self):
        ev = CompetitorEvent("ev1", "2025-06-15", "acuvue", impact_estimate="high")
        result = BrandStateEngine._compute_competitor_pressure(None, None, [ev])
        assert result == {}

    def test_replay_includes_competitor_pressure(self):
        """replay 时竞品事件应影响 competitor_pressure"""
        store, path = _fresh_store()
        try:
            # 添加干预
            store.save_intervention(HistoricalIntervention(
                "iv1", "r1", product_line="moodyplus",
                date_start="2025-06-01", date_end="2025-06-30",
                theme="science", audience_segment="general",
            ))
            store.save_outcome(HistoricalOutcomeWindow(
                "oc1", "iv1", brand_lift=0.1,
            ))
            # 添加同期竞品事件
            store.save_competitor_event(CompetitorEvent(
                "ev1", "2025-06-15", "acuvue",
                event_type="new_launch", impact_estimate="high",
            ))
            # 添加初始 signal
            store.save_signal(BrandSignalSnapshot(
                "sig1", "2025-05-01", dimension="science_credibility", value=0.5,
            ))

            engine = BrandStateEngine(store)
            states = engine.replay_history()

            assert len(states) >= 2
            final = states[-1]
            # 竞品事件应使 competitor_pressure 高于初始值 (0.3)
            assert final.perception.competitor_pressure > 0.3
            # evidence 应包含竞品事件标记
            assert "competitor_events_in_window" in final.evidence_sources
        finally:
            _cleanup(store, path)

    def test_replay_no_competitor_no_extra_evidence(self):
        """无竞品事件时 evidence 不含 competitor 标记"""
        store, path = _fresh_store()
        try:
            store.save_intervention(HistoricalIntervention(
                "iv1", "r1", product_line="moodyplus",
                date_start="2025-06-01", date_end="2025-06-30",
                theme="science", audience_segment="general",
            ))
            store.save_signal(BrandSignalSnapshot(
                "sig1", "2025-05-01", dimension="science_credibility", value=0.5,
            ))

            engine = BrandStateEngine(store)
            states = engine.replay_history()
            final = states[-1]
            assert "competitor_events_in_window" not in final.evidence_sources
        finally:
            _cleanup(store, path)


# ------------------------------------------------------------------
# Backtesting
# ------------------------------------------------------------------

class TestBacktest:
    def _setup_backtest_data(self):
        store, path = _fresh_store()
        # 3 science interventions with outcomes
        for i in range(1, 4):
            store.save_intervention(HistoricalIntervention(
                f"iv{i}", "r1", product_line="moodyplus",
                theme="science", audience_segment="general",
                date_start=f"2025-0{i}-01",
            ))
            store.save_outcome(HistoricalOutcomeWindow(
                f"oc{i}", f"iv{i}",
                brand_lift=0.1 * i,
                comment_sentiment=0.3,
            ))
        # 1 beauty intervention
        store.save_intervention(HistoricalIntervention(
            "iv-beauty", "r1", product_line="moodyplus",
            theme="beauty", audience_segment="general",
            date_start="2025-04-01",
        ))
        store.save_outcome(HistoricalOutcomeWindow(
            "oc-beauty", "iv-beauty",
            brand_lift=0.2,
        ))
        return store, path

    def test_backtest_basic(self):
        store, path = self._setup_backtest_data()
        try:
            engine = BrandStateEngine(store)
            result = engine.backtest()

            assert result["total_interventions"] == 4
            assert result["tested"] == 4
            assert result["skipped"] == 0
            assert "mean_absolute_error" in result
            assert isinstance(result["mean_absolute_error"], float)
            assert len(result["details"]) == 4
        finally:
            _cleanup(store, path)

    def test_backtest_has_per_dimension_mae(self):
        store, path = self._setup_backtest_data()
        try:
            engine = BrandStateEngine(store)
            result = engine.backtest()

            mae = result["per_dimension_mae"]
            for dim in PERCEPTION_DIMENSIONS:
                assert dim in mae
                assert mae[dim] >= 0
        finally:
            _cleanup(store, path)

    def test_backtest_science_uses_leave_one_out(self):
        """science 的 holdout 应用其他 2 条 science 的平均来预测"""
        store, path = self._setup_backtest_data()
        try:
            engine = BrandStateEngine(store)
            result = engine.backtest()

            science_details = [d for d in result["details"] if d["theme"] == "science"]
            assert len(science_details) == 3
            for d in science_details:
                assert d["similar_count"] == 2, \
                    "each science holdout should match other 2 science interventions"
                assert d["method"] == "historical_average"
        finally:
            _cleanup(store, path)

    def test_backtest_beauty_falls_back_to_heuristic(self):
        """唯一的 beauty 干预留一后无同类 → fallback"""
        store, path = self._setup_backtest_data()
        try:
            engine = BrandStateEngine(store)
            result = engine.backtest()

            beauty_details = [d for d in result["details"] if d["theme"] == "beauty"]
            assert len(beauty_details) == 1
            assert beauty_details[0]["similar_count"] == 0
            assert beauty_details[0]["method"] == "heuristic_fallback"
        finally:
            _cleanup(store, path)

    def test_backtest_skips_no_theme(self):
        """无 theme 的 intervention 应被跳过"""
        store, path = _fresh_store()
        try:
            store.save_intervention(HistoricalIntervention(
                "iv-notheme", "r1", product_line="moodyplus",
                theme="", audience_segment="general",
            ))
            store.save_outcome(HistoricalOutcomeWindow(
                "oc-nt", "iv-notheme", brand_lift=0.1,
            ))

            engine = BrandStateEngine(store)
            result = engine.backtest()
            assert result["tested"] == 0
            assert result["skipped"] == 1
        finally:
            _cleanup(store, path)

    def test_backtest_skips_no_outcomes(self):
        """无 outcome 的 intervention 应被跳过"""
        store, path = _fresh_store()
        try:
            store.save_intervention(HistoricalIntervention(
                "iv-nooc", "r1", product_line="moodyplus",
                theme="science", audience_segment="general",
            ))

            engine = BrandStateEngine(store)
            result = engine.backtest()
            assert result["tested"] == 0
            assert result["skipped"] == 1
        finally:
            _cleanup(store, path)

    def test_backtest_respects_segment(self):
        """回测应只比较同 segment 的数据"""
        store, path = _fresh_store()
        try:
            # general segment
            store.save_intervention(HistoricalIntervention(
                "iv-gen", "r1", product_line="moodyplus",
                theme="science", audience_segment="general",
            ))
            store.save_outcome(HistoricalOutcomeWindow(
                "oc-gen", "iv-gen", brand_lift=0.1,
            ))
            # young_female segment
            store.save_intervention(HistoricalIntervention(
                "iv-yf", "r1", product_line="moodyplus",
                theme="science", audience_segment="young_female",
            ))
            store.save_outcome(HistoricalOutcomeWindow(
                "oc-yf", "iv-yf", brand_lift=0.5,
            ))

            engine = BrandStateEngine(store)
            result_gen = engine.backtest(audience_segment="general")
            result_yf = engine.backtest(audience_segment="young_female")

            assert result_gen["total_interventions"] == 1
            assert result_yf["total_interventions"] == 1
        finally:
            _cleanup(store, path)

    def test_backtest_error_values_are_reasonable(self):
        """MAE 应在合理范围内 (< 0.3，因为 delta clamp 到 [-0.3, 0.3])"""
        store, path = self._setup_backtest_data()
        try:
            engine = BrandStateEngine(store)
            result = engine.backtest()
            assert result["mean_absolute_error"] < 0.3
        finally:
            _cleanup(store, path)

    def test_backtest_includes_competitor_pressure(self):
        """回测口径应与 replay 一致：带竞品事件的 holdout 不应得到假零误差"""
        store, path = _fresh_store()
        try:
            # 一条干预 + outcome + 同期 high 竞品事件
            store.save_intervention(HistoricalIntervention(
                "iv-comp", "r1", product_line="moodyplus",
                date_start="2025-06-01", date_end="2025-06-30",
                theme="science", audience_segment="general",
            ))
            store.save_outcome(HistoricalOutcomeWindow(
                "oc-comp", "iv-comp", brand_lift=0.1,
            ))
            store.save_competitor_event(CompetitorEvent(
                "ev-comp", "2025-06-15", "acuvue",
                event_type="new_launch", impact_estimate="high",
            ))

            engine = BrandStateEngine(store)
            result = engine.backtest()

            assert result["tested"] == 1
            detail = result["details"][0]
            # actual_delta 应包含非零的 competitor_pressure
            assert detail["actual_delta"]["competitor_pressure"] > 0, \
                "backtest actual_delta should include competitor_pressure from events"
            # predicted_delta 也应包含（heuristic fallback + 同窗口竞品）
            assert detail["predicted_delta"]["competitor_pressure"] > 0, \
                "backtest predicted_delta should include competitor_pressure"
        finally:
            _cleanup(store, path)


# ------------------------------------------------------------------
# Combined channel + budget + competitor in full flow
# ------------------------------------------------------------------

class TestCombinedFlow:
    def test_full_flow_with_all_pr4_features(self):
        """完整流程：渠道+预算+竞品 → replay → predict"""
        store, path = _fresh_store()
        try:
            # 初始信号
            store.save_signal(BrandSignalSnapshot(
                "sig1", "2025-01-01", dimension="science_credibility", value=0.5,
            ))

            # 干预（bilibili渠道，大预算）
            store.save_intervention(HistoricalIntervention(
                "iv1", "r1", product_line="moodyplus",
                date_start="2025-02-01", date_end="2025-02-28",
                theme="science", channel_mix=["bilibili"],
                budget=100000, audience_segment="general",
            ))
            store.save_outcome(HistoricalOutcomeWindow(
                "oc1", "iv1", brand_lift=0.15, comment_sentiment=0.5,
            ))

            # 竞品事件
            store.save_competitor_event(CompetitorEvent(
                "ev1", "2025-02-15", "acuvue",
                event_type="price_cut", impact_estimate="medium",
            ))

            engine = BrandStateEngine(store)

            # Replay
            states = engine.replay_history()
            assert len(states) >= 2

            final = states[-1]
            # bilibili 放大了 science_credibility
            assert final.perception.science_credibility > 0.5
            # 竞品压力上升
            assert final.perception.competitor_pressure > 0.3

            # Predict（用 redbook 渠道）
            prediction = engine.predict_impact(
                {"theme": "science", "channel_mix": ["redbook"], "budget": 50000},
            )
            assert "delta" in prediction
            assert prediction["similar_interventions"] == 1

            # Backtest
            bt = engine.backtest()
            assert bt["total_interventions"] == 1
        finally:
            _cleanup(store, path)

    def test_predict_with_channel_and_budget(self):
        """predict_impact 应考虑 plan 中的 channel 和 budget（通过 heuristic fallback）"""
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)

            # 无历史 → heuristic fallback
            r_bili_big = engine.predict_impact({
                "theme": "science",
                "channel_mix": ["bilibili"],
                "budget": 200000,
            })
            r_douyin_small = engine.predict_impact({
                "theme": "science",
                "channel_mix": ["douyin"],
                "budget": 10000,
            })

            # bilibili+大预算 应产生更大的 science delta
            assert r_bili_big["delta"]["science_credibility"] > \
                r_douyin_small["delta"]["science_credibility"]
        finally:
            _cleanup(store, path)
