---
phase: quick-260318-ohu
plan: 01
subsystem: campaign-scorer
tags: [brief-type, ranking, dim-boost, benchmark, tdd]
dependency_graph:
  requires: [campaign_scorer.py, submarket_evaluator.py, brief_weights.py]
  provides: [brief_type weighted ranking, brand_005 benchmark fixture]
  affects: [scoring pipeline, benchmark accuracy]
tech_stack:
  added: []
  patterns: [DIM_BOOST_WEIGHT signal blending, prefetch-and-reuse dimension_results]
key_files:
  created:
    - backend/tests/fixtures/benchmark/brand_005.json
  modified:
    - backend/app/services/campaign_scorer.py
    - backend/tests/test_benchmark_runner.py
    - backend/tests/test_scorer.py
decisions:
  - "DIM_BOOST_WEIGHT=0.15 (env-overridable): 维度信号占最终分 15%，足以在 brief_type 差异明显时翻转排名，不影响 brief_type=None 路径"
  - "预取 dim_results 并复用，避免 DimensionEvaluator 被调用两次"
  - "brand_005 label_confidence=high，固化明星KOL快转化 vs 高定情绪大片的典型失手场景"
metrics:
  duration: "~5 min"
  completed: "2026-03-18"
  tasks_completed: 2
  files_modified: 4
---

# Quick Task 260318-ohu Summary

**One-liner:** 将 brief_type 加权维度分（DIM_BOOST_WEIGHT=0.15）混入 overall_score 第三路信号，并用 brand_005.json 固化明星同款快转化 vs 高定情绪大片的回归 benchmark。

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | 将加权维度分混入 campaign_scorer.py 的最终 overall_score | bb8ae1f | campaign_scorer.py, test_scorer.py |
| 2 | 新增 brand_005.json 并更新 test_fixture_count 断言 | c560389 | brand_005.json, test_benchmark_runner.py |

## Fix Implementation (Task 1)

**Problem:** DimensionEvaluator 已对维度 softmax 概率按 brief_weights 缩放，但加权维度分未回流到 overall_score——排序仍由纯 BT+panel 概率决定，brief_type 权重配置实际上对最终 ranking 无效。

**Solution:** 在 `CampaignScorer.score()` 的 Overall scores 块之后、Agent score 块之前，插入 Brief-type dimension weight boost 逻辑：

1. `brief_type is not None` 时，预取 `dimension_results`
2. 按 campaign 汇总加权维度分（已是 `softmax × dim_weight`）
3. 归一化到 `sum=1` 得到 `dim_weighted_probs`
4. 混入：`final_score = base_score × (1 - 0.15) + dim_weighted_probs × 0.15`
5. `brief_type=None` 时 `dim_weights={}` → 完全跳过，行为不变
6. 复用预取结果，`dimension_results` 块改为条件分支，避免重复 evaluate

**Key constant:** `DIM_BOOST_WEIGHT = float(os.environ.get('DIM_BOOST_WEIGHT', '0.15'))`

## Benchmark Fixture (Task 2)

**File:** `backend/tests/fixtures/benchmark/brand_005.json`

- `brief_type`: brand
- `expected_winner_id`: b005_b（高定情绪大片）
- `label_confidence`: high
- Scenario: 明星同款速抢 KOL 快转化投流 vs 高定情绪大片品牌美学宣言

**Assertion updates:**
- `test_fixture_count`: 11 → 12
- `test_fixture_loading`: >=10 → >=11

## Test Results

```
50 passed in 0.21s
(test_scorer.py + test_benchmark_runner.py + test_brief_weights.py + test_campaign_scorer_agent_scores.py)
```

New tests added to `test_scorer.py`:
- `test_brief_type_none_backward_compat` — brief_type=None 行为不变
- `test_brief_type_brand_emotional_wins` — brief_type=brand 情感方案胜出
- `test_brief_type_conversion_wins` — brief_type=conversion 转化方案胜出

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- [x] `backend/app/services/campaign_scorer.py` — exists, contains `dim_weighted_scores`
- [x] `backend/tests/fixtures/benchmark/brand_005.json` — exists, contains `brand_editorial` context, `expected_winner_id=b005_b`
- [x] `backend/tests/test_benchmark_runner.py` — `len(files) == 12` assertion present
- [x] Commits bb8ae1f and c560389 exist in git log
- [x] 50 tests pass
