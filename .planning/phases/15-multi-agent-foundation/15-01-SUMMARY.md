---
phase: 15-multi-agent-foundation
plan: "01"
subsystem: api
tags: [llm, concurrency, semaphore, threading, rate-limiting]

# Dependency graph
requires: []
provides:
  - "Global LLM concurrency cap via LLMClient._semaphore (all agents auto-limited)"
  - "Config.MAX_LLM_CONCURRENT — env-overridable, default 5"
  - "ImageAnalyzer cleaned of redundant local semaphore"
affects:
  - 15-multi-agent-foundation
  - 16-agent-expansion

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "LLMClient as concurrency bottleneck: all services that instantiate LLMClient automatically inherit the global semaphore — no per-service implementation required"

key-files:
  created: []
  modified:
    - backend/app/config.py
    - backend/app/utils/llm_client.py
    - backend/app/services/image_analyzer.py
    - backend/tests/test_image_analyzer_concurrent.py

key-decisions:
  - "Global LLMSemaphore at LLMClient level (not per-service) — every agent type inherits limit without code duplication"
  - "chat() and chat_multimodal() each acquire/release independently; chat_json/chat_multimodal_json delegate through them and do not add a second acquire"
  - "MAX_LLM_CONCURRENT default 5 — conservative starting point pending Bailian RPM/TPM tier verification (see Blockers)"

patterns-established:
  - "Semaphore acquire in base client, not in service layer: adding a new agent type = instantiate LLMClient, done"

requirements-completed:
  - MA-01

# Metrics
duration: 8min
completed: 2026-03-18
---

# Phase 15 Plan 01: LLM Global Concurrency Control Summary

**Global LLM concurrency cap via `threading.Semaphore(Config.MAX_LLM_CONCURRENT)` inside `LLMClient`, replacing per-service semaphore in `ImageAnalyzer`**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-18T04:30:00Z
- **Completed:** 2026-03-18T04:38:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `Config.MAX_LLM_CONCURRENT` (default 5, env-overridable) added to `backend/app/config.py`
- `LLMClient.__init__` now creates `self._semaphore = threading.Semaphore(Config.MAX_LLM_CONCURRENT)`
- `chat()` and `chat_multimodal()` both wrap the `create()` call in `acquire/try/finally/release`
- `ImageAnalyzer` local semaphore, `_safe_analyze_single()` method, and `threading` import fully removed; `analyze_plan_images()` calls `analyze_single_image` directly via `executor.submit`
- Test updated to assert the new architecture (ImageAnalyzer has no `_semaphore`)

## Task Commits

1. **Task 1: config.py 添加 MAX_LLM_CONCURRENT** - `1e8995a` (feat)
2. **Task 2: LLMClient semaphore + ImageAnalyzer cleanup** - `45820e7` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `backend/app/config.py` — Added `MAX_LLM_CONCURRENT = int(os.environ.get('MAX_LLM_CONCURRENT', '5'))`
- `backend/app/utils/llm_client.py` — Added `import threading`, `self._semaphore` in `__init__`, acquire/release in `chat()` and `chat_multimodal()`
- `backend/app/services/image_analyzer.py` — Removed `import threading`, `self._semaphore`, and `_safe_analyze_single()`; `executor.submit` now calls `analyze_single_image` directly
- `backend/tests/test_image_analyzer_concurrent.py` — Updated `test_has_semaphore` to `test_semaphore_in_llm_client_not_image_analyzer`, asserting `ImageAnalyzer` no longer owns `_semaphore`

## Decisions Made
- Semaphore lives in `LLMClient`, not in each service. Any future agent (AudiencePanel, PairwiseJudge, SummaryGenerator) gets concurrency control for free by instantiating `LLMClient`.
- `chat_json` and `chat_multimodal_json` delegate to `chat`/`chat_multimodal` respectively, so they do not acquire a second slot — no deadlock risk.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test asserting old ImageAnalyzer semaphore behavior**
- **Found during:** Task 2 (LLMClient semaphore + ImageAnalyzer cleanup)
- **Issue:** `test_has_semaphore` asserted `hasattr(analyzer, "_semaphore")` — would permanently fail after the architectural change
- **Fix:** Renamed test to `test_semaphore_in_llm_client_not_image_analyzer`; assertion now confirms `ImageAnalyzer` does NOT have `_semaphore`
- **Files modified:** `backend/tests/test_image_analyzer_concurrent.py`
- **Verification:** 590 tests pass after fix
- **Committed in:** `45820e7` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — test updated to reflect new architecture)
**Impact on plan:** Necessary correctness fix; no scope creep.

## Issues Encountered
- Two pre-existing test failures confirmed unrelated to this plan's changes:
  - `tests/test_smoke.py` — `LLM_API_KEY 未配置` (no env in test environment)
  - `tests/test_campaign_scorer_agent_scores.py` — Phase 15-02 TDD RED test (not yet implemented)

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- `LLMClient._semaphore` is live; all existing and future services using `LLMClient` are automatically rate-limited
- `MAX_LLM_CONCURRENT=5` is conservative — adjust upward after verifying Bailian account RPM/TPM tier (see Blockers in STATE.md)
- Phase 16 agents can instantiate `LLMClient` without implementing their own semaphore

---
*Phase: 15-multi-agent-foundation*
*Completed: 2026-03-18*

## Self-Check: PASSED
