---
phase: 14-frontend-rewrite-core-pages
plan: 03
subsystem: ui
tags: [react, typescript, tailwind, motion, components]

# Dependency graph
requires:
  - phase: 13-critical-bug-fixes-api-contract-lock
    provides: contracts.ts frozen, EvaluatePage polling infrastructure

provides:
  - StepIndicator: reusable horizontal step bar component (3-step, number circles + connector)
  - SplitPanel: 40/60 split layout with motion/react entrance animation
  - LogBuffer: auto-scrolling log display, max 200 lines, scroll-to-bottom on update
  - RunningPage: redesigned with SplitPanel layout + StepIndicator + LogBuffer
  - EvaluatePage: StepIndicator above EVAL_STAGES list, progress-linked (progressToStep), LogBuffer for message stream

affects: [future-running-page-polling, evaluate-page-ux, progress-visualization]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "StepIndicator: isDone/isActive derived from index vs currentStep, connector line fills on done"
    - "LogBuffer: receives messages[] from parent, parent owns polling/appending, component owns scroll"
    - "progressToStep(p): 0-39 → 0, 40-79 → 1, 80-100 → 2 maps 4 EVAL_STAGES to 3 display steps"

key-files:
  created:
    - frontend/src/components/StepIndicator.tsx
    - frontend/src/components/SplitPanel.tsx
    - frontend/src/components/LogBuffer.tsx
  modified:
    - frontend/src/pages/RunningPage.tsx
    - frontend/src/pages/EvaluatePage.tsx

key-decisions:
  - "LogBuffer is display-only — parent owns log state and appending logic, component just renders and scrolls"
  - "Race path uses fixed RACE_CURRENT_STEP=1 (synchronous, no polling) — step advances only via navigation"
  - "EvaluatePage progressToStep maps 4 EVAL_STAGES to 3 StepIndicator steps for cleaner UX"

patterns-established:
  - "Log state pattern: useState<string[]>([]) in page, passed down to LogBuffer as messages prop"
  - "Step mapping pattern: external function progressToStep() keeps component JSX clean"

requirements-completed: [FE-05, FE-07]

# Metrics
duration: 3min
completed: 2026-03-18
---

# Phase 14 Plan 03: StepIndicator / SplitPanel / LogBuffer Components Summary

**Three reusable progress-visualization components (StepIndicator, SplitPanel, LogBuffer) integrated into RunningPage and EvaluatePage for structured progress feedback during AI inference**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-18T04:17:23Z
- **Completed:** 2026-03-18T04:20:20Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Created StepIndicator with number circles, animated connector lines, isDone/isActive state
- Created SplitPanel with 40/60 layout and motion/react entrance animation on right panel
- Created LogBuffer with auto-scroll-to-bottom, configurable maxLines (default 200)
- RunningPage redesigned: spinner moved into SplitPanel left, LogBuffer in right panel, StepIndicator at top
- EvaluatePage: StepIndicator inserted above EVAL_STAGES list, synced to progress via progressToStep()
- EvaluatePage: res.message appended to logs on each poll tick, LogBuffer shown when logs.length > 0

## Task Commits

1. **Task 1: 创建 StepIndicator / SplitPanel / LogBuffer 组件** - `142f936` (feat)
2. **Task 2: RunningPage + EvaluatePage 接入新组件** - `8906b76` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `frontend/src/components/StepIndicator.tsx` - Horizontal step bar with number circles, connector lines, transitions
- `frontend/src/components/SplitPanel.tsx` - Left/right split layout with motion entrance on right panel
- `frontend/src/components/LogBuffer.tsx` - Auto-scrolling log display, parent-controlled messages array
- `frontend/src/pages/RunningPage.tsx` - Replaced spinner with SplitPanel+StepIndicator+LogBuffer layout
- `frontend/src/pages/EvaluatePage.tsx` - Added StepIndicator above stages, LogBuffer below message

## Decisions Made

- LogBuffer is a pure display component — parent (page) owns log state and appending. This keeps the component reusable without coupling it to polling logic.
- Race path uses a fixed `RACE_CURRENT_STEP = 1` constant since raceCampaigns() is synchronous — there's no polling to drive step progression.
- progressToStep() maps 4 EVAL_STAGES to 3 display steps for cleaner visual hierarchy.

## Deviations from Plan

None - plan executed exactly as written.

One pre-existing issue encountered:
- `tsc -b` incremental cache had stale errors (TS6133 on exportUtils.ts, HomePage.tsx). Resolved by deleting `tsconfig.tsbuildinfo` and running clean build. Not a deviation from plan scope.

## Issues Encountered

- tsc incremental build cache produced false TS6133 errors on pre-existing files (exportUtils.ts, HomePage.tsx). Clean build (`rm tsconfig.tsbuildinfo`) resolved. No code changes needed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 3 components are self-contained, tested via build, ready for reuse in future pages
- LogBuffer ready for 2s polling pattern (parent sets up setInterval, appends to logs state)
- StepIndicator can accept any steps[] array and currentStep index

---
*Phase: 14-frontend-rewrite-core-pages*
*Completed: 2026-03-18*
