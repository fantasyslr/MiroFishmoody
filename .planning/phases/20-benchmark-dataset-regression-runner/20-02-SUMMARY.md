---
phase: 20-benchmark-dataset-regression-runner
plan: "02"
subsystem: testing

tags: [benchmark, mock, regression-runner, pytest, llm-mock, brief_type]

requires:
  - phase: 20-01
    provides: 11 benchmark fixture JSON files at backend/tests/fixtures/benchmark/*.json

provides:
  - backend/benchmark/mock_llm_client.py: deterministic MockLLMClient (duck-type LLMClient)
  - backend/benchmark/run.py: CLI benchmark runner with accuracy report
  - backend/tests/test_benchmark_runner.py: 9 pytest tests covering mock, accuracy, fixtures

affects:
  - future weight tuning: run `cd backend && uv run python benchmark/run.py` after any brief_weights.py change

tech-stack:
  added: []
  patterns:
    - "MockLLMClient dispatch: keyword matching on last message text, priority: summary > panel > pairwise > fallback"
    - "LLMClient patch target: app.services.evaluation_orchestrator.LLMClient (import-site patching)"
    - "_InMemoryTaskManager: minimal TaskManager duck-type, no SQLite, no side effects"
    - "Benchmark result retrieval: evaluation_store[set_id] (orchestrator has no return value)"

key-files:
  created:
    - backend/benchmark/mock_llm_client.py
    - backend/benchmark/run.py
    - backend/tests/test_benchmark_runner.py
  modified: []

key-decisions:
  - "patch target is app.services.evaluation_orchestrator.LLMClient (not app.utils.llm_client.LLMClient) — patch the name in the module that uses it"
  - "MockLLMClient dispatch priority: summary (confidence_notes keyword) > panel (dimension_scores) > pairwise (reach_potential) — SummaryGenerator prompt includes pairwise output so pairwise check must be lower priority"
  - "EvaluationOrchestrator.run() has no return value — results read from evaluation_store[set_id] dict after run() completes"
  - "_InMemoryTaskManager needed because TaskManager is a SQLite-backed singleton that requires MOODY_UPLOAD_FOLDER and initializes DB on import"

patterns-established:
  - "Benchmark runner pattern: patch LLMClient at import site, pass no-op save_result_fn, read results from evaluation_store dict"
  - "Mock dispatch uses keyword priority to handle prompts that contain multiple signal words (SummaryGenerator embeds pairwise output)"

requirements-completed: [BENCH-03]

duration: 8min
completed: 2026-03-18
---

# Phase 20 Plan 02: Mock LLMClient + Benchmark Regression Runner Summary

**Deterministic MockLLMClient + CLI runner that replays all 11 benchmark fixtures without API keys, outputting per-brief_type accuracy; initial baseline: brand=0.75, seeding=0.75, conversion=1.00, overall=0.82**

## Performance

- **Duration:** ~8 min
- **Completed:** 2026-03-18
- **Tasks:** 2
- **Files created:** 3

## Run Commands

```bash
# Run benchmark (from backend/ dir)
cd backend && uv run python benchmark/run.py

# Run with explicit LLM_API_KEY unset (confirms no real API calls)
cd backend && LLM_API_KEY="" uv run python benchmark/run.py

# Run pytest
cd backend && uv run pytest tests/test_benchmark_runner.py -v
```

## Initial Benchmark Results

```
=== Benchmark Regression Report ===
brand       3/4  accuracy=0.75
seeding     3/4  accuracy=0.75
conversion  3/3  accuracy=1.00
---
overall     9/11  accuracy=0.82
```

## Mock Injection Point

`app.services.evaluation_orchestrator.LLMClient` (import-site patching via `unittest.mock.patch`)

## Architecture Notes

- `EvaluationOrchestrator.run()` has **no return value** — results are stored in `evaluation_store[set_id]`; runner reads from there after each call
- `_InMemoryTaskManager` bypasses the SQLite-backed singleton `TaskManager`; implements `create_task / update_task / get_task / complete_task / fail_task`
- `MockLLMClient` also implements `chat_multimodal_json` (forwards to same dispatch) in case campaigns have `image_paths` set

## MockLLMClient Dispatch Logic

| Priority | Trigger keywords | Response type |
|----------|-----------------|---------------|
| 1 | `confidence_notes`, `营销策略顾问` | SummaryGenerator |
| 2 | `dimension_scores`, `thumb_stop`, `claim_risk` | AudiencePanel |
| 3 | `reach_potential`, `conversion_potential`, `brand_alignment` | PairwiseJudge |
| 4 | (fallback) | generic dict |

PairwiseJudge mock always returns `winner="A"` (first campaign in the pair wins — deterministic rule).

## Known Limitations

- Mock PairwiseJudge always picks campaign_a (first arg to `evaluate_pair`). Fixtures whose expected winner is `campaign_b` will always miss → brand and seeding each have 1 miss (accuracy=0.75)
- `JudgeCalibration.save_predictions()` writes to `uploads/calibration/` on each benchmark run (side effect, not harmful but creates files)
- Summary generator sees 2 WARNING attempts per fixture if summary keyword detection fails (fixed in this plan by priority reorder)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] MockLLMClient summary dispatch shadowed by pairwise keywords**
- **Found during:** Task 2 first run (22 WARNING lines for 11 fixtures)
- **Issue:** SummaryGenerator prompt contains pairwise output text (e.g., "胜者", "方案 A vs 方案 B"), causing `is_pairwise` to fire before `is_summary`, returning pairwise JSON with `summary=0 chars`
- **Fix:** Reordered dispatch: `confidence_notes` keyword check for summary runs first; pairwise moves to lowest priority
- **Files modified:** `backend/benchmark/mock_llm_client.py`
- **Commit:** `5d0cd0e`

**2. [Rule 2 - Missing] MockLLMClient summary text too short for quality gate**
- **Found during:** Task 2 (SummaryGenerator requires `len(summary) >= 20`)
- **Fix:** Extended `_summary_response()` summary to 40+ chars
- **Files modified:** `backend/benchmark/mock_llm_client.py`
- **Commit:** `5d0cd0e`

**3. [Rule 3 - Blocking] patch path `backend.app.services.evaluation_orchestrator.LLMClient` fails**
- **Found during:** Task 2 first run
- **Issue:** When running from `backend/` dir, module path is `app.services...` not `backend.app.services...`
- **Fix:** Changed patch target to `app.services.evaluation_orchestrator.LLMClient`
- **Commit:** `5d0cd0e`

## Task Commits

1. **Task 1: MockLLMClient** — `ead1276`
2. **Task 2: run.py + pytest** — `5d0cd0e`

## Self-Check

See below.
