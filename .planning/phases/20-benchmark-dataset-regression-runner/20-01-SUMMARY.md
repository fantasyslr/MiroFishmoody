---
phase: 20-benchmark-dataset-regression-runner
plan: "01"
subsystem: testing

tags: [benchmark, fixtures, json, ground-truth, brief_type, regression]

requires:
  - phase: 19-brief-type-weighted-scoring
    provides: BriefType enum, BRIEF_DIMENSION_WEIGHTS config used to design winner labels

provides:
  - backend/tests/fixtures/benchmark/*.json: 11 labeled campaign-comparison fixtures (brand×4, seeding×4, conversion×3)
  - backend/tests/fixtures/benchmark/schema.md: JSON format contract for runner in Plan 20-02
  - backend/benchmark/__init__.py: runner package placeholder

affects:
  - 20-02: regression runner reads glob backend/tests/fixtures/benchmark/*.json via json.load()

tech-stack:
  added: []
  patterns:
    - "Benchmark fixture pattern: static JSON files with id/brief_type/expected_winner_id/label_confidence/rationale/campaigns[] schema"
    - "Winner labeling heuristic: winner is the campaign whose expected score is highest under the corresponding BRIEF_DIMENSION_WEIGHTS profile"
    - "label_confidence=medium marks edge cases where actual performance is uncertain (used in benchmark denominator but flagged as uncertain)"

key-files:
  created:
    - backend/tests/fixtures/benchmark/schema.md
    - backend/tests/fixtures/benchmark/__init__.py
    - backend/tests/fixtures/benchmark/brand_001.json
    - backend/tests/fixtures/benchmark/brand_002.json
    - backend/tests/fixtures/benchmark/brand_003.json
    - backend/tests/fixtures/benchmark/brand_004.json
    - backend/tests/fixtures/benchmark/seeding_001.json
    - backend/tests/fixtures/benchmark/seeding_002.json
    - backend/tests/fixtures/benchmark/seeding_003.json
    - backend/tests/fixtures/benchmark/seeding_004.json
    - backend/tests/fixtures/benchmark/conversion_001.json
    - backend/tests/fixtures/benchmark/conversion_002.json
    - backend/tests/fixtures/benchmark/conversion_003.json
    - backend/benchmark/__init__.py
  modified: []

key-decisions:
  - "Fixture glob pattern for runner: backend/tests/fixtures/benchmark/*.json (excludes __init__.py via .json filter)"
  - "label_confidence=medium used for genuine edge cases (b003: UGC vs KOL; s003: date vs workplace; c003: group-buy vs repurchase) — runner counts these in denominator but flags as uncertain"
  - "seeding_004 winner is s004_b (graduation emotional hook), not s004_a (product catalog) — validates that runner picks emotional-resonance winner under seeding weight profile"

patterns-established:
  - "Fixture winner design: brand/seeding winners lead on emotional_resonance(0.30); conversion winners lead on conversion_readiness(0.35) and clarity — mirrors BRIEF_DIMENSION_WEIGHTS"
  - "Each fixture has exactly 2 campaigns to create a clear binary comparison (signal-to-noise for early regression runs)"

requirements-completed: [BENCH-01, BENCH-02]

duration: 3min
completed: 2026-03-18
---

# Phase 20 Plan 01: Benchmark Dataset Schema and Seed Fixtures Summary

**11 labeled campaign-comparison JSON fixtures (brand×4, seeding×4, conversion×3) with schema contract, each designed as a deterministic binary choice aligned to BRIEF_DIMENSION_WEIGHTS winner heuristics**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-18T07:42:18Z
- **Completed:** 2026-03-18T07:45:00Z
- **Tasks:** 2
- **Files modified:** 14 created

## Accomplishments

- Created `backend/tests/fixtures/benchmark/schema.md` — 6-field JSON format contract (id, brief_type, expected_winner_id, label_confidence, rationale, campaigns[])
- Created 11 benchmark fixture files: brand×4, seeding×4, conversion×3; all pass `json.load()` + schema validation + `expected_winner_id` membership check
- Created `backend/benchmark/__init__.py` package placeholder for Plan 20-02 runner

## Brief_type Distribution

| brief_type | count | confidence breakdown |
|-----------|-------|----------------------|
| brand | 4 | high×3, medium×1 |
| seeding | 4 | high×3, medium×1 |
| conversion | 3 | high×2, medium×1 |
| **total** | **11** | high×8, medium×3 |

## Task Commits

1. **Task 1: 创建 benchmark schema 文档和目录结构** - `3b081e6` (chore)
2. **Task 2: 创建 11 组 benchmark 种子数据** - `beda328` (feat)

## Files Created

- `backend/tests/fixtures/benchmark/schema.md` — JSON format contract doc
- `backend/tests/fixtures/benchmark/__init__.py` — package placeholder
- `backend/tests/fixtures/benchmark/brand_001.json` — 品牌情感叙事 vs 促销硬广, winner=b001_a
- `backend/tests/fixtures/benchmark/brand_002.json` — 品牌价值观纪录片 vs 产品参数图, winner=b002_a
- `backend/tests/fixtures/benchmark/brand_003.json` — UGC合集 vs 明星代言大片, winner=b003_b (medium)
- `backend/tests/fixtures/benchmark/brand_004.json` — 联名美学宣言 vs 新品上市图文, winner=b004_a
- `backend/tests/fixtures/benchmark/seeding_001.json` — 通勤vlog种草 vs 硬广投放, winner=s001_a
- `backend/tests/fixtures/benchmark/seeding_002.json` — 开箱30天测评 vs 安全科普长图, winner=s002_a
- `backend/tests/fixtures/benchmark/seeding_003.json` — 约会妆容教程 vs 职场精致感, winner=s003_a (medium)
- `backend/tests/fixtures/benchmark/seeding_004.json` — 12色全介绍 vs 毕业季情感钩, winner=s004_b
- `backend/tests/fixtures/benchmark/conversion_001.json` — 首单立减+7天退换 vs 品牌故事片, winner=c001_a
- `backend/tests/fixtures/benchmark/conversion_002.json` — 618限时闪购 vs 选购攻略长图, winner=c002_a
- `backend/tests/fixtures/benchmark/conversion_003.json` — 三人拼团5折 vs 回购续杯优惠, winner=c003_a (medium)
- `backend/benchmark/__init__.py` — runner package placeholder (run.py in Plan 20-02)

## Fixture Path Pattern (for Plan 20-02)

```python
import glob, json
files = glob.glob("backend/tests/fixtures/benchmark/*.json")
for f in files:
    fixture = json.load(open(f))
    # fixture["brief_type"], fixture["expected_winner_id"], fixture["campaigns"]
```

## Decisions Made

- Fixture glob pattern uses `*.json` (excludes `__init__.py` automatically)
- All fixtures use exactly 2 campaigns per comparison — creates clean binary signal for early regression runs
- `label_confidence=medium` reserved for 3 genuine edge cases where winner heuristic has inherent uncertainty
- Winner design follows BRIEF_DIMENSION_WEIGHTS exactly: brand/seeding winners dominate emotional_resonance(0.30), conversion winners dominate conversion_readiness(0.35)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 11 fixture files ready for Plan 20-02 regression runner to consume via glob
- `backend/benchmark/run.py` to be created in Plan 20-02
- Runner will call EvaluationOrchestrator with mock LLMClient, compare `rankings[0].campaign_id` vs `expected_winner_id`

---
*Phase: 20-benchmark-dataset-regression-runner*
*Completed: 2026-03-18*
