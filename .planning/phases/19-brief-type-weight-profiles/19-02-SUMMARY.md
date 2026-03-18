---
phase: 19-brief-type-weight-profiles
plan: "02"
subsystem: scoring-pipeline
tags: [brief-type, dimension-weights, evaluation, scoring]
dependency_graph:
  requires:
    - "19-01 (BRIEF_DIMENSION_WEIGHTS, BriefType, WEIGHT_PROFILE_VERSIONS)"
  provides:
    - "DimensionEvaluator.evaluate(brief_type=) weight injection"
    - "CampaignScorer(brief_type=) constructor param"
    - "EvaluationResult.weight_profile_version field"
  affects:
    - "19-03 (EvaluationOrchestrator will wire brief_type end-to-end)"
tech_stack:
  added: []
  patterns:
    - "Optional param with None=equal-weights fallback (backward compatible)"
    - "Softmax prob scaling by dim_weight (no renormalization within dimension)"
key_files:
  created: []
  modified:
    - backend/app/services/submarket_evaluator.py
    - backend/app/services/campaign_scorer.py
    - backend/app/models/evaluation.py
decisions:
  - "brief_type=None → dim_weights={} → no scaling applied, fully backward compatible"
  - "Weight scaling applied after softmax (not before), so relative per-campaign ranking within a dimension is preserved; weight only affects cross-dimension contribution magnitude"
  - "weight_profile_version field excluded from to_dict() when None, consistent with existing Optional field pattern"
metrics:
  duration: ~4 min
  completed: "2026-03-18T07:24:16Z"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 3
---

# Phase 19 Plan 02: Brief-Type Weight Injection into Scoring Pipeline Summary

**One-liner:** brief_type 权重通过 DimensionEvaluator → CampaignScorer 管道注入，EvaluationResult 新增 weight_profile_version 可追溯字段。

## What Was Built

将 Plan 19-01 中定义的 `BRIEF_DIMENSION_WEIGHTS` 注入实际评分管道：

1. `DimensionEvaluator.evaluate()` 新增 `brief_type: Optional[BriefType] = None` 参数，根据 brief_type 对 softmax 概率进行维度权重缩放
2. `CampaignScorer.__init__()` 新增 `brief_type` 参数，存储后在 `evaluate()` 调用时透传
3. `EvaluationResult` 新增 `weight_profile_version: Optional[str]` 字段，`to_dict()` 按条件输出

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | DimensionEvaluator 应用 brief_type 权重 | b3c4437 | backend/app/services/submarket_evaluator.py |
| 2 | CampaignScorer 接受并传递 brief_type | 04aed72 | backend/app/services/campaign_scorer.py |
| 3 | EvaluationResult 新增 weight_profile_version | 4d5252c | backend/app/models/evaluation.py |

## Decisions Made

- **softmax 后缩放：** 权重作用于 softmax 概率而非原始分，保证 campaign 间相对排名不变，weight 仅影响跨维度比较时的贡献比例
- **不归一化：** 各维度独立，缩放后 softmax 概率之和不再为 1，但跨维度聚合时这正是所需行为
- **backward compatibility 优先：** `brief_type=None` 时 `dim_weights={}` 无任何修改路径触发，100% 与修改前等价

## Verification Results

- `DimensionEvaluator brief_type OK` — brief_type=None 和 brief_type=CONVERSION 均正常，结果长度一致
- `CampaignScorer brief_type OK` — BRAND 实例 brief_type 正确存储，无参实例默认 None
- `EvaluationResult weight_profile_version OK` — 设置时 to_dict() 含该 key，未设置时不含
- `BRIEF_DIMENSION_WEIGHTS['conversion']['conversion_readiness'] == 0.35` — conversion brief 权重验证通过
- 665 tests passed (2 pre-existing failures excluded: test_sync_etl_enrichment parquet dep + test_phase56 MagicMock serialization)

## Deviations from Plan

None — plan executed exactly as written.

## Pre-existing Test Failures (Out of Scope)

- `scripts/test_sync_etl_enrichment.py::test_idempotent_rerun` — pyarrow/fastparquet 缺失，与本次修改无关
- `tests/test_phase56.py::test_run_evaluation_fails_on_empty_pairwise` — MagicMock not JSON serializable in judge_calibration，pre-existing
- `tests/test_smoke.py::TestHealth::test_enhanced_health` — pre-existing TypeError

## Self-Check: PASSED

- [x] `backend/app/services/submarket_evaluator.py` — exists, contains `brief_type` (4 lines), `BRIEF_DIMENSION_WEIGHTS` (import + use)
- [x] `backend/app/services/campaign_scorer.py` — exists, contains `brief_type` (3 lines), `self.brief_type` in __init__ and evaluate call
- [x] `backend/app/models/evaluation.py` — exists, contains `weight_profile_version` (field + to_dict), defaults None
- [x] Commits b3c4437, 04aed72, 4d5252c — all exist on moody-main
