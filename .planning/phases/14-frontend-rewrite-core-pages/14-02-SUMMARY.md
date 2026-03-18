---
phase: 14-frontend-rewrite-core-pages
plan: 02
subsystem: ui
tags: [react, typescript, evaluate, race, both-mode, winner-hero, conflict-badge]

# Dependency graph
requires:
  - phase: 13-critical-bug-fixes-api-contract-lock
    provides: contracts.ts frozen, Both mode evaluate navigation working
provides:
  - Winner Hero Card above tab navigation in EvaluateResultPage (data-testid=winner-hero)
  - Cross-path conflict amber badge in EvaluateResultPage
  - Cross-path conflict amber badge in ResultPage (Both mode + evalStatus=completed guard)
affects: [15-llm-semaphore, ResultPage, EvaluateResultPage]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "IIFE pattern (() => { ... })() for conditional inline JSX blocks"
    - "Defensive try/catch around cross-state reads to prevent page-level errors"
    - "evalStatus guard before showing cross-path data (prevents premature diff display)"

key-files:
  created: []
  modified:
    - frontend/src/pages/EvaluateResultPage.tsx
    - frontend/src/pages/ResultPage.tsx

key-decisions:
  - "Cross-path conflict badge placed before Winner Hero Card in EvaluateResultPage so both are above tab nav and visible on first render"
  - "ResultPage conflict badge gated on bothMode AND evalStatus === 'completed' to avoid showing stale/incomplete evaluate state"
  - "Both badges use defensive try/catch so any cross-state read failure silently returns null instead of crashing the page"

patterns-established:
  - "Winner Hero Card: rankings[0] after sort by rank asc — index 0 is always champion"
  - "Cross-state reads (getRaceState inside EvaluateResultPage, getEvaluateState inside ResultPage) are always wrapped in try/catch"

requirements-completed:
  - FE-02
  - FE-06

# Metrics
duration: 5min
completed: 2026-03-18
---

# Phase 14 Plan 02: EvaluateResultPage Winner Hero + Cross-Path Conflict Badges Summary

**Winner Hero Card above tab nav in EvaluateResultPage shows champion name/composite_score/verdict on first render; amber conflict banner appears on both result pages when Race and Evaluate winners differ in Both mode.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-18T04:10:00Z
- **Completed:** 2026-03-18T04:15:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- EvaluateResultPage now surfaces champion name, composite score, verdict badge, panel avg, and pairwise W/L record as a persistent hero card above the tab nav — no tab switch required
- Cross-path conflict amber banner shows in EvaluateResultPage whenever Race state has a different winner than Evaluate state
- Cross-path conflict amber banner shows in ResultPage when Both mode is active, evaluate is completed, and the two winners differ — gated to prevent premature display
- `getRaceState` added to EvaluateResultPage imports; `getEvaluateState` was already present in ResultPage

## Task Commits

1. **Task 1: EvaluateResultPage — Winner Hero Card** - `142f936` (feat)
2. **Task 2: ResultPage — Cross-path conflict badge** - `4b0e8cf` (feat)

## Files Created/Modified
- `frontend/src/pages/EvaluateResultPage.tsx` - Added `getRaceState` import, cross-path conflict badge, winner hero card (both inserted between `<div ref={exportRef}>` and tab navigation)
- `frontend/src/pages/ResultPage.tsx` - Added cross-path conflict badge after Recommendation block in header section

## Decisions Made
- Winner Hero Card uses IIFE pattern consistent with existing inline conditional patterns in the file
- Both conflict badges use `try/catch` to ensure cross-state reads never crash the page (race state may be cleared when user is on evaluate page and vice versa)
- ResultPage badge requires `evalStatus === 'completed'` guard so the banner only appears once evaluate result is fully available, not while polling

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
Pre-existing `noUnusedLocals` TS error in `exportUtils.ts` (line 51, `imgData` variable) appeared in initial build output but resolved automatically — it was a false positive from cached tsbuildinfo. Final build passed cleanly with no errors.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Both result pages now have winner-first layout and cross-path conflict visibility
- Ready for Phase 14-03 or subsequent frontend rewrite plans
- No blockers

---
*Phase: 14-frontend-rewrite-core-pages*
*Completed: 2026-03-18*
