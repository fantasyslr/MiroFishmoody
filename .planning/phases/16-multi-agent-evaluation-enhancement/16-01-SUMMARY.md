---
phase: 16-multi-agent-evaluation-enhancement
plan: "01"
subsystem: evaluation
tags: [pairwise-judge, persona-registry, multi-judge, position-bias, tdd]

requires:
  - phase: 15-multi-agent-foundation
    provides: LLMSemaphore, AgentScore, audience panel infrastructure

provides:
  - moodyplus.json with 9 personas (added tech_perceiver, medical_compliance, daily_comfort_user)
  - colored_lenses.json with 8 personas (added beauty_blogger, visual_creator, subculture_fan)
  - MultiJudgeEnsemble class in pairwise_judge.py with forced position alternation
  - EvaluationOrchestrator default judge switched to MultiJudgeEnsemble

affects:
  - 16-multi-agent-evaluation-enhancement (Phase 16 plans 02+)
  - EvaluationOrchestrator consumers
  - AudiencePanel persona loading

tech-stack:
  added: []
  patterns:
    - "MultiJudgeEnsemble extends PairwiseJudge — drop-in replacement, same evaluate_all() signature"
    - "Even-index judges: (A,B) order; odd-index judges: (B,A) then _flip_vote() back to normalized labels"
    - "PairwiseResult.votes contains ALL normalized votes with 'position' field (normal/swapped)"

key-files:
  created:
    - backend/tests/test_pairwise_judge_multijudge.py
  modified:
    - backend/app/config/personas/moodyplus.json
    - backend/app/config/personas/colored_lenses.json
    - backend/app/services/pairwise_judge.py
    - backend/app/services/evaluation_orchestrator.py
    - backend/tests/test_persona_registry.py

key-decisions:
  - "MultiJudgeEnsemble is a PairwiseJudge subclass — avoids duplicating Bradley-Terry logic, evaluate_all() inherited"
  - "All normalized votes (normal + swapped-flipped) go into PairwiseResult.votes, not split into votes + swap_votes — simplifies majority counting"
  - "position_swap_consistent derived from normal vs swapped sub-majority comparison — same semantics as original PairwiseJudge"
  - "EvaluationOrchestrator default judge switched to MultiJudgeEnsemble (USE_MARKET_JUDGE flag path unchanged)"

patterns-established:
  - "TDD RED: add failing count assertions before touching JSON files"
  - "JSON persona files must use single quotes for inner quotations (double quotes break JSON parsing)"

requirements-completed: [MA-03, MA-04]

duration: 7min
completed: 2026-03-18
---

# Phase 16 Plan 01: Multi-Agent Evaluation Enhancement — Persona Expansion + MultiJudge Summary

**Persona pools expanded (moodyPlus 6→9, colored_lenses 5→8) and MultiJudgeEnsemble with forced odd/even position alternation replaces PairwiseJudge as EvaluationOrchestrator default**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-03-18T05:00:00Z
- **Completed:** 2026-03-18T05:07:06Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- moodyplus.json expanded to 9 personas: added tech_perceiver (material science), medical_compliance (compliance professional), daily_comfort_user (busy parent)
- colored_lenses.json expanded to 8 personas: added beauty_blogger (makeup artist), visual_creator (photographer), subculture_fan (subculture identity)
- MultiJudgeEnsemble: even-index judges evaluate (A,B), odd-index evaluate (B,A) then flip labels — all votes normalized into PairwiseResult.votes
- EvaluationOrchestrator default judge switched from PairwiseJudge to MultiJudgeEnsemble

## Task Commits

Each task was committed atomically:

1. **Task 1: 扩展 moodyPlus 和 colored_lenses 人格池** - `a1fc221` (feat + test update)
2. **Task 2: MultiJudge ensemble — 强制奇偶位置交替** - `eca8d8a` (feat + test)

**Plan metadata:** (pending docs commit)

_Note: TDD tasks — RED written first, GREEN implemented after confirming failure_

## Files Created/Modified

- `backend/app/config/personas/moodyplus.json` - Added 3 personas (9 total)
- `backend/app/config/personas/colored_lenses.json` - Added 3 personas (8 total)
- `backend/app/services/pairwise_judge.py` - Appended MultiJudgeEnsemble class
- `backend/app/services/evaluation_orchestrator.py` - Import + default judge switch
- `backend/tests/test_persona_registry.py` - Count assertions updated + new expanded pool test classes
- `backend/tests/test_pairwise_judge_multijudge.py` - New TDD test file (8 tests)

## Decisions Made

- MultiJudgeEnsemble is a PairwiseJudge subclass to inherit Bradley-Terry and evaluate_all() without duplication
- All normalized votes (both normal and swapped-flipped) collected in PairwiseResult.votes — the 'position' field distinguishes them; swap_votes also populated for backward compatibility
- ProductLine enum is MOODYPLUS (not CLEAR) — found during test authoring, fixed inline

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] JSON parse error due to Chinese typographic double quotes**
- **Found during:** Task 1 (moodyplus.json edit)
- **Issue:** Description text contained Chinese-style `"临床数据"` and `"医疗级"` which broke JSON parsing
- **Fix:** Replaced curly double quotes with single quotes inside description strings
- **Files modified:** backend/app/config/personas/moodyplus.json
- **Verification:** `python3 -c "import json; json.load(open(...))"` passed
- **Committed in:** a1fc221 (part of Task 1)

**2. [Rule 1 - Bug] ProductLine.CLEAR does not exist — enum is MOODYPLUS**
- **Found during:** Task 2 (test authoring)
- **Issue:** Test helper used ProductLine.CLEAR which is not a valid enum value
- **Fix:** Changed to ProductLine.MOODYPLUS
- **Files modified:** backend/tests/test_pairwise_judge_multijudge.py
- **Verification:** All 8 MultiJudge tests pass
- **Committed in:** eca8d8a (part of Task 2)

**3. [Rule 1 - Bug] Old count assertions in test_persona_registry.py would fail after JSON expansion**
- **Found during:** Task 1 (running full persona test suite after GREEN)
- **Issue:** TestCategoryLoading.test_get_personas_moodyplus asserted len==6, TestMoodyplusPreset asserted len==6, etc.
- **Fix:** Updated assertions to reflect new counts (9 and 8) and added new expected IDs
- **Files modified:** backend/tests/test_persona_registry.py
- **Verification:** All 31 persona_registry tests pass
- **Committed in:** a1fc221 (part of Task 1)

---

**Total deviations:** 3 auto-fixed (2 Rule 1 bugs, 1 Rule 1 stale test assertion)
**Impact on plan:** All fixes necessary for correctness. No scope creep.

## Issues Encountered

- `scripts/test_sync_etl_enrichment.py` fails with `ImportError: pyarrow` — pre-existing issue unrelated to this plan, excluded from test run scope

## Next Phase Readiness

- Persona pool and MultiJudgeEnsemble ready for Phase 16-02
- CrossAgentValidator and other Phase 16 agents can now reference the expanded persona pool
- Research flag from STATE.md remains: CrossAgentValidator debate-round cost needs validation against real data before production enable

---
*Phase: 16-multi-agent-evaluation-enhancement*
*Completed: 2026-03-18*
