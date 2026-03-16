"""
Brandiction readiness — 回归测试

覆盖：
1. perception 信号不足时，brand-state/latest / replay / predict / probability-board 返回 _readiness + _warning
2. baseline/race 不受 readiness warning 影响
3. competitor_pressure 不足时 warning 存在但结果结构不变
"""

import sys
import os
import json
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.brandiction import (
    HistoricalIntervention,
    HistoricalOutcomeWindow,
    BrandSignalSnapshot,
    CompetitorEvent,
)
from app.models.brand_state import BrandState, PerceptionVector
from app.services.brandiction_store import BrandictionStore
from app.services.brand_state_engine import BrandStateEngine

# ------------------------------------------------------------------
# All tests in this module depend on BrandictionStore.readiness_assessment(),
# which has not been implemented yet. Skip the entire module until the
# readiness feature is built.
# ------------------------------------------------------------------
_SKIP_REASON = (
    "BrandictionStore.readiness_assessment() not yet implemented. "
    "These tests were written test-first for the readiness feature "
    "(signal coverage assessment, per-subsystem readiness grading, "
    "competitor pressure warnings). Unblock by implementing "
    "readiness_assessment() on BrandictionStore — see test expectations "
    "in this file for the expected return schema."
)
pytestmark = pytest.mark.skip(reason=_SKIP_REASON)


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


def _seed_minimal_data(store):
    """Add minimal intervention + outcome + brand_state so APIs don't 404."""
    store.save_intervention(HistoricalIntervention(
        intervention_id="iv-test-1", run_id="run-test",
        theme="science_credibility", channel_mix=["bilibili"],
        budget=50000, date_start="2025-01-01", date_end="2025-01-31",
        market="cn",
    ))
    store.save_outcome(HistoricalOutcomeWindow(
        outcome_id="oc-test-1", intervention_id="iv-test-1",
        impressions=10000, clicks=500, ctr=0.05,
    ))
    store.save_brand_state(BrandState(
        state_id="bs-test-1", as_of_date="2025-01-31",
        product_line="moodyplus", audience_segment="general",
        market="cn",
        perception=PerceptionVector(
            science_credibility=0.5, comfort_trust=0.5,
            aesthetic_affinity=0.5, price_sensitivity=0.5,
            social_proof=0.5, skepticism=0.3, competitor_pressure=0.2,
        ),
        confidence=0.4,
    ))


# ------------------------------------------------------------------
# Test: readiness_assessment with insufficient data
# ------------------------------------------------------------------

class TestReadinessAssessmentInsufficient:
    """When there are very few signals, readiness should be experimental."""

    def test_empty_db_readiness(self):
        store, path = _fresh_store()
        try:
            r = store.readiness_assessment()
            assert r["readiness"] in ("experimental", "insufficient")
            assert len(r["warnings"]) > 0
            assert r["detail"]["brand_state_latest"]["readiness"] != "production"
            assert r["detail"]["competitor_pressure"]["readiness"] != "production"
            # baseline/race is always production-ready
            assert r["detail"]["baseline_race"]["readiness"] == "production"
        finally:
            _cleanup(store, path)

    def test_sparse_signals_readiness(self):
        store, path = _fresh_store()
        try:
            # Add a few signals — still below threshold
            for i in range(3):
                store.save_signal(BrandSignalSnapshot(
                    signal_id=f"sig-{i}", date="2025-01-15",
                    product_line="moodyplus", audience_segment="general",
                    dimension="science_credibility", value=0.6,
                    market="cn",
                ))
            r = store.readiness_assessment()
            assert r["readiness"] == "experimental"
            assert r["detail"]["brand_state_latest"]["readiness"] == "experimental"
            assert r["meta"]["signals_count"] == 3
            assert r["meta"]["dimension_coverage"] == "1/7"
        finally:
            _cleanup(store, path)


# ------------------------------------------------------------------
# Test: readiness fields in API-like responses
# ------------------------------------------------------------------

class TestReadinessInAPIResponses:
    """Verify that _readiness and _warning fields are present when data is sparse."""

    def test_brand_state_latest_has_readiness(self):
        store, path = _fresh_store()
        try:
            _seed_minimal_data(store)
            state = store.get_latest_brand_state("moodyplus", "general", market="cn")
            assert state is not None
            # Simulate what the API route does
            result = state.to_dict()
            assessment = store.readiness_assessment(market="cn")
            bs_detail = assessment["detail"].get("brand_state_latest", {})
            result["_readiness"] = bs_detail.get("readiness", "experimental")
            if bs_detail.get("readiness") != "production":
                result["_warning"] = bs_detail.get("reason", "")

            assert "_readiness" in result
            assert result["_readiness"] == "experimental"
            assert "_warning" in result
            assert "signals" in result["_warning"].lower() or "insufficient" in result["_warning"].lower()
            # Original structure intact
            assert "perception" in result
            assert "state_id" in result
        finally:
            _cleanup(store, path)

    def test_predict_has_readiness(self):
        store, path = _fresh_store()
        try:
            _seed_minimal_data(store)
            engine = BrandStateEngine(store)
            plan = {"theme": "science_credibility", "channel_mix": ["bilibili"], "budget": 50000}
            pred = engine.predict_impact(
                intervention_plan=plan,
                product_line="moodyplus",
                audience_segment="general",
                market="cn",
            )
            # Simulate what the API route does
            assessment = store.readiness_assessment(market="cn")
            predict_detail = assessment["detail"].get("predict", {})
            pred["_readiness"] = predict_detail.get("readiness", "experimental")

            assert "_readiness" in pred
            assert pred["_readiness"] in ("experimental", "insufficient")
            # Original prediction structure intact
            assert "delta" in pred
            assert "confidence" in pred
        finally:
            _cleanup(store, path)


