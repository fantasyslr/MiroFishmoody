"""
Brandiction PR5 — 时间衰减、多步情景模拟、情景对比、竞品注入重构
"""

import sys
import os
import math
import tempfile

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
    SIGNAL_HALF_LIFE_DAYS,
    _parse_date,
    _decay_weight,
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
# Temporal decay helpers
# ------------------------------------------------------------------

class TestDecayHelpers:
    def test_parse_date_iso(self):
        d = _parse_date("2025-06-15")
        assert d is not None
        assert d.year == 2025 and d.month == 6 and d.day == 15

    def test_parse_date_with_time(self):
        d = _parse_date("2025-06-15T12:30:00")
        assert d is not None

    def test_parse_date_invalid(self):
        assert _parse_date("not-a-date") is None

    def test_decay_weight_same_day_is_1(self):
        from datetime import datetime
        ref = datetime(2025, 6, 15)
        w = _decay_weight("2025-06-15", ref)
        assert abs(w - 1.0) < 1e-6

    def test_decay_weight_future_is_1(self):
        from datetime import datetime
        ref = datetime(2025, 6, 15)
        w = _decay_weight("2025-06-20", ref)
        assert abs(w - 1.0) < 1e-6

    def test_decay_weight_half_life(self):
        """半衰期后权重约为 0.5"""
        from datetime import datetime, timedelta
        ref = datetime(2025, 6, 15)
        half_life_ago = ref - timedelta(days=SIGNAL_HALF_LIFE_DAYS)
        w = _decay_weight(half_life_ago.strftime("%Y-%m-%d"), ref)
        assert abs(w - 0.5) < 0.01

    def test_decay_weight_old_signal_is_small(self):
        """很旧的信号权重接近 0"""
        from datetime import datetime
        ref = datetime(2025, 6, 15)
        w = _decay_weight("2023-01-01", ref)
        assert w < 0.1


# ------------------------------------------------------------------
# Temporal decay in build_state_from_signals
# ------------------------------------------------------------------

class TestTemporalDecay:
    def test_single_signal_no_decay_effect(self):
        """只有一条信号时衰减不影响结果"""
        store, path = _fresh_store()
        try:
            store.save_signal(BrandSignalSnapshot(
                "sig1", "2025-06-01", dimension="science_credibility", value=0.7,
            ))
            engine = BrandStateEngine(store)
            state = engine.build_state_from_signals("2025-06-15")
            assert abs(state.perception.science_credibility - 0.7) < 1e-6
        finally:
            _cleanup(store, path)

    def test_recent_signal_weighted_more(self):
        """近期信号权重更高"""
        store, path = _fresh_store()
        try:
            # 旧信号: low value
            store.save_signal(BrandSignalSnapshot(
                "sig-old", "2025-01-01", dimension="science_credibility", value=0.2,
            ))
            # 新信号: high value
            store.save_signal(BrandSignalSnapshot(
                "sig-new", "2025-06-01", dimension="science_credibility", value=0.8,
            ))

            engine = BrandStateEngine(store)
            state = engine.build_state_from_signals("2025-06-15")

            # 加权平均应更接近 0.8（新信号）而非 0.5（简单平均）
            assert state.perception.science_credibility > 0.5
            assert state.perception.science_credibility > 0.65, \
                f"should be closer to recent value, got {state.perception.science_credibility}"
        finally:
            _cleanup(store, path)

    def test_decay_off_uses_latest(self):
        """关闭衰减时取最新值"""
        store, path = _fresh_store()
        try:
            store.save_signal(BrandSignalSnapshot(
                "sig-old", "2025-01-01", dimension="science_credibility", value=0.2,
            ))
            store.save_signal(BrandSignalSnapshot(
                "sig-new", "2025-06-01", dimension="science_credibility", value=0.8,
            ))

            engine = BrandStateEngine(store)
            state = engine.build_state_from_signals("2025-06-15", use_decay=False)

            assert abs(state.perception.science_credibility - 0.8) < 1e-6
        finally:
            _cleanup(store, path)

    def test_multiple_dimensions_independent(self):
        """不同维度的衰减加权互相独立"""
        store, path = _fresh_store()
        try:
            # science: 旧=0.2, 新=0.8
            store.save_signal(BrandSignalSnapshot(
                "s1", "2025-01-01", dimension="science_credibility", value=0.2,
            ))
            store.save_signal(BrandSignalSnapshot(
                "s2", "2025-06-01", dimension="science_credibility", value=0.8,
            ))
            # comfort: only old signal
            store.save_signal(BrandSignalSnapshot(
                "s3", "2025-01-01", dimension="comfort_trust", value=0.6,
            ))

            engine = BrandStateEngine(store)
            state = engine.build_state_from_signals("2025-06-15")

            # comfort only has one signal, no weighting
            assert abs(state.perception.comfort_trust - 0.6) < 1e-6
            # science is weighted
            assert state.perception.science_credibility > 0.5
        finally:
            _cleanup(store, path)

    def test_evidence_shows_weighted(self):
        """多条同维度信号时 evidence 标注 (weighted)"""
        store, path = _fresh_store()
        try:
            store.save_signal(BrandSignalSnapshot(
                "s1", "2025-01-01", dimension="science_credibility", value=0.3,
            ))
            store.save_signal(BrandSignalSnapshot(
                "s2", "2025-06-01", dimension="science_credibility", value=0.7,
            ))

            engine = BrandStateEngine(store)
            state = engine.build_state_from_signals("2025-06-15")

            assert any("weighted" in e for e in state.evidence_sources)
        finally:
            _cleanup(store, path)

    def test_replay_initial_state_uses_decay(self):
        """replay 初始 state 应与 build_state_from_signals 使用同一套衰减逻辑"""
        store, path = _fresh_store()
        try:
            # 同维度两条信号：旧=0.2, 新=0.8
            store.save_signal(BrandSignalSnapshot(
                "s-old", "2025-01-01", dimension="science_credibility", value=0.2,
            ))
            store.save_signal(BrandSignalSnapshot(
                "s-new", "2025-06-01", dimension="science_credibility", value=0.8,
            ))
            # 添加一条干预让 replay 有东西可跑
            store.save_intervention(HistoricalIntervention(
                "iv1", "r1", product_line="moodyplus",
                date_start="2025-06-15", date_end="2025-06-30",
                theme="science", audience_segment="general",
            ))

            engine = BrandStateEngine(store)

            # build_state_from_signals 的结果（带衰减）
            manual = engine.build_state_from_signals("2025-06-15")

            # replay 的初始 state
            states = engine.replay_history()
            replay_initial = states[0]

            # 两者的 science_credibility 应相同（都经过衰减加权）
            assert abs(
                manual.perception.science_credibility -
                replay_initial.perception.science_credibility
            ) < 1e-6, (
                f"build={manual.perception.science_credibility} "
                f"vs replay_initial={replay_initial.perception.science_credibility}"
            )
            # 且不应等于 0.8（旧逻辑取最新值的结果）
            assert replay_initial.perception.science_credibility != 0.8
        finally:
            _cleanup(store, path)


