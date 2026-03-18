---
phase: 16-multi-agent-evaluation-enhancement
plan: "02"
subsystem: services
tags: [consensus, outlier-detection, statistics, stdev, panel-scores, evaluation]

requires:
  - phase: 15-multi-agent-foundation
    provides: PanelScore model with dimension_scores extension point; EvaluationOrchestrator pipeline structure

provides:
  - ConsensusAgent service with stdev-based outlier detection
  - suspect=True flag in PanelScore.dimension_scores for outlier persona scores
  - EvaluationOrchestrator integration — suspect flags generated automatically on every evaluate run

affects:
  - 16-03-frontend-badges (reads suspect flag from panel_scores.dimension_scores in result JSON)
  - Any phase reading evaluation result JSON panel_scores

tech-stack:
  added: []
  patterns:
    - "Local import pattern: consensus_agent imported inside run() method, consistent with MarketJudge conditional import"
    - "In-place mutation + return for chaining: detect() mutates PanelScore objects and returns same list"
    - "Per-campaign stdev grouping: outlier threshold applied independently per campaign_id, not globally"

key-files:
  created:
    - backend/app/services/consensus_agent.py
    - backend/tests/test_consensus_agent.py
  modified:
    - backend/app/services/evaluation_orchestrator.py

key-decisions:
  - "stdev_threshold=2.0 matches controversy badge threshold from CONTEXT.md — consistent scale across Phase 16"
  - "No suspect=False written for non-outliers — absence of key means clean, presence means flagged"
  - "Single-persona campaigns skip detection — stdev undefined with n<2, silent pass-through"
  - "Test data uses [8,8,8,2] not [9,8,8,2] — ensures only true statistical outlier exceeds threshold"

patterns-established:
  - "ConsensusAgent.detect() uses deviation > threshold (strictly greater) — ties at threshold are not flagged"

requirements-completed:
  - MA-07

duration: 2min
completed: 2026-03-18
---

# Phase 16 Plan 02: ConsensusAgent Summary

**ConsensusAgent using statistics.stdev flags outlier persona scores as suspect=True in panel_scores.dimension_scores, wired into EvaluationOrchestrator after AudiencePanel evaluation.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-18T05:02:00Z
- **Completed:** 2026-03-18T05:04:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- ConsensusAgent.detect() groups panel scores by campaign, computes cross-persona stdev, marks outliers with suspect=True in dimension_scores
- 5 unit tests covering: outlier flagged, tight scores not flagged, single-persona no-flag, in-place mutation, per-campaign independence
- EvaluationOrchestrator integrates ConsensusAgent after AudiencePanel.evaluate_all(), before empty-check — suspect flags automatically generated on every evaluate run

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for ConsensusAgent** - `9ae28d8` (test)
2. **Task 1 GREEN: ConsensusAgent implementation** - `20e8050` (feat)
3. **Task 2: EvaluationOrchestrator integration** - `30bc141` (feat)

_Note: TDD task has separate RED and GREEN commits._

## Files Created/Modified
- `backend/app/services/consensus_agent.py` - ConsensusAgent class with stdev outlier detection
- `backend/tests/test_consensus_agent.py` - 5 unit tests covering all detection behaviors
- `backend/app/services/evaluation_orchestrator.py` - Added ConsensusAgent call after panel evaluation

## Decisions Made
- `stdev_threshold=2.0` defaults match controversy badge threshold for consistent Phase 16 scale
- Non-outlier scores do NOT get `suspect=False` — absence means clean, simpler for frontend to handle
- Local import inside `run()` method, consistent with existing `MarketJudge` conditional import pattern

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test data so only the true statistical outlier exceeds threshold**
- **Found during:** Task 1 GREEN (first test run)
- **Issue:** Test used scores [9,8,8,2]. Mean=6.75, stdev≈3.2 — both score=9 (deviation 2.25) and score=2 (deviation 4.75) exceeded threshold=2.0. Test asserted only 1 suspect but 2 were flagged.
- **Fix:** Changed test data to [8,8,8,2]. Mean=6.5, stdev≈2.65 — deviation(8)=1.5 < 2.0, only deviation(2)=4.5 > 2.0. Same fix applied to `test_multiple_campaigns_independent`.
- **Files modified:** backend/tests/test_consensus_agent.py
- **Verification:** `uv run pytest tests/test_consensus_agent.py` — 5 passed
- **Committed in:** 20e8050 (Task 1 feat commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - test data bug)
**Impact on plan:** Implementation correct; test data needed adjustment to match mathematical reality. No scope creep.

## Issues Encountered
- Pre-existing test failures unrelated to this plan: `test_persona_registry.py` (JSON parse error), `test_smoke.py` (LLM_API_KEY not set), `scripts/test_sync_etl_enrichment.py` (pyarrow missing). All existed before this plan.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 16-03 can read `panel_scores[*].dimension_scores.suspect === true` from evaluation result JSON to render controversy badges
- EvaluationOrchestrator integration complete — suspect flags in all future evaluate runs automatically

---
*Phase: 16-multi-agent-evaluation-enhancement*
*Completed: 2026-03-18*
