---
phase: 17-tech-debt-paydown
plan: "02"
subsystem: backend/services
tags: [characterization-tests, strangler-fig, refactoring, backtest, brand-state]
dependency_graph:
  requires: []
  provides:
    - BrandStateEngine characterization tests (TD-02 safety net)
    - BacktestEngine independent class
  affects:
    - backend/app/services/brand_state_engine.py (backtest() now delegates)
    - backend/app/services/backtest_engine.py (new file)
tech_stack:
  added: []
  patterns:
    - strangler-fig extraction via constructor injection
    - characterization tests as refactoring safety net
    - lazy import to avoid circular dependency
key_files:
  created:
    - backend/tests/test_brand_state_characterization.py
    - backend/app/services/backtest_engine.py
  modified:
    - backend/app/services/brand_state_engine.py
decisions:
  - BacktestEngine receives engine instance via __init__ to reuse compute_intervention_impact and _inject_competitor_delta without copying them
  - Lazy import (from .backtest_engine import BacktestEngine inside method body) avoids circular import
  - _themes_match helper copied into backtest_engine.py (no cross-module dependency on private helper)
metrics:
  duration: "2 min"
  completed_date: "2026-03-18"
  tasks_completed: 2
  files_changed: 3
---

# Phase 17 Plan 02: BrandStateEngine Characterization Tests + BacktestEngine Extraction Summary

**One-liner:** BrandStateEngine safety net via 7 characterization tests + backtest() extracted to BacktestEngine with strangler-fig delegation.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Write BrandStateEngine characterization tests | e25918c | backend/tests/test_brand_state_characterization.py |
| 2 | Extract BacktestEngine (strangler fig) | fd57582 | backend/app/services/backtest_engine.py, backend/app/services/brand_state_engine.py |

## What Was Built

**Task 1 — Characterization Tests**

Created `backend/tests/test_brand_state_characterization.py` with 7 tests covering all BrandStateEngine public methods:
- `test_build_state_from_signals_empty_store` — returns BrandState with PerceptionVector
- `test_compute_intervention_impact_no_outcomes` — returns delta dict keyed on PERCEPTION_DIMENSIONS
- `test_replay_history_empty_store` — returns empty list
- `test_predict_impact_returns_required_fields` — dict with current_state, delta, confidence
- `test_cognition_probability_board_empty_store` — dict with paths list
- `test_simulate_scenario_empty_steps_raises` — ValueError guard
- `test_backtest_empty_store` — total_interventions=0, tested=0

All 7 tests pass on original code and continue passing after Task 2 refactoring.

**Task 2 — BacktestEngine Extraction**

Created `backend/app/services/backtest_engine.py`:
- `BacktestEngine.__init__(store, engine)` — store for data access, engine for helper methods
- `BacktestEngine.backtest(product_line, audience_segment, market)` — full leave-one-out logic verbatim from original
- `_themes_match()` helper copied locally (no external dependency)

Modified `backend/app/services/brand_state_engine.py`:
- `BrandStateEngine.backtest()` body replaced with 3-line delegation to `BacktestEngine`
- Lazy import inside method body prevents circular import

## Test Results

```
71 passed, 10 skipped
(scripts/test_sync_etl_enrichment.py excluded — pre-existing pyarrow dependency failure)
(test_phase56.py::test_run_evaluation_fails_on_empty_pairwise — pre-existing MagicMock serialization failure, unrelated to TD-02)
```

## Deviations from Plan

### Plan Adjustments (not deviations)

**cognition_probability_board test** — Plan's template showed `engine.cognition_probability_board()` with no arguments, but the method requires `intervention_plans: List[Dict[str, Any]]`. Adjusted test to pass `[{"theme": "science"}]` and assert on `"paths"` key (returned structure). The plan's stated intent (test empty store behavior) is fully preserved.

No Rule 1/2/3/4 deviations were needed.

## Self-Check: PASSED

- [x] test_brand_state_characterization.py created at backend/tests/test_brand_state_characterization.py
- [x] backtest_engine.py created at backend/app/services/backtest_engine.py
- [x] brand_state_engine.py modified (delegation in backtest())
- [x] Commit e25918c (Task 1) verified
- [x] Commit fd57582 (Task 2) verified
