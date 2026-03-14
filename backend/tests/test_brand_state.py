"""
Brandiction PR2+PR3 — BrandState、StateTransition、BrandStateEngine、概率板测试
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.brand_state import (
    BrandState,
    PerceptionVector,
    StateTransition,
    PERCEPTION_DIMENSIONS,
)
from app.models.brandiction import (
    HistoricalIntervention,
    HistoricalOutcomeWindow,
    BrandSignalSnapshot,
)
from app.services.brandiction_store import BrandictionStore
from app.services.brand_state_engine import BrandStateEngine


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
# PerceptionVector tests
# ------------------------------------------------------------------

class TestPerceptionVector:
    def test_default_values(self):
        pv = PerceptionVector()
        assert pv.science_credibility == 0.5
        assert pv.skepticism == 0.3

    def test_from_dict_partial(self):
        pv = PerceptionVector.from_dict({"science_credibility": 0.8})
        assert pv.science_credibility == 0.8
        assert pv.comfort_trust == 0.5  # default

    def test_delta(self):
        pv1 = PerceptionVector(science_credibility=0.5)
        pv2 = PerceptionVector(science_credibility=0.7)
        d = pv1.delta(pv2)
        assert abs(d["science_credibility"] - 0.2) < 0.001

    def test_apply_delta(self):
        pv = PerceptionVector(science_credibility=0.5)
        new_pv = pv.apply_delta({"science_credibility": 0.3})
        assert new_pv.science_credibility == 0.8

    def test_apply_delta_clamps(self):
        pv = PerceptionVector(science_credibility=0.9)
        new_pv = pv.apply_delta({"science_credibility": 0.5})
        assert new_pv.science_credibility == 1.0

        pv2 = PerceptionVector(science_credibility=0.1)
        new_pv2 = pv2.apply_delta({"science_credibility": -0.5})
        assert new_pv2.science_credibility == 0.0

    def test_roundtrip(self):
        pv = PerceptionVector(science_credibility=0.8, comfort_trust=0.6)
        d = pv.to_dict()
        pv2 = PerceptionVector.from_dict(d)
        assert pv2.science_credibility == 0.8
        assert pv2.comfort_trust == 0.6


# ------------------------------------------------------------------
# BrandState model tests
# ------------------------------------------------------------------

class TestBrandStateModel:
    def test_from_dict(self):
        d = {
            "state_id": "bs1",
            "as_of_date": "2025-06-01",
            "perception": {"science_credibility": 0.8},
        }
        bs = BrandState.from_dict(d)
        assert bs.state_id == "bs1"
        assert bs.perception.science_credibility == 0.8

    def test_to_dict_includes_perception(self):
        bs = BrandState(
            state_id="bs1",
            as_of_date="2025-06-01",
            perception=PerceptionVector(science_credibility=0.8),
        )
        d = bs.to_dict()
        assert d["perception"]["science_credibility"] == 0.8

    def test_extra_fields(self):
        d = {"state_id": "bs1", "as_of_date": "2025-06-01", "custom": "value"}
        bs = BrandState.from_dict(d)
        assert bs.extra["custom"] == "value"


# ------------------------------------------------------------------
# Store: BrandState persistence
# ------------------------------------------------------------------

class TestBrandStateStore:
    def test_save_and_get(self):
        store, path = _fresh_store()
        try:
            bs = BrandState(
                state_id="bs1",
                as_of_date="2025-06-01",
                perception=PerceptionVector(science_credibility=0.8, comfort_trust=0.6),
                confidence=0.7,
                evidence_sources=["signal@2025-06-01"],
            )
            store.save_brand_state(bs)
            got = store.get_brand_state("bs1")
            assert got is not None
            assert got.perception.science_credibility == 0.8
            assert got.perception.comfort_trust == 0.6
            assert got.confidence == 0.7
            assert got.evidence_sources == ["signal@2025-06-01"]
        finally:
            _cleanup(store, path)

    def test_list_brand_states(self):
        store, path = _fresh_store()
        try:
            store.save_brand_state(BrandState("bs1", "2025-06-01"))
            store.save_brand_state(BrandState("bs2", "2025-07-01"))
            store.save_brand_state(BrandState("bs3", "2025-08-01"))

            all_states = store.list_brand_states()
            assert len(all_states) == 3

            filtered = store.list_brand_states(date_from="2025-06-15")
            assert len(filtered) == 2
        finally:
            _cleanup(store, path)

    def test_get_latest(self):
        store, path = _fresh_store()
        try:
            store.save_brand_state(BrandState("bs1", "2025-06-01"))
            store.save_brand_state(BrandState("bs2", "2025-08-01"))
            store.save_brand_state(BrandState("bs3", "2025-07-01"))

            latest = store.get_latest_brand_state()
            assert latest.state_id == "bs2"
        finally:
            _cleanup(store, path)

    def test_save_and_list_transitions(self):
        store, path = _fresh_store()
        try:
            # Create required parent rows for foreign keys
            store.save_intervention(HistoricalIntervention("iv1", "r1"))
            store.save_brand_state(BrandState("bs1", "2025-06-01"))
            store.save_brand_state(BrandState("bs2", "2025-07-01"))

            tr = StateTransition(
                transition_id="tr1",
                intervention_id="iv1",
                state_before_id="bs1",
                state_after_id="bs2",
                delta={"science_credibility": 0.1},
                method="historical",
            )
            store.save_transition(tr)
            trs = store.list_transitions("iv1")
            assert len(trs) == 1
            assert trs[0].delta["science_credibility"] == 0.1
        finally:
            _cleanup(store, path)

    def test_stats_includes_brand_states(self):
        store, path = _fresh_store()
        try:
            store.save_brand_state(BrandState("bs1", "2025-06-01"))
            s = store.stats()
            assert s["brand_states"] == 1
            assert s["state_transitions"] == 0
        finally:
            _cleanup(store, path)


# ------------------------------------------------------------------
# BrandStateEngine tests
# ------------------------------------------------------------------

class TestBrandStateEngine:
    def test_build_from_signals(self):
        store, path = _fresh_store()
        try:
            # 先插入一些 signals
            store.save_signal(BrandSignalSnapshot(
                "s1", "2025-06-01", dimension="science_credibility", value=0.8,
            ))
            store.save_signal(BrandSignalSnapshot(
                "s2", "2025-06-01", dimension="comfort_trust", value=0.7,
            ))

            engine = BrandStateEngine(store)
            state = engine.build_state_from_signals("2025-06-15")
            assert state.perception.science_credibility == 0.8
            assert state.perception.comfort_trust == 0.7
            assert state.confidence > 0.3  # 有数据时信心更高
        finally:
            _cleanup(store, path)

    def test_build_from_signals_no_data(self):
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)
            state = engine.build_state_from_signals("2025-06-15")
            # 无数据，使用默认值
            assert state.perception.science_credibility == 0.5
            assert state.confidence == 0.3
        finally:
            _cleanup(store, path)

    def test_compute_intervention_impact_science(self):
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)
            iv = HistoricalIntervention("iv1", "r1", theme="science")
            outcomes = [
                HistoricalOutcomeWindow("oc1", "iv1", brand_lift=0.15, comment_sentiment=0.6),
            ]
            delta = engine.compute_intervention_impact(iv, outcomes)
            assert delta["science_credibility"] > 0  # science theme → positive
            assert delta["social_proof"] > 0  # positive sentiment
        finally:
            _cleanup(store, path)

    def test_compute_intervention_impact_no_outcomes(self):
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)
            iv = HistoricalIntervention("iv1", "r1", theme="comfort")
            delta = engine.compute_intervention_impact(iv, [])
            # 无 outcome 只有主题基线
            assert delta["comfort_trust"] == 0.05
        finally:
            _cleanup(store, path)

    def test_replay_history(self):
        store, path = _fresh_store()
        try:
            # 插入历史数据
            store.save_intervention(HistoricalIntervention(
                "iv1", "r1", product_line="moodyplus",
                date_start="2025-06-01", date_end="2025-07-15", theme="science",
            ))
            store.save_outcome(HistoricalOutcomeWindow(
                "oc1", "iv1", brand_lift=0.1, comment_sentiment=0.5,
            ))

            store.save_intervention(HistoricalIntervention(
                "iv2", "r1", product_line="moodyplus",
                date_start="2025-08-01", date_end="2025-09-15", theme="comfort",
            ))
            store.save_outcome(HistoricalOutcomeWindow(
                "oc2", "iv2", brand_lift=0.08, comment_sentiment=0.3,
            ))

            engine = BrandStateEngine(store)
            states = engine.replay_history()
            assert len(states) == 3  # initial + 2 transitions

            # 状态应该有递进变化
            first = states[0]
            last = states[-1]
            # science 和 comfort 都应该有提升
            assert last.perception.science_credibility >= first.perception.science_credibility

            # 检查 transitions 被记录
            transitions = store.list_transitions()
            assert len(transitions) == 2
        finally:
            _cleanup(store, path)

    def test_predict_impact_no_history(self):
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)
            result = engine.predict_impact({"theme": "science_credibility"})
            assert "current_state" in result
            assert "predicted_state" in result
            assert "delta" in result
            assert result["confidence"] == 0.2  # no history
        finally:
            _cleanup(store, path)

    def test_predict_impact_with_history(self):
        store, path = _fresh_store()
        try:
            # 插入历史相似干预
            store.save_intervention(HistoricalIntervention(
                "iv1", "r1", product_line="moodyplus", theme="science",
            ))
            store.save_outcome(HistoricalOutcomeWindow(
                "oc1", "iv1", brand_lift=0.15,
            ))

            engine = BrandStateEngine(store)
            result = engine.predict_impact({"theme": "science"})
            assert result["confidence"] > 0.2
            assert result["similar_interventions"] == 1
            assert result["delta"]["science_credibility"] > 0
        finally:
            _cleanup(store, path)

    def test_cognition_probability_board(self):
        store, path = _fresh_store()
        try:
            engine = BrandStateEngine(store)
            plans = [
                {"theme": "science_credibility", "budget": 50000},
                {"theme": "comfort_beauty", "budget": 50000},
            ]
            result = engine.cognition_probability_board(plans)
            assert "current_state" in result
            assert "paths" in result
            assert len(result["paths"]) == 2
            assert "recommendation" in result

            # 每条路径应该有完整结构
            for p in result["paths"]:
                assert "predicted_delta" in p
                assert "confidence" in p
                assert "dimension_impacts" in p
        finally:
            _cleanup(store, path)

    def test_probability_board_with_history(self):
        store, path = _fresh_store()
        try:
            # 插入历史数据让推荐更有依据
            store.save_intervention(HistoricalIntervention(
                "iv1", "r1", product_line="moodyplus", theme="science",
            ))
            store.save_outcome(HistoricalOutcomeWindow(
                "oc1", "iv1", brand_lift=0.2, comment_sentiment=0.7,
            ))

            engine = BrandStateEngine(store)
            plans = [
                {"theme": "science", "budget": 50000},
                {"theme": "comfort", "budget": 50000},
            ]
            result = engine.cognition_probability_board(plans)

            # science 路径应该有更高 confidence（有历史数据）
            science_path = result["paths"][0]
            comfort_path = result["paths"][1]
            assert science_path["confidence"] > comfort_path["confidence"]
        finally:
            _cleanup(store, path)


# ------------------------------------------------------------------
# Regression: replay 幂等
# ------------------------------------------------------------------

class TestReplayIdempotent:
    def test_replay_twice_same_row_count(self):
        """连续 replay 两次，brand_states 和 state_transitions 行数不变"""
        store, path = _fresh_store()
        try:
            store.save_intervention(HistoricalIntervention(
                "iv1", "r1", product_line="moodyplus",
                date_start="2025-06-01", date_end="2025-07-15", theme="science",
            ))
            store.save_outcome(HistoricalOutcomeWindow(
                "oc1", "iv1", brand_lift=0.1,
            ))

            engine = BrandStateEngine(store)

            # 第一次 replay
            states1 = engine.replay_history()
            s1 = store.stats()

            # 第二次 replay（同一批数据）
            states2 = engine.replay_history()
            s2 = store.stats()

            assert s1["brand_states"] == s2["brand_states"], \
                f"brand_states should be idempotent: {s1['brand_states']} vs {s2['brand_states']}"
            assert s1["state_transitions"] == s2["state_transitions"], \
                f"state_transitions should be idempotent: {s1['state_transitions']} vs {s2['state_transitions']}"

            # 最终状态的 perception 应该一致
            assert states1[-1].perception.to_dict() == states2[-1].perception.to_dict()
        finally:
            _cleanup(store, path)


# ------------------------------------------------------------------
# Regression: empty theme 不应匹配所有历史
# ------------------------------------------------------------------

class TestEmptyTheme:
    def test_find_similar_empty_theme_returns_nothing(self):
        """空 theme 不应匹配任何历史干预"""
        store, path = _fresh_store()
        try:
            store.save_intervention(HistoricalIntervention(
                "iv1", "r1", product_line="moodyplus", theme="science",
            ))
            engine = BrandStateEngine(store)
            matches = engine._find_similar_interventions("", "moodyplus")
            assert matches == []
            matches2 = engine._find_similar_interventions("  ", "moodyplus")
            assert matches2 == []
        finally:
            _cleanup(store, path)

    def test_predict_impact_empty_theme_raises(self):
        """predict_impact({}) 应该抛 ValueError，不应返回假预测"""
        store, path = _fresh_store()
        try:
            store.save_intervention(HistoricalIntervention(
                "iv1", "r1", product_line="moodyplus", theme="science",
            ))
            store.save_outcome(HistoricalOutcomeWindow("oc1", "iv1", brand_lift=0.15))
            engine = BrandStateEngine(store)
            import pytest
            with pytest.raises(ValueError, match="theme"):
                engine.predict_impact({})
            with pytest.raises(ValueError, match="theme"):
                engine.predict_impact({"theme": ""})
            with pytest.raises(ValueError, match="theme"):
                engine.predict_impact({"theme": "   "})
        finally:
            _cleanup(store, path)

    def test_short_theme_does_not_match_long(self):
        """单字符 theme 不应匹配 'science' 等长 theme"""
        store, path = _fresh_store()
        try:
            store.save_intervention(HistoricalIntervention(
                "iv1", "r1", product_line="moodyplus", theme="science",
            ))
            engine = BrandStateEngine(store)
            matches = engine._find_similar_interventions("s", "moodyplus")
            assert matches == [], "single char should not match 'science'"
            matches2 = engine._find_similar_interventions("sc", "moodyplus")
            assert matches2 == [], "two chars should not match 'science'"
        finally:
            _cleanup(store, path)


# ------------------------------------------------------------------
# Regression: audience_segment 隔离
# ------------------------------------------------------------------

class TestAudienceSegment:
    def test_get_latest_respects_segment(self):
        """不同 segment 的 state 互不干扰"""
        store, path = _fresh_store()
        try:
            store.save_brand_state(BrandState(
                "bs-gen", "2025-06-01", audience_segment="general",
                perception=PerceptionVector(science_credibility=0.8),
            ))
            store.save_brand_state(BrandState(
                "bs-young", "2025-06-01", audience_segment="young_female",
                perception=PerceptionVector(science_credibility=0.3),
            ))

            gen = store.get_latest_brand_state("moodyplus", "general")
            young = store.get_latest_brand_state("moodyplus", "young_female")
            assert gen.state_id == "bs-gen"
            assert young.state_id == "bs-young"
            assert gen.perception.science_credibility == 0.8
            assert young.perception.science_credibility == 0.3
        finally:
            _cleanup(store, path)

    def test_get_latest_tie_breaker_is_stable(self):
        """同日同 segment 多条 state，结果应稳定（按 state_id DESC）"""
        store, path = _fresh_store()
        try:
            store.save_brand_state(BrandState("bs-aaa", "2025-06-01"))
            store.save_brand_state(BrandState("bs-zzz", "2025-06-01"))
            latest = store.get_latest_brand_state()
            assert latest.state_id == "bs-zzz"  # DESC → zzz > aaa
        finally:
            _cleanup(store, path)

    def test_predict_does_not_mix_segment_history(self):
        """不同 segment 的历史样本不应混用"""
        store, path = _fresh_store()
        try:
            # general: 弱 science 历史
            store.save_intervention(HistoricalIntervention(
                "iv-gen", "r1", product_line="moodyplus", theme="science",
                audience_segment="general",
            ))
            store.save_outcome(HistoricalOutcomeWindow(
                "oc-gen", "iv-gen", brand_lift=0.02,
            ))
            # young_female: 强 science 历史
            store.save_intervention(HistoricalIntervention(
                "iv-yf", "r1", product_line="moodyplus", theme="science",
                audience_segment="young_female",
            ))
            store.save_outcome(HistoricalOutcomeWindow(
                "oc-yf", "iv-yf", brand_lift=0.30,
            ))

            engine = BrandStateEngine(store)

            gen_result = engine.predict_impact(
                {"theme": "science"}, audience_segment="general",
            )
            yf_result = engine.predict_impact(
                {"theme": "science"}, audience_segment="young_female",
            )

            assert gen_result["similar_interventions"] == 1, \
                "general should only see 1 historical sample"
            assert yf_result["similar_interventions"] == 1, \
                "young_female should only see 1 historical sample"
            assert gen_result["delta"]["science_credibility"] != \
                yf_result["delta"]["science_credibility"], \
                "different segments should produce different deltas"
        finally:
            _cleanup(store, path)
