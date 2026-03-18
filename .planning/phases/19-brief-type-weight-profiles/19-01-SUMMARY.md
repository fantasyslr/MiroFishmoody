---
phase: 19-brief-type-weight-profiles
plan: "01"
subsystem: backend-models-services
tags: [brief-type, weights, enum, data-contract]
dependency_graph:
  requires: []
  provides:
    - BriefType enum (backend/app/models/campaign.py)
    - BRIEF_DIMENSION_WEIGHTS (backend/app/services/brief_weights.py)
    - WEIGHT_PROFILE_VERSIONS (backend/app/services/brief_weights.py)
    - BRIEF_TYPE_VALUES (backend/app/services/brief_weights.py)
  affects:
    - Phase 19-02: CampaignScorer 将依赖 BRIEF_DIMENSION_WEIGHTS
    - Phase 19-03: API 层将依赖 BriefType + BRIEF_TYPE_VALUES 做校验
tech_stack:
  added: []
  patterns: [str-Enum, frozenset-for-validation, TDD-red-green]
key_files:
  created:
    - backend/app/services/brief_weights.py
    - backend/tests/test_brief_type_enum.py
    - backend/tests/test_brief_weights.py
  modified:
    - backend/app/models/campaign.py
decisions:
  - "BriefType 放在 ProductLine 之后、Campaign dataclass 之前，与已有 Enum 模式一致"
  - "emotional_resonance 作为第 6 个维度占位，当前 DimensionEvaluator 不输出时权重贡献 0，不破坏已有评分"
  - "BRIEF_TYPE_VALUES 使用 frozenset 而非 list，语义更明确且 O(1) 查找"
metrics:
  duration_seconds: 104
  completed_date: "2026-03-18"
  tasks_completed: 2
  files_changed: 4
---

# Phase 19 Plan 01: BriefType Enum + Weight Profiles Summary

**One-liner:** BriefType(str, Enum) + 3-profile weight config via brief_weights.py establishing the data contract for downstream CampaignScorer and API validation.

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | 新增 BriefType enum 到 campaign.py | cb92a16 | campaign.py, test_brief_type_enum.py |
| 2 | 创建 brief_weights.py 权重配置文件 | ea4f840 | brief_weights.py, test_brief_weights.py |

## What Was Built

**Task 1 — BriefType enum**

Added `class BriefType(str, Enum)` with BRAND/SEEDING/CONVERSION values to `backend/app/models/campaign.py`. Placed immediately after `ProductLine`, before `Campaign` dataclass. Pattern mirrors existing `ProductLine` exactly.

**Task 2 — brief_weights.py**

Created `backend/app/services/brief_weights.py` with:
- `BRIEF_DIMENSION_WEIGHTS`: 3 weight profiles (brand/seeding/conversion), each covering 6 dimensions summing exactly to 1.0
- `WEIGHT_PROFILE_VERSIONS`: version strings brand-v1 / seeding-v1 / conversion-v1
- `BRIEF_TYPE_VALUES`: frozenset for O(1) API validation

The 6th dimension `emotional_resonance` is a reserved placeholder — weight 0.0 for conversion, 0.30 for brand/seeding. Current DimensionEvaluator does not output this dimension; the placeholder ensures the weight config is future-proof without breaking existing scorer math.

## Verification Results

- `uv run pytest tests/test_brief_type_enum.py tests/test_brief_weights.py`: 18/18 passed
- `BriefType('brand') == BriefType.BRAND`: OK
- All 3 weight profiles sum to exactly 1.0 (verified programmatically)
- Pre-existing failures (test_phase56, test_smoke::test_enhanced_health) are unrelated to this plan

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] `backend/app/models/campaign.py` — BriefType enum added
- [x] `backend/app/services/brief_weights.py` — file created
- [x] `backend/tests/test_brief_type_enum.py` — 6 tests
- [x] `backend/tests/test_brief_weights.py` — 12 tests
- [x] Commit cb92a16 exists
- [x] Commit ea4f840 exists
