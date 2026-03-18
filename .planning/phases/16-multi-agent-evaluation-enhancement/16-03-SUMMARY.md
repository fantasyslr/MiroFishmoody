---
phase: 16-multi-agent-evaluation-enhancement
plan: "03"
subsystem: ui, evaluation
tags: [pairwise-judge, devil-advocate, controversy-badge, react, typescript, pytest, tdd]

# Dependency graph
requires:
  - phase: 16-01
    provides: MultiJudgeEnsemble, JUDGE_PERSPECTIVES, PairwiseJudge base class
  - phase: 16-02
    provides: ConsensusAgent suspect flag in dimension_scores, EvalPanelScore type

provides:
  - DEVIL_ADVOCATE_PERSPECTIVE dict with id=devil_advocate, name=品牌怀疑者
  - dissent=True flag on devil advocate votes in PairwiseResult.votes
  - isControversial() pure frontend function combining suspect + dissent signals
  - Orange rounded 争议 badge in RankingTab campaign name row
  - 可疑评分 badge in PersonaScoreCard score display

affects:
  - future pairwise judge consumers (dissent field now always present in vote dicts)
  - EvaluateResultPage rendering logic

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Devil's advocate pattern: 4th judge perspective with dissent=True flag for controversy detection"
    - "Dual-signal controversy: combine ConsensusAgent suspect + devil advocate dissent on frontend without API change"
    - "TDD flow: RED test commit → GREEN implementation commit (2 commits per task)"

key-files:
  created:
    - backend/tests/test_devil_advocate.py
  modified:
    - backend/app/services/pairwise_judge.py
    - frontend/src/pages/EvaluateResultPage.tsx

key-decisions:
  - "DEVIL_ADVOCATE_PERSPECTIVE separate from JUDGE_PERSPECTIVES list — enables clean inclusion/exclusion without modifying existing judges"
  - "dissent flag set via judge['id'] == 'devil_advocate' in judge_pair() return — single source of truth, no caller-side logic"
  - "_flip_vote() preserves dissent automatically via **vote spread — no additional code needed"
  - "MultiJudgeEnsemble._perspectives replaces hardcoded JUDGE_PERSPECTIVES reference — supports 4 judge types, 7 default slots"
  - "isControversial() is pure frontend computation — no API schema change needed"

patterns-established:
  - "Controversy badge pattern: orange rounded-full badge with bg-orange-100 text-orange-700 border-orange-300"
  - "Suspect badge pattern: smaller orange rounded-sm bg-orange-50 text-orange-600 border-orange-200"

requirements-completed:
  - MA-05
  - MA-06

# Metrics
duration: 2min
completed: 2026-03-18
---

# Phase 16 Plan 03: Devil's Advocate Judge + Controversy Badge Summary

**Devil's advocate judge (品牌怀疑者) added to MultiJudgeEnsemble with dissent=True flag; EvaluateResultPage shows orange 争议 badge combining ConsensusAgent suspect and devil advocate dissent signals**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-18T05:09:10Z
- **Completed:** 2026-03-18T05:11:30Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- DEVIL_ADVOCATE_PERSPECTIVE dict added to pairwise_judge.py (id=devil_advocate, 品牌怀疑者 with skeptical system prompt)
- judge_pair() adds dissent=True for devil advocate votes, dissent=False for all others; _flip_vote() preserves via **vote spread
- MultiJudgeEnsemble now includes devil's advocate as 4th perspective (7 judge slots by default instead of 6)
- isControversial() frontend function combines ConsensusAgent suspect flag + devil advocate dissent vote
- RankingTab shows orange rounded-full 争议 badge next to verdict badge when campaign is controversial
- PersonaScoreCard shows 可疑评分 badge next to score when dimension_scores.suspect=true

## Task Commits

1. **TDD RED: test_devil_advocate.py** - `e3ea2fd` (test)
2. **Task 1: Devil's advocate judge** - `5492eb1` (feat)
3. **Task 2: Controversy badge frontend** - `33d2b56` (feat)

## Files Created/Modified
- `backend/tests/test_devil_advocate.py` - 8 tests for devil advocate perspective, dissent flag, flip_vote preservation
- `backend/app/services/pairwise_judge.py` - Added DEVIL_ADVOCATE_PERSPECTIVE, dissent flag in judge_pair(), updated MultiJudgeEnsemble
- `frontend/src/pages/EvaluateResultPage.tsx` - Added isControversial(), 争议 badge in RankingTab, 可疑评分 badge in PersonaScoreCard

## Decisions Made
- dissent flag implemented as `judge["id"] == "devil_advocate"` in judge_pair() return — clean, no caller-side logic
- `_flip_vote()` needed no change — `**vote` spread already propagates dissent
- Frontend controversy detection is pure computation, no API schema change needed
- RankingTab signature extended with panelScores + pairwiseResults props (non-breaking: called from single site)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Fixed test mock for MultiJudgeEnsemble instantiation**
- **Found during:** Task 1 (TDD GREEN phase)
- **Issue:** Test `test_ensemble_includes_devil_advocate_perspective` called `MultiJudgeEnsemble()` without llm_client, triggering LLM_API_KEY validation error in CI environment
- **Fix:** Added `_make_ensemble()` helper in test class that passes `llm_client=MagicMock()`
- **Files modified:** backend/tests/test_devil_advocate.py
- **Verification:** All 8 tests pass
- **Committed in:** 5492eb1 (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical — test mock)
**Impact on plan:** Necessary fix for test correctness in no-LLM-key environment. No scope creep.

## Issues Encountered
- 2 pre-existing backend test failures (test_phase56.py, test_smoke.py) due to LLM_API_KEY not configured in test environment — unrelated to this plan, not introduced here

## Next Phase Readiness
- Devil's advocate dissent signal flows end-to-end: pairwise_judge → PairwiseResult.votes → frontend controversy detection
- 争议 badge visible in RankingTab whenever hasSuspect OR hasDissent is true
- ConsensusAgent suspect + devil advocate dissent signals fully wired — controversy detection complete

---
*Phase: 16-multi-agent-evaluation-enhancement*
*Completed: 2026-03-18*
