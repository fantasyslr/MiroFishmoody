---
phase: 14-frontend-rewrite-core-pages
plan: "04"
subsystem: ui
tags: [html2canvas, jspdf, pdf-export, png-export, multi-page]

# Dependency graph
requires:
  - phase: 11-export-utilities
    provides: exportUtils.ts with html2canvas + jsPDF installed and initial implementation

provides:
  - Multi-page PDF export via slice-based canvas pagination (no content truncation)
  - Full-element PNG capture with windowWidth/windowHeight for large scrollable content
  - Reliable export for 5-campaign EvaluateResultPage without crashes or silent failures

affects:
  - EvaluateResultPage.tsx (uses captureElementAsPDF and captureElementAsImage)
  - ResultPage.tsx (uses captureElementAsPDF and captureElementAsImage)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Slice-based PDF pagination: render full element to canvas, then draw sub-rectangles to per-page temp canvases using drawImage with source offsets"
    - "0.5mm tolerance on remainingHeightMm to prevent blank trailing pages"
    - "windowWidth/windowHeight set to scrollWidth/scrollHeight for accurate large-element capture"

key-files:
  created: []
  modified:
    - frontend/src/lib/exportUtils.ts

key-decisions:
  - "PDF pagination via canvas slicing (drawImage with source offsets) rather than negative y-offset on a single full-height image — more compatible across jsPDF versions"
  - "0.5mm trailing-page tolerance: prevents float arithmetic from adding a near-empty last page"
  - "titleAreaHeight = 14mm reserved only on first page; subsequent pages use full otherPageContentHeight = pageHeight - margin*2"

patterns-established:
  - "Multi-page PDF: always slice canvas into per-page temp canvases; never rely on jsPDF to handle oversized images"

requirements-completed:
  - FE-04

# Metrics
duration: 3min
completed: "2026-03-18"
---

# Phase 14 Plan 04: Export Utils Fix Summary

**Slice-based multi-page PDF pagination for captureElementAsPDF — 5-campaign EvaluateResultPage exports without truncation at A4 boundary**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-18T04:17:25Z
- **Completed:** 2026-03-18T04:20:07Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Replaced single-page truncation (`Math.min(imgHeight, availableHeight)`) with a `while (remainingHeightMm > 0)` pagination loop
- Each page slice copied to a temporary canvas via `drawImage` with source Y offset, then added to PDF with `pdf.addPage()`
- Added `windowWidth: element.scrollWidth` and `windowHeight: element.scrollHeight` to both `captureElementAsImage` and `captureElementAsPDF` to ensure large scrollable elements are fully captured
- Function signatures unchanged — callers (EvaluateResultPage.tsx, ResultPage.tsx) require zero modifications
- `npm run build` passes with no TypeScript errors

## Task Commits

1. **Task 1: exportUtils.ts — 多页 PDF + 满载稳定性修复** - `0d8c8fc` (fix, included in phase 14-01 batch commit)

**Plan metadata:** (pending docs commit)

## Files Created/Modified
- `frontend/src/lib/exportUtils.ts` — Full rewrite: multi-page pagination loop, temp canvas slicing per page, windowWidth/windowHeight for both export functions

## Decisions Made
- Canvas slicing via `drawImage(canvas, 0, canvasOffsetPx, canvas.width, sliceHeightPx, 0, 0, ...)` chosen over negative-y single-image approach — more reliable across jsPDF versions and avoids vendor-specific behavior
- Unused `imgData` variable (from original template) removed as auto-fix for TS6133 error

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused `imgData` variable**
- **Found during:** Task 1 (build verification)
- **Issue:** Plan template included `const imgData = canvas.toDataURL('image/png')` but the slice-based implementation doesn't use this variable. TypeScript error TS6133 blocked build.
- **Fix:** Removed the unused `const imgData = ...` line; sliceCanvas.toDataURL() used per-page instead.
- **Files modified:** `frontend/src/lib/exportUtils.ts`
- **Verification:** `npm run build` passes (no TS errors)
- **Committed in:** 0d8c8fc (part of task commit)

---

**Total deviations:** 1 auto-fixed (1 bug — unused variable causing build failure)
**Impact on plan:** Necessary fix; plan template had a stale variable from earlier draft. No scope creep.

## Issues Encountered
- `exportUtils.ts` changes were already present in HEAD (`0d8c8fc`) when execution began — the file had been partially updated in a prior session. Verified current HEAD matches the plan specification exactly and build passes.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- PDF and PNG export are reliable for 5-campaign EvaluateResultPage content
- Both callers (EvaluateResultPage, ResultPage) unchanged — no migration needed
- Ready for Phase 14-05 and beyond

---
*Phase: 14-frontend-rewrite-core-pages*
*Completed: 2026-03-18*
