---
phase: 19-brief-type-weight-profiles
plan: "03"
subsystem: api
tags: [brief_type, weight_profile, flask, react, typescript, enum-validation]

requires:
  - phase: 19-01
    provides: BriefType enum, BRIEF_TYPE_VALUES, brief_weights contracts
  - phase: 19-02
    provides: CampaignScorer brief_type param, EvaluationResult.weight_profile_version, DimensionEvaluator weight scaling
provides:
  - EvaluationOrchestrator.run() accepts and propagates brief_type to CampaignScorer and EvaluationResult
  - POST /api/campaign/evaluate validates brief_type enum, returns 400 on unknown value, backward-compatible on omit
  - Frontend evaluate/both mode renders 3-option brief_type selector (品牌传播/达人种草/转化拉新), blocks submit without selection
  - Full brief_type chain: UI selection -> API validation -> orchestrator -> scorer -> weight_profile_version in result JSON
affects:
  - 19-04 (if any): weight_profile_version is now written to EvaluationResult, downstream reports can read it
  - Phase 20: benchmark labeling now captures correct weight_profile_version per evaluation

tech-stack:
  added: []
  patterns:
    - "Enum validation at API boundary: BRIEF_TYPE_VALUES set check before BriefType() constructor, returns 400 with Chinese error message"
    - "Thread args tuple extended to pass brief_type_enum from API layer to orchestrator"
    - "Frontend radio-style button group with Tailwind active state; persisted to form state via persistForm()"

key-files:
  created: []
  modified:
    - backend/app/services/evaluation_orchestrator.py
    - backend/app/api/campaign.py
    - frontend/src/lib/api.ts
    - frontend/src/pages/HomePage.tsx

key-decisions:
  - "Thread args tuple (task_id, campaign_set, category, brief_type_enum) — brief_type_enum is None when not provided, ensuring backward compatibility without any conditional branching in thread spawn"
  - "Double validation in API: BRIEF_TYPE_VALUES set check first, then BriefType() constructor — belt-and-suspenders for clear 400 error message in Chinese"
  - "Frontend button-group (not native radio inputs) for consistent Tailwind styling; value stored as string union type matching API contract"

patterns-established:
  - "API enum validation: check value in BRIEF_TYPE_VALUES frozenset before constructing Enum; return 400 with descriptive Chinese error"
  - "Thread-based async API: extend args tuple to propagate new parameters rather than using kwargs or closures"
  - "Frontend form guard: check required field before payload construction, set uploadError and return early"

requirements-completed: [EVAL-01, EVAL-02, EVAL-05]

duration: ~15min
completed: 2026-03-18
---

# Phase 19 Plan 03: Brief Type Full-Chain Integration Summary

**brief_type 全链路接通：前端 3 选 1 UI + API 400 枚举校验 + orchestrator 传导 + 结果 JSON 写入 weight_profile_version**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-18
- **Completed:** 2026-03-18
- **Tasks:** 3 (+ 1 human-verify checkpoint, approved)
- **Files modified:** 4

## Accomplishments

- `EvaluationOrchestrator.run()` 新增 `brief_type` 参数，传给 `CampaignScorer`，写入 `EvaluationResult.weight_profile_version`；brief_type=None 完全向后兼容
- `POST /api/campaign/evaluate` 枚举校验：未知 brief_type 返回 HTTP 400 + 中文错误消息，不传 brief_type 返回 202（默认 seeding 行为）
- 前端 evaluate/both 模式新增必填 brief 类型按钮组（品牌传播 / 达人种草 / 转化拉新），未选中时阻止提交并显示中文提示
- 人工验证通过：brief_type 选择器可见，validation 工作正常，结果 JSON 包含 `weight_profile_version: "brand-v1"`

## Task Commits

Each task was committed atomically:

1. **Task 1: EvaluationOrchestrator brief_type** - `ca31a4c` (feat)
2. **Task 2: API 层 brief_type 400 校验** - `799d565` (feat)
3. **Task 3: 前端 brief_type 选择器** - `9c272b5` (feat)

## Files Created/Modified

- `backend/app/services/evaluation_orchestrator.py` - run() 新增 brief_type 参数，传给 CampaignScorer，写入 weight_profile_version
- `backend/app/api/campaign.py` - 提取 brief_type_raw，BRIEF_TYPE_VALUES 校验，400 on unknown，thread args 扩展
- `frontend/src/lib/api.ts` - EvaluatePayload 新增 brief_type 可选字段
- `frontend/src/pages/HomePage.tsx` - briefType state + 3 选 1 按钮组 + 提交前 guard

## Decisions Made

- Thread args tuple 追加 `brief_type_enum`（而非 kwargs）——保持现有 thread 模式一致性，None 值自然实现向后兼容
- API 双重校验（frozenset check + BriefType 构造器）确保 400 错误消息准确，避免 ValueError 漏出变成 500
- 前端使用 button 模拟 radio（非原生 input[type=radio]）以匹配现有 productLine 选择器的 Tailwind 样式

## Deviations from Plan

None — plan executed exactly as written. All 4 modifications per task matched the specified locations.

## Issues Encountered

- 后端 `uv run pytest -x -q` 失败于 `scripts/test_sync_etl_enrichment.py`（pyarrow 依赖缺失）和 `tests/test_phase56.py`（MagicMock JSON 序列化）。两者均为预存问题，与本 plan 无关。排除 scripts/ 后，278 tests passed, 1 pre-existing failure。

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 19 所有 plan (01/02/03) 完成，brief_type 全链路已接通
- Phase 20 benchmark labeling 可以开始：历史 campaign 评审结果将携带正确的 weight_profile_version
- 已知预存测试失败（test_phase56.py MagicMock JSON 序列化）需在 Phase 20 前修复以避免干扰 CI

---
*Phase: 19-brief-type-weight-profiles*
*Completed: 2026-03-18*