# ------------------------------------------------------------------
# Test: baseline/race not affected by readiness warnings
# ------------------------------------------------------------------

class TestBaselineRaceUnaffected:
    """baseline/race readiness is always 'production' regardless of signal scarcity."""

    def test_baseline_race_always_production(self):
        store, path = _fresh_store()
        try:
            r = store.readiness_assessment()
            assert r["detail"]["baseline_race"]["readiness"] == "production"
        finally:
            _cleanup(store, path)

    def test_baseline_race_production_with_sparse_data(self):
        store, path = _fresh_store()
        try:
            _seed_minimal_data(store)
            r = store.readiness_assessment()
            assert r["detail"]["baseline_race"]["readiness"] == "production"
            # Other subsystems are experimental but race is not
            assert r["detail"]["brand_state_latest"]["readiness"] != "production"
        finally:
            _cleanup(store, path)


# ------------------------------------------------------------------
# Test: competitor pressure warnings
# ------------------------------------------------------------------

class TestCompetitorPressureWarnings:
    """competitor_pressure should have warnings but not break result structure."""

    def test_no_competitor_events(self):
        store, path = _fresh_store()
        try:
            r = store.readiness_assessment()
            cp = r["detail"]["competitor_pressure"]
            assert cp["readiness"] == "insufficient"
            assert "reason" in cp
        finally:
            _cleanup(store, path)

    def test_with_unverified_competitor_events(self):
        store, path = _fresh_store()
        try:
            store.save_competitor_event(CompetitorEvent(
                event_id="ce-test-1", date="2025-02-01",
                competitor="ttdeye", market="global",
                event_type="campaign", impact_estimate="medium",
            ))
            r = store.readiness_assessment()
            cp = r["detail"]["competitor_pressure"]
            assert cp["readiness"] == "experimental"
            assert "no verified" in cp["reason"].lower() or "no measurable" in cp["reason"].lower()
            assert r["meta"]["competitor_events_real"] >= 1

            # Warnings list mentions competitor pressure
            cp_warnings = [w for w in r["warnings"] if "competitor" in w.lower()]
            assert len(cp_warnings) > 0
        finally:
            _cleanup(store, path)

    def test_competitor_note_in_brand_state(self):
        """API response should include _competitor_pressure_note when unverified."""
        store, path = _fresh_store()
        try:
            _seed_minimal_data(store)
            store.save_competitor_event(CompetitorEvent(
                event_id="ce-test-2", date="2025-02-01",
                competitor="eyecandys", market="cn",
                event_type="campaign", impact_estimate="medium",
            ))
            state = store.get_latest_brand_state("moodyplus", "general", market="cn")
            result = state.to_dict()
            assessment = store.readiness_assessment(market="cn")
            cp_detail = assessment["detail"].get("competitor_pressure", {})
            if cp_detail.get("readiness") != "production":
                result["_competitor_pressure_note"] = cp_detail.get("reason", "")

            assert "_competitor_pressure_note" in result
            # Original perception structure unchanged
            assert "competitor_pressure" in result["perception"]
        finally:
            _cleanup(store, path)


# ------------------------------------------------------------------
# Test: readiness endpoint data shape
# ------------------------------------------------------------------

class TestReadinessEndpointShape:
    """The readiness assessment response has the expected schema."""

    def test_response_shape(self):
        store, path = _fresh_store()
        try:
            r = store.readiness_assessment()
            assert "readiness" in r
            assert "warnings" in r
            assert "detail" in r
            assert "meta" in r
            assert isinstance(r["warnings"], list)
            assert isinstance(r["detail"], dict)
            for subsystem in ["brand_state_latest", "replay", "predict",
                              "probability_board", "competitor_pressure", "baseline_race"]:
                assert subsystem in r["detail"], f"missing {subsystem}"
                assert "readiness" in r["detail"][subsystem]
            assert "signals_count" in r["meta"]
            assert "dimension_coverage" in r["meta"]
        finally:
            _cleanup(store, path)
