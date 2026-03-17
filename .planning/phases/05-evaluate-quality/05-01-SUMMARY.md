---
phase: 05-evaluate-quality
plan: 01
subsystem: evaluation
tags: [pairwise-judge, position-bias, debiasing, image-analyzer, structured-diagnostics, llm-prompt]

# Dependency graph
requires:
  - phase: 04-concurrent-image
    provides: "Concurrent ImageAnalyzer with Semaphore-bounded LLM calls"
  - phase: 01-fix-image-pipeline
    provides: "Shared image_helpers for path resolution and base64 encoding"
provides:
  - "PairwiseJudge position-swap debiasing with consistency flag"
  - "ImageAnalyzer structured diagnostics (issues[] + recommendations[])"
  - "PairwiseResult model with position_swap_consistent and swap_votes fields"
affects: [08-frontend-dashboard, evaluation-orchestrator]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Position-swap debiasing: evaluate each pair in both A-B and B-A order, flip labels, compare majority"
    - "Structured LLM diagnostics: prompt requests typed issues/recommendations with category/severity/priority"

key-files:
  created:
    - backend/tests/test_pairwise_debiasing.py
    - backend/tests/test_structured_diagnostics.py
  modified:
    - backend/app/services/pairwise_judge.py
    - backend/app/models/evaluation.py
    - backend/app/services/image_analyzer.py

key-decisions:
  - "Winner determined from normal-order round only; swap round is for detection, not correction"
  - "Diagnostics field is additive -- visual_risks/hooks remain for compute_visual_score backward compat"
  - "Aggregation prompt caps diagnostics at 8 issues + 8 recommendations"

patterns-established:
  - "Position-swap debiasing: _flip_vote static method reverses A/B labels for swapped-order results"
  - "Structured diagnostics: issues have category/severity/description, recommendations have category/action/priority"

requirements-completed: [QUAL-01, QUAL-02]

# Metrics
duration: 3min
completed: 2026-03-17
---

# Phase 5 Plan 1: Evaluate Quality Summary

**PairwiseJudge position-swap debiasing to detect order bias + ImageAnalyzer structured diagnostics with issues[]/recommendations[] for frontend consumption**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-17T05:38:44Z
- **Completed:** 2026-03-17T05:41:50Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- PairwiseJudge evaluates each pair in both A-vs-B and B-vs-A order, flagging position bias via position_swap_consistent field
- ImageAnalyzer prompts now request structured diagnostics with typed issues (category/severity/description) and recommendations (category/action/priority)
- All 595 existing tests pass with zero regressions; 10 new tests added

## Task Commits

Each task was committed atomically:

1. **Task 1: PairwiseJudge position-swap debiasing** - `91796fe` (test) + `51d1d8e` (feat)
2. **Task 2: ImageAnalyzer structured diagnostics** - `7a18eef` (test) + `fa1cb03` (feat)

_TDD: each task has separate test and implementation commits._

## Files Created/Modified
- `backend/app/models/evaluation.py` - Added position_swap_consistent and swap_votes to PairwiseResult; updated to_dict() serialization
- `backend/app/services/pairwise_judge.py` - Added _flip_vote() and dual-round evaluate_pair() with swap detection
- `backend/app/services/image_analyzer.py` - Added diagnostics field to ANALYSIS_SYSTEM_PROMPT and aggregation rule to AGGREGATION_SYSTEM_PROMPT
- `backend/tests/test_pairwise_debiasing.py` - 5 tests for swap logic, consistency flag, return type
- `backend/tests/test_structured_diagnostics.py` - 5 tests for diagnostics structure and backward compat

## Decisions Made
- Winner determined from normal-order round only -- swap round detects bias but does not change outcome (conservative approach, avoids double-counting)
- Diagnostics field is purely additive -- existing visual_risks/hooks fields remain untouched for compute_visual_score backward compatibility
- Aggregation prompt limits diagnostics to 8 issues + 8 recommendations to prevent LLM output bloat

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Evaluation pipeline now produces position bias signals and structured diagnostics
- Phase 8 frontend dashboard can consume diagnostics.issues[] and diagnostics.recommendations[] directly
- position_swap_consistent field enables UI to flag unreliable pairwise results

---
*Phase: 05-evaluate-quality*
*Completed: 2026-03-17*
