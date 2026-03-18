---
phase: 13-critical-bug-fixes-api-contract-lock
plan: "02"
subsystem: ui
tags: [react, typescript, localStorage, race-condition, api-contract]

requires:
  - phase: 13-critical-bug-fixes-api-contract-lock/13-01
    provides: Phase 13 test infrastructure and evaluate endpoint parser fixes

provides:
  - BUG-06 fix: Both mode now awaits evaluateCampaigns before navigate('/running'), guaranteeing evaluateTaskId is in localStorage
  - BUG-07 fix: RunningPage no longer shows fake STEPS progress animation; honest Loader2 spinner while raceCampaigns() resolves
  - FE-08: frontend/src/lib/contracts.ts created as API contract lock — re-exports api.ts types + adds EvaluateSubmitResponse, ImageFileEntry, ListImagesResponse, LogoutResponse

affects:
  - Phase 14 frontend rewrite (depends on contracts.ts as stable import surface)
  - ResultPage/EvaluatePage (polling logic now receives evaluateTaskId reliably in Both mode)

tech-stack:
  added: []
  patterns:
    - "API contract lock via contracts.ts: page components import types from contracts.ts, not api.ts directly"
    - "Both mode: await evaluate POST before navigate so downstream pages have taskId in localStorage"

key-files:
  created:
    - frontend/src/lib/contracts.ts
  modified:
    - frontend/src/pages/HomePage.tsx
    - frontend/src/pages/RunningPage.tsx

key-decisions:
  - "Both mode evaluate uses try/finally so navigate('/running') fires even if evaluate POST fails — Race path remains available"
  - "RunningPage fake STEPS removed entirely; no intermediate state shown, only honest wait + spinner"
  - "contracts.ts frozen at 2026-03-18; lib/api.ts must NOT be modified — any new types go in contracts.ts"

patterns-established:
  - "contracts.ts pattern: import type from api.ts, re-export, add endpoint-literal shapes for types not yet in api.ts"

requirements-completed: [BUG-06, BUG-07, FE-08]

duration: 3min
completed: "2026-03-18"
---

# Phase 13 Plan 02: BUG-06 + BUG-07 + FE-08 Summary

**Both mode race condition fixed via await + try/finally; RunningPage fake STEPS animation removed; contracts.ts API contract lock created with 4 new endpoint types**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-18T03:57:03Z
- **Completed:** 2026-03-18T03:59:25Z
- **Tasks:** 2
- **Files modified:** 3 (2 modified, 1 created)

## Accomplishments

- BUG-06: Converted Both mode fire-and-forget to `await evaluateCampaigns` + `try/finally`, ensuring `evaluateTaskId` is written to localStorage before `navigate('/running')`
- BUG-07: Stripped all fake animation (STEPS array, currentStep state, setInterval) from RunningPage; replaced with honest Loader2 spinner
- FE-08: Created `frontend/src/lib/contracts.ts` — re-exports 9 types from api.ts, adds 4 new endpoint-literal types (EvaluateSubmitResponse, ImageFileEntry, ListImagesResponse, LogoutResponse)

## Task Commits

Each task was committed atomically:

1. **Task 1: BUG-06 await + FE-08 contracts.ts** - `37798d2` (fix + feat) — included in 13-01 commit (files were staged together)
2. **Task 2: BUG-07 RunningPage fake animation removal** - `843603c` (fix)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `frontend/src/pages/HomePage.tsx` — Both mode handler: fire-and-forget `.then()` replaced with `await` + `try/finally`
- `frontend/src/lib/contracts.ts` — New: API contract lock file, frozen 2026-03-18
- `frontend/src/pages/RunningPage.tsx` — Removed STEPS, currentStep, setInterval, CheckCircle2/Circle; added Loader2 spinner

## Decisions Made

- `navigate('/running')` moved into `finally` block so Both mode always navigates even if evaluate POST fails — Race path remains available regardless
- `setSubmitting(false)` also moved to `finally` to guarantee UI state resets before navigation
- RunningPage fake steps removed entirely with no replacement text steps — spinner + copy "推演通常需要 10-20 秒" is sufficient honest feedback
- contracts.ts uses `import type` + `export type` (type-only imports, zero runtime cost)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Task 1 files (HomePage.tsx, contracts.ts) were already committed in the 13-01 commit (37798d2) because they were staged together in the same session. Files matched the 13-02 plan spec exactly — no rework needed.
- RunningPage.tsx had a pending modification marker (M) in git status from earlier work; write required re-read before overwrite.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both mode polling (ResultPage checking evaluateTaskId) now has reliable localStorage data
- Phase 14 frontend rewrite can import API types from contracts.ts as stable surface
- api.ts is frozen — no further modifications permitted without updating contracts.ts and the corresponding Flask endpoint
