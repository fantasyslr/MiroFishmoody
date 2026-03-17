---
phase: 12-iteration-analytics
plan: 01
subsystem: api, ui
tags: [versioning, iteration, campaign, compare, react, flask]

requires:
  - phase: 08-evaluate-scoring
    provides: Scoreboard model and dimension scores for campaigns
provides:
  - Campaign version linking via parent_set_id
  - Version history API endpoint
  - Version compare API endpoint with dimension deltas
  - "迭代优化" iteration button on result pages
  - CompareVersionPage with side-by-side delta view
  - Iterate state management (localStorage)
affects: [12-iteration-analytics]

tech-stack:
  added: []
  patterns: [parent chain traversal for version history, closure-wrapped save_result_fn for metadata injection]

key-files:
  created:
    - frontend/src/pages/CompareVersionPage.tsx
  modified:
    - backend/app/models/campaign.py
    - backend/app/api/campaign.py
    - frontend/src/lib/api.ts
    - frontend/src/pages/ResultPage.tsx
    - frontend/src/pages/EvaluateResultPage.tsx
    - frontend/src/App.tsx
    - frontend/src/pages/HomePage.tsx

key-decisions:
  - "Version computed by walking parent chain at evaluate time, stored in result JSON"
  - "Closure-wrapped save_result_fn to inject parent_set_id/version without modifying orchestrator"
  - "Version history built by scanning all result files and building parent->child index"

patterns-established:
  - "Iterate state: localStorage round-trip with saveIterateState/getIterateState/clearIterateState"
  - "DeltaBadge component pattern: green TrendingUp / red TrendingDown for score deltas"

requirements-completed: [ITER-01]

duration: 5min
completed: 2026-03-17
---

# Phase 12 Plan 01: Campaign Iteration & Version Compare Summary

**Campaign versioning system with parent_set_id linking, version history/compare APIs, iterate buttons on result pages, and side-by-side CompareVersionPage with dimension delta arrows**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-17T09:11:17Z
- **Completed:** 2026-03-17T09:16:06Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Backend Campaign model extended with parent_campaign_id and version fields
- Two new API endpoints: version-history (chain traversal) and compare (dimension deltas)
- "迭代优化" button on both ResultPage and EvaluateResultPage
- CompareVersionPage with side-by-side layout showing green/red delta indicators
- Iterate state flow: result page -> HomePage banner -> auto-link parent_set_id on submission

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend version model + iteration API + compare endpoint** - `15ed931` (feat)
2. **Task 2: Frontend iteration button + CompareVersionPage** - `96a93c0` (feat)

## Files Created/Modified
- `backend/app/models/campaign.py` - Added parent_campaign_id and version fields to Campaign dataclass
- `backend/app/api/campaign.py` - Version computation, parent_set_id passthrough, version-history and compare endpoints
- `frontend/src/lib/api.ts` - VersionInfo, VersionCompareResult types, API functions, iterate state helpers, parent_set_id in EvaluatePayload
- `frontend/src/pages/ResultPage.tsx` - Added "迭代优化" button with iterate state save
- `frontend/src/pages/EvaluateResultPage.tsx` - Added "迭代优化" and conditional "版本对比" buttons
- `frontend/src/pages/CompareVersionPage.tsx` - New page: side-by-side version comparison with delta badges
- `frontend/src/App.tsx` - Added /compare route
- `frontend/src/pages/HomePage.tsx` - Iterate banner, parent_set_id injection, clearIterateState on submit

## Decisions Made
- Version number computed by walking parent chain at evaluate() time rather than stored incrementally -- simpler, no state corruption risk
- Used closure-wrapped save_result_fn to inject parent_set_id/version into saved results without modifying EvaluationOrchestrator
- Version history endpoint scans all result files to build parent->child index -- acceptable for MVP scale

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Version linking infrastructure ready for analytics plan (12-02)
- CompareVersionPage can be enhanced with more visualization in future iterations

---
*Phase: 12-iteration-analytics*
*Completed: 2026-03-17*
