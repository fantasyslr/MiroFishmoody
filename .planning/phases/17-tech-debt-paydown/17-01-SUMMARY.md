---
phase: 17-tech-debt-paydown
plan: 01
subsystem: api
tags: [threading, lock, tech-debt, campaign, evaluation]

# Dependency graph
requires:
  - phase: 10-concurrency
    provides: "Phase 10 decision: lock scopes minimal — only dict ops under lock, no I/O or LLM calls"
provides:
  - "TD-01 annotations on every _store_lock usage in campaign.py (7 sites)"
  - "TD-01 step annotations in EvaluationOrchestrator separating dict-write from file-I/O"
affects: [any future maintainer reading campaign.py or evaluation_orchestrator.py]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TD-01 comment convention: mark every dict-only lock scope with '# TD-01: dict-only — no I/O or LLM inside lock'"
    - "TD-01 step convention: separate dict-write (step 1, under lock) from file-I/O (step 2, outside lock) with explicit comments and blank line"

key-files:
  created: []
  modified:
    - backend/app/api/campaign.py
    - backend/app/services/evaluation_orchestrator.py

key-decisions:
  - "TD-01 annotation pattern established: comment-only enforcement, no logic change required"
  - "EvaluationOrchestrator lock/IO separation documented via step comments (step 1 = dict under lock, step 2 = file I/O outside lock)"

patterns-established:
  - "TD-01: dict-only comment above every with _store_lock: makes lock scope auditable at a glance"
  - "Step 1 / Step 2 blank-line separation in orchestrator prevents accidental I/O drift into lock scope during future maintenance"

requirements-completed: [TD-01]

# Metrics
duration: 4min
completed: 2026-03-18
---

# Phase 17 Plan 01: Lock Scope Annotation Summary

**TD-01 enforcement: 7 dict-only annotations in campaign.py + 2-step separation comments in EvaluationOrchestrator to make Phase 10 lock-scope decision auditable and maintenance-proof**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-18T05:20:00Z
- **Completed:** 2026-03-18T05:24:44Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Added 7x `# TD-01: dict-only — no I/O or LLM inside lock` comments above every `with _store_lock:` block in campaign.py
- Added `# TD-01: step 1 — dict write under lock` and `# TD-01: step 2 — file I/O outside lock` comments with blank-line separation in EvaluationOrchestrator.run()
- Phase 10 decision (lock scopes minimal, dict-only) is now visually verifiable by code review without needing to trace I/O paths manually

## Task Commits

Each task was committed atomically:

1. **Task 1: 审计并注释所有 lock 作用域** - `2ece879` (chore)
2. **Task 2: 拆分 EvaluationOrchestrator 中 dict-write 与 file-I/O** - `2c640e1` (chore)

## Files Created/Modified
- `backend/app/api/campaign.py` - 7 TD-01 dict-only annotations added above each `with _store_lock:` block
- `backend/app/services/evaluation_orchestrator.py` - step 1/step 2 annotations separating dict write from file I/O

## Decisions Made
- Comment-only approach (no logic changes) — Phase 10 implementation was already correct; annotations make intent explicit for future maintainers
- Used `# TD-01:` prefix as traceable tag tied to the requirement ID

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

3 pre-existing test failures confirmed unchanged before and after:
- `scripts/test_sync_etl_enrichment.py` — pyarrow ImportError (unrelated to this plan)
- `tests/test_phase56.py::test_run_evaluation_fails_on_empty_pairwise` — pre-existing assertion mismatch
- `tests/test_smoke.py::TestEvaluationFlow::test_submit_and_check_status` — LLM_API_KEY not set in test env

No new failures introduced.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- TD-01 requirement fully satisfied; lock scope policy is now reviewable at a glance
- Remaining tech-debt plans in Phase 17 can proceed independently

---
*Phase: 17-tech-debt-paydown*
*Completed: 2026-03-18*