# ------------------------------------------------------------------
# Refactored _inject_competitor_delta
# ------------------------------------------------------------------

class TestInjectCompetitorDelta:
    def test_no_events_returns_original(self):
        delta = {"science_credibility": 0.05, "competitor_pressure": 0.0}
        result = BrandStateEngine._inject_competitor_delta(
            delta, "2025-06-01", "2025-06-30", [],
        )
        assert result == delta

    def test_with_events_adds_pressure(self):
        ev = CompetitorEvent("ev1", "2025-06-15", "acuvue", impact_estimate="high")
        delta = {d: 0.0 for d in PERCEPTION_DIMENSIONS}
        result = BrandStateEngine._inject_competitor_delta(
            delta, "2025-06-01", "2025-06-30", [ev],
        )
        assert result["competitor_pressure"] > 0

    def test_clamps_result(self):
        """注入后应 clamp 到 [-0.3, 0.3]"""
        delta = {d: 0.25 for d in PERCEPTION_DIMENSIONS}
        events = [
            CompetitorEvent(f"ev{i}", "2025-06-15", "c", impact_estimate="high")
            for i in range(5)
        ]
        result = BrandStateEngine._inject_competitor_delta(
            delta, "2025-06-01", "2025-06-30", events,
        )
        assert result["competitor_pressure"] <= 0.3

    def test_replay_and_backtest_share_helper(self):
        """replay 和 backtest 都应调用 _inject_competitor_delta"""
        import inspect
        source = inspect.getsource(BrandStateEngine.replay_history)
        assert "_inject_competitor_delta" in source
        bt_source = inspect.getsource(BrandStateEngine.backtest)
        assert "_inject_competitor_delta" in bt_source


# ------------------------------------------------------------------
# Multi-step scenario simulation
# ------------------------------------------------------------------

