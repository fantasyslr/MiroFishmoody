---
phase: 07-unified-entry
plan: 01
subsystem: ui
tags: [react, typescript, mode-selector, unified-entry, tailwind]

requires:
  - phase: 06-evaluate-frontend
    provides: EvaluatePage, EvaluateResultPage, evaluate API client functions
provides:
  - Mode selector cards (race/evaluate/both) on HomePage
  - Unified submit handler dispatching to correct API per mode
  - Both-mode localStorage state helpers (saveBothModeState, getBothModeState, clearBothModeState)
affects: [08-polish, running-page, result-page]

tech-stack:
  added: []
  patterns: [mode-based dispatch in submit handler, background API fire for both-mode]

key-files:
  created: []
  modified:
    - frontend/src/pages/HomePage.tsx
    - frontend/src/lib/api.ts

key-decisions:
  - "Both mode navigates to /running immediately, fires evaluate in background"
  - "Evaluate failure in both-mode is silent -- race result still accessible"

patterns-established:
  - "Mode selector pattern: SimulationMode type + MODE_OPTIONS config array + grid cards"
  - "Both-mode state: localStorage key mirofishmoody.both_mode stores evaluateTaskId/evaluateSetId for cross-page linking"

requirements-completed: [UNIF-01, UNIF-02]

duration: 3min
completed: 2026-03-17
---

# Phase 7 Plan 1: Unified Entry Summary

**Three-mode selector (race/evaluate/both) on HomePage with unified submit handler dispatching to correct API and navigation target**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-17T06:50:21Z
- **Completed:** 2026-03-17T06:53:40Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Three mode cards (race/evaluate/both) render on HomePage with visual highlight, default Race
- Unified handleSubmit replaces handleRace, dispatching based on selected mode
- Both-mode fires race + evaluate in parallel, navigates to /running, stores evaluate task ID for later access
- Build passes with zero TypeScript errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Add mode selector state and card UI to HomePage** - `574d112` (feat)
2. **Task 2: Implement unified submit handler for all three modes** - `5664c91` (feat)

## Files Created/Modified
- `frontend/src/pages/HomePage.tsx` - Added SimulationMode type, MODE_OPTIONS config, mode selector card grid, buildRacePayload/buildEvaluatePayload helpers, unified handleSubmit, dynamic button text/time
- `frontend/src/lib/api.ts` - Added saveBothModeState, getBothModeState, clearBothModeState helpers for both-mode cross-page state

## Decisions Made
- Both mode navigates to /running immediately (Race result comes first), fires evaluate in background
- Evaluate failure in both-mode is silent -- user still gets race result without error
- Mode selector uses icon per mode (Zap for race, Search for evaluate, Layers for both)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Task 1 initially included Task 2 imports (EvaluatePayload, evaluateCampaigns, saveBothModeState) causing TS errors; deferred imports to Task 2 to keep commits atomic and buildable.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Unified entry complete; RunningPage/ResultPage can read getBothModeState() to show "view evaluate result" link
- Phase 08 polish can add visual refinements to mode cards

---
*Phase: 07-unified-entry*
*Completed: 2026-03-17*

## Self-Check: PASSED
