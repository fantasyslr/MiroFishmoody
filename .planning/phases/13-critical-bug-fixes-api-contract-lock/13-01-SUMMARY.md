---
phase: 13-critical-bug-fixes-api-contract-lock
plan: "01"
subsystem: backend/api
tags: [bug-fix, api-contract, evaluate-endpoint, tdd]
dependency_graph:
  requires: []
  provides: [_parse_evaluate_campaigns, evaluate-202-response]
  affects: [backend/app/api/campaign.py, evaluate-endpoint]
tech_stack:
  added: []
  patterns: [TDD-RED-GREEN, parser-function-isolation]
key_files:
  created:
    - backend/tests/test_phase13_evaluate_parser.py
    - backend/tests/test_phase13_evaluate_endpoint.py
  modified:
    - backend/app/api/campaign.py
decisions:
  - "新增 _parse_evaluate_campaigns() 而非修改 _parse_campaigns()，保持 /race 路径不受影响"
  - "evaluate() 返回 202 Accepted（修正自 200），匹配异步任务启动语义"
  - "端点集成测试使用 mock EvaluationOrchestrator 避免 LLM_API_KEY 依赖"
metrics:
  duration: "~4min"
  completed_date: "2026-03-18"
  tasks_completed: 2
  files_changed: 3
---

# Phase 13 Plan 01: BUG-05 Evaluate Payload Field Mismatch Fix Summary

**One-liner:** 新增 `_parse_evaluate_campaigns()` 接受前端 `{campaign_id, description}` 字段，替换 evaluate() 中对 `_parse_campaigns()` 的错误调用，修复所有 Evaluate 提交 400 的 BUG-05。

## What Was Built

- `_parse_evaluate_campaigns(data: dict) -> CampaignSet`：新解析函数，专门处理前端 EvaluatePayload 形状
  - `campaign_id` 优先于 `id`，保持与已上传图片文件名前缀一致
  - `description` 映射为 `core_message`；缺失时回退为 `name`，不抛异常
  - `product_line` 无效值安全回退为 `colored_lenses`
  - 少于 2 个方案时抛 `ValueError("至少需要 2 个 campaign 方案")`
  - 重复 `campaign_id` 时抛 `ValueError`

- `evaluate()` 端点两处修改：
  1. 第 351 行：`_parse_campaigns(data)` → `_parse_evaluate_campaigns(data)`
  2. 返回码 200 → 202（异步任务启动语义）

- 测试覆盖：5 个解析器单元测试 + 1 个端点集成测试

## Verification Results

```
backend/tests/test_phase13_evaluate_parser.py::test_parse_evaluate_campaigns_basic PASSED
backend/tests/test_phase13_evaluate_parser.py::test_parse_evaluate_campaigns_image_paths PASSED
backend/tests/test_phase13_evaluate_parser.py::test_parse_evaluate_campaigns_id_mapping PASSED
backend/tests/test_phase13_evaluate_parser.py::test_parse_evaluate_campaigns_description_fallback PASSED
backend/tests/test_phase13_evaluate_parser.py::test_parse_evaluate_campaigns_min_campaigns PASSED

backend/tests/test_phase13_evaluate_endpoint.py::test_evaluate_endpoint_accepts_evaluate_payload PASSED

Full suite (excl. parquet): 606 passed, 2 failed, 10 skipped
  - 2 pre-existing failures (LLM_API_KEY not configured in test env)
  - Baseline maintained (was 601 passed + our 6 new passing tests = 607 total, minus 1 pre-existing)
```

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 (TDD RED) | 37798d2 | test(13-01): add failing tests for _parse_evaluate_campaigns |
| Task 2 (TDD GREEN) | 8385091 | feat(13-01): implement _parse_evaluate_campaigns() and fix evaluate() endpoint |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed evaluate() return code 200 → 202**
- **Found during:** Task 2 implementation
- **Issue:** `evaluate()` returned HTTP 200 for async task creation; correct semantic for "accepted for processing" is 202 Accepted
- **Fix:** Added `, 202` to the `return jsonify(...)` call in `evaluate()`
- **Files modified:** `backend/app/api/campaign.py`
- **Commit:** 8385091

**2. Endpoint test uses self-contained fixtures**
- **Found during:** Task 1 — conftest.py has no `client` or `auth_headers` fixtures
- **Fix:** Test file defines its own `app`/`client` fixtures (matching test_smoke.py pattern) and uses Flask session login instead of auth headers
- **Note:** No fixture named `auth_headers` exists in this project; auth is cookie/session-based

## Self-Check: PASSED

- backend/tests/test_phase13_evaluate_parser.py — FOUND
- backend/tests/test_phase13_evaluate_endpoint.py — FOUND
- backend/app/api/campaign.py — FOUND
- Commit 37798d2 — FOUND
- Commit 8385091 — FOUND