class TestSimulateScenario:
    def test_basic_single_step(self):
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)
            result = engine.simulate_scenario(
                steps=[{"theme": "science", "budget": 50000}],
            )

            assert result["steps_count"] == 1
            assert len(result["timeline"]) == 1
            assert "initial_state" in result
            assert "final_state" in result
            assert "cumulative_delta" in result
            assert "scenario_id" in result
        finally:
            _cleanup(store, path)

    def test_multi_step_cumulates(self):
        """多步 delta 应该累积"""
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)
            result = engine.simulate_scenario(
                steps=[
                    {"theme": "science", "budget": 50000},
                    {"theme": "science", "budget": 50000},
                    {"theme": "science", "budget": 50000},
                ],
            )

            assert result["steps_count"] == 3
            assert len(result["timeline"]) == 3
            # 3 步 science 应该累积 > 1 步
            single = engine.simulate_scenario(
                steps=[{"theme": "science", "budget": 50000}],
            )
            assert result["cumulative_delta"]["science_credibility"] > \
                single["cumulative_delta"]["science_credibility"]
        finally:
            _cleanup(store, path)

    def test_mixed_themes(self):
        """不同 theme 的步骤影响不同维度"""
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)
            result = engine.simulate_scenario(
                steps=[
                    {"theme": "science", "budget": 50000},
                    {"theme": "beauty", "budget": 50000},
                ],
            )

            cd = result["cumulative_delta"]
            assert cd["science_credibility"] > 0
            assert cd["aesthetic_affinity"] > 0
        finally:
            _cleanup(store, path)

    def test_state_chains_through_steps(self):
        """每步的 base_state 是上一步的结果"""
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)
            result = engine.simulate_scenario(
                steps=[
                    {"theme": "science"},
                    {"theme": "science"},
                ],
            )

            t = result["timeline"]
            # Step 1 的状态应不同于 initial
            step0_sci = t[0]["state_after"]["perception"]["science_credibility"]
            step1_sci = t[1]["state_after"]["perception"]["science_credibility"]
            initial_sci = result["initial_state"]["perception"]["science_credibility"]

            assert step0_sci > initial_sci
            assert step1_sci > step0_sci
        finally:
            _cleanup(store, path)

    def test_custom_scenario_id(self):
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)
            result = engine.simulate_scenario(
                steps=[{"theme": "science"}],
                scenario_id="my-scenario",
            )
            assert result["scenario_id"] == "my-scenario"
        finally:
            _cleanup(store, path)

    def test_empty_steps_raises(self):
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)
            try:
                engine.simulate_scenario(steps=[])
                assert False, "should raise ValueError"
            except ValueError:
                pass
        finally:
            _cleanup(store, path)

    def test_missing_theme_raises(self):
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)
            try:
                engine.simulate_scenario(steps=[{"budget": 50000}])
                assert False, "should raise ValueError"
            except ValueError:
                pass
        finally:
            _cleanup(store, path)

    def test_with_historical_data(self):
        """有历史数据时应使用历史模式预测"""
        store, path = _fresh_store()
        try:
            store.save_intervention(HistoricalIntervention(
                "iv1", "r1", product_line="moodyplus",
                theme="science", audience_segment="general",
            ))
            store.save_outcome(HistoricalOutcomeWindow(
                "oc1", "iv1", brand_lift=0.2, comment_sentiment=0.5,
            ))

            engine = BrandStateEngine(store)
            result = engine.simulate_scenario(
                steps=[{"theme": "science"}],
            )

            assert result["timeline"][0]["reasoning"].startswith("基于")
        finally:
            _cleanup(store, path)


# ------------------------------------------------------------------
# Scenario comparison
# ------------------------------------------------------------------

