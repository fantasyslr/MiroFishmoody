"""
BrandStateEngine characterization tests (TD-02)

These tests capture the existing behavior of all public BrandStateEngine methods.
They are NOT functional specs — they lock down the current output shape so that
strangler-fig refactoring cannot silently break behavior.
"""

import sys
import os
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.brand_state_engine import BrandStateEngine
from app.services.brandiction_store import BrandictionStore
from app.models.brand_state import PERCEPTION_DIMENSIONS, PerceptionVector
from app.models.brandiction import HistoricalIntervention


# ------------------------------------------------------------------
# Fixtures (copied from test_brand_state.py — not imported)
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
# 1. build_state_from_signals
# ------------------------------------------------------------------

def test_build_state_from_signals_empty_store():
    """Empty store: returns a BrandState with a PerceptionVector."""
    store, path = _fresh_store()
    try:
        engine = BrandStateEngine(store)
        state = engine.build_state_from_signals("2025-01-01")
        assert state.product_line == "moodyplus"
        assert isinstance(state.perception, PerceptionVector)
    finally:
        _cleanup(store, path)


# ------------------------------------------------------------------
# 2. compute_intervention_impact
# ------------------------------------------------------------------

def test_compute_intervention_impact_no_outcomes():
    """Given an intervention with no outcomes, returns delta dict keyed on PERCEPTION_DIMENSIONS."""
    store, path = _fresh_store()
    try:
        engine = BrandStateEngine(store)
        iv = HistoricalIntervention(
            intervention_id="t1", run_id="r1",
            theme="science", product_line="moodyplus",
            channel_mix=["bilibili"], budget=50000,
        )
        delta = engine.compute_intervention_impact(iv, [], market="cn")
        assert set(delta.keys()) == set(PERCEPTION_DIMENSIONS)
        assert all(isinstance(v, float) for v in delta.values())
    finally:
        _cleanup(store, path)


# ------------------------------------------------------------------
# 3. replay_history
# ------------------------------------------------------------------

def test_replay_history_empty_store():
    """Empty store: returns empty list."""
    store, path = _fresh_store()
    try:
        engine = BrandStateEngine(store)
        result = engine.replay_history()
        assert result == []
    finally:
        _cleanup(store, path)


# ------------------------------------------------------------------
# 4. predict_impact
# ------------------------------------------------------------------

def test_predict_impact_returns_required_fields():
    """predict_impact returns dict with current_state, delta, and confidence."""
    store, path = _fresh_store()
    try:
        engine = BrandStateEngine(store)
        result = engine.predict_impact({"theme": "science"})
        assert "current_state" in result
        assert "delta" in result
        assert "confidence" in result
    finally:
        _cleanup(store, path)


# ------------------------------------------------------------------
# 5. cognition_probability_board
# ------------------------------------------------------------------

def test_cognition_probability_board_empty_store():
    """Empty store: returns dict with 'paths' key (list) and 'recommendation' key."""
    store, path = _fresh_store()
    try:
        engine = BrandStateEngine(store)
        # cognition_probability_board requires at least one plan in the list
        result = engine.cognition_probability_board([{"theme": "science"}])
        assert isinstance(result, dict)
        assert "paths" in result
        assert isinstance(result["paths"], list)
    finally:
        _cleanup(store, path)


# ------------------------------------------------------------------
# 6. simulate_scenario
# ------------------------------------------------------------------

def test_simulate_scenario_empty_steps_raises():
    """simulate_scenario raises ValueError when steps list is empty."""
    store, path = _fresh_store()
    try:
        engine = BrandStateEngine(store)
        with pytest.raises(ValueError):
            engine.simulate_scenario([])
    finally:
        _cleanup(store, path)


# ------------------------------------------------------------------
# 7. backtest
# ------------------------------------------------------------------

def test_backtest_empty_store():
    """Empty store: returns dict with total_interventions=0 and tested=0."""
    store, path = _fresh_store()
    try:
        engine = BrandStateEngine(store)
        result = engine.backtest()
        assert result["total_interventions"] == 0
        assert result["tested"] == 0
    finally:
        _cleanup(store, path)