class TestCompareScenarios:
    def test_basic_comparison(self):
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)
            result = engine.compare_scenarios(
                scenarios=[
                    {"name": "科普路线", "steps": [{"theme": "science"}]},
                    {"name": "颜值路线", "steps": [{"theme": "beauty"}]},
                ],
            )

            assert "current_state" in result
            assert len(result["scenarios"]) == 2
            assert "recommendation" in result

            for sc in result["scenarios"]:
                assert "name" in sc
                assert "score" in sc
                assert "rank" in sc
                assert "confidence" in sc
                assert "final_state" in sc
                assert "cumulative_delta" in sc
        finally:
            _cleanup(store, path)

    def test_ranking_order(self):
        """rank 1 的 score 应该最高"""
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)
            result = engine.compare_scenarios(
                scenarios=[
                    {"name": "A", "steps": [{"theme": "science"}]},
                    {"name": "B", "steps": [{"theme": "beauty"}]},
                ],
            )

            valid = [s for s in result["scenarios"] if "rank" in s]
            rank1 = [s for s in valid if s["rank"] == 1][0]
            rank2 = [s for s in valid if s["rank"] == 2][0]
            assert rank1["score"] >= rank2["score"]
        finally:
            _cleanup(store, path)

    def test_ranking_confidence_weighted(self):
        """
        高置信路线 vs 低置信路线：confidence 加权应翻转 raw delta 排序。
        science: 1 步, 有 5 条历史数据 → confidence=0.8, raw_delta ~0.125
        beauty_3x: 3 步无历史 → confidence=0.2, raw_delta ~0.15
        raw: beauty > science；score (raw×conf): science(0.1) > beauty(0.03)
        """
        store, path = _fresh_store()
        try:
            # 给 science 提供 5 条历史数据 → confidence = min(0.8, 0.3+0.1*5) = 0.8
            for i in range(1, 6):
                store.save_intervention(HistoricalIntervention(
                    f"iv{i}", "r1", product_line="moodyplus",
                    theme="science", audience_segment="general",
                ))
                store.save_outcome(HistoricalOutcomeWindow(
                    f"oc{i}", f"iv{i}", brand_lift=0.1, comment_sentiment=0.3,
                ))

            engine = BrandStateEngine(store)
            result = engine.compare_scenarios(
                scenarios=[
                    {"name": "science_once", "steps": [
                        {"theme": "science", "budget": 50000},
                    ]},
                    {"name": "beauty_3x", "steps": [
                        {"theme": "beauty"},
                        {"theme": "beauty"},
                        {"theme": "beauty"},
                    ]},
                ],
            )

            sci = [s for s in result["scenarios"] if s["name"] == "science_once"][0]
            beauty = [s for s in result["scenarios"] if s["name"] == "beauty_3x"][0]

            # science has 5 historical samples → much higher confidence
            assert sci["confidence"] > beauty["confidence"], \
                f"science conf={sci['confidence']} should > beauty conf={beauty['confidence']}"

            # beauty_3x has more raw cumulative delta (3 heuristic steps)
            sci_raw = sum(
                v for k, v in sci["cumulative_delta"].items()
                if v > 0 and k != "skepticism" and k != "price_sensitivity"
            )
            beauty_raw = sum(
                v for k, v in beauty["cumulative_delta"].items()
                if v > 0 and k != "skepticism" and k != "price_sensitivity"
            )
            assert beauty_raw > sci_raw, \
                f"beauty_3x raw={beauty_raw} should > science raw={sci_raw}"

            # After confidence weighting, science should win
            assert sci["score"] > beauty["score"], \
                f"science score={sci['score']} should > beauty score={beauty['score']} after confidence weighting"
            assert sci["rank"] == 1
        finally:
            _cleanup(store, path)

    def test_multi_step_scenario_comparison(self):
        """多步情景也能比较"""
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)
            result = engine.compare_scenarios(
                scenarios=[
                    {"name": "短期冲击", "steps": [
                        {"theme": "science", "budget": 200000},
                    ]},
                    {"name": "持续渗透", "steps": [
                        {"theme": "science", "budget": 50000},
                        {"theme": "science", "budget": 50000},
                        {"theme": "science", "budget": 50000},
                    ]},
                ],
            )
            assert len(result["scenarios"]) == 2
            for sc in result["scenarios"]:
                assert "score" in sc
        finally:
            _cleanup(store, path)

    def test_empty_steps_produces_error(self):
        """空 steps 的情景应返回 error 而非崩溃"""
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)
            result = engine.compare_scenarios(
                scenarios=[
                    {"name": "valid", "steps": [{"theme": "science"}]},
                    {"name": "invalid", "steps": []},
                ],
            )
            invalid = [s for s in result["scenarios"] if s["name"] == "invalid"][0]
            assert "error" in invalid
            valid = [s for s in result["scenarios"] if s["name"] == "valid"][0]
            assert "error" not in valid
        finally:
            _cleanup(store, path)

    def test_empty_scenarios_raises(self):
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)
            try:
                engine.compare_scenarios(scenarios=[])
                assert False, "should raise ValueError"
            except ValueError:
                pass
        finally:
            _cleanup(store, path)

    def test_recommendation_text(self):
        """有正向影响时推荐应包含情景名"""
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)
            result = engine.compare_scenarios(
                scenarios=[
                    {"name": "我的路线", "steps": [{"theme": "science"}]},
                ],
            )
            assert "我的路线" in result["recommendation"]
        finally:
            _cleanup(store, path)

    def test_comparison_respects_segment(self):
        """不同 segment 的比较应独立"""
        store, path = _fresh_store()
        try:
            # young_female has strong science history
            store.save_intervention(HistoricalIntervention(
                "iv-yf", "r1", product_line="moodyplus",
                theme="science", audience_segment="young_female",
            ))
            store.save_outcome(HistoricalOutcomeWindow(
                "oc-yf", "iv-yf", brand_lift=0.3,
            ))

            engine = BrandStateEngine(store)

            gen_result = engine.compare_scenarios(
                scenarios=[{"name": "sci", "steps": [{"theme": "science"}]}],
                audience_segment="general",
            )
            yf_result = engine.compare_scenarios(
                scenarios=[{"name": "sci", "steps": [{"theme": "science"}]}],
                audience_segment="young_female",
            )

            gen_sci = gen_result["scenarios"][0]
            yf_sci = yf_result["scenarios"][0]
            # young_female has historical data → should differ
            assert gen_sci["cumulative_delta"]["science_credibility"] != \
                yf_sci["cumulative_delta"]["science_credibility"]
        finally:
            _cleanup(store, path)
