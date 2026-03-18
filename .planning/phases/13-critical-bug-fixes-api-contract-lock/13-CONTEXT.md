# Phase 13: Critical Bug Fixes + API Contract Lock - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning
**Source:** Autonomous smart discuss (infrastructure phase)

<domain>
## Phase Boundary

修复三个阻断性 bug（图片盲评、Both 模式 race condition、RunningPage 假动画）并锁定 contracts.ts 防止 Phase 14 重写期间 API drift。纯技术修复，无新用户功能。

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure/bug fix phase. Key constraints from research:
- BUG-05 真实根因是 EvaluatePayload 字段映射错误，需新建 `_parse_evaluate_campaigns()`
- BUG-06 修复在 HomePage.tsx 302-311 行，`await evaluateCampaigns()` 后再导航
- BUG-07 RunningPage 是 Race 同步路径无 task_id，改为诚实 spinner
- FE-08 contracts.ts 从 api.ts re-export 类型，不修改 api.ts 本身

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/image_helpers.py` — resolve_image_path() 已正确实现
- `frontend/src/lib/api.ts` — 现有 API client，FROZEN 不可修改
- `frontend/src/pages/EvaluatePage.tsx` — 已有正确的轮询模式可参考

### Established Patterns
- Backend: Flask route handlers thin, business logic in services/
- Frontend: React + TypeScript strict, Tailwind styling
- Testing: pytest for backend, npm run build for frontend type checking

### Integration Points
- `backend/app/api/campaign.py` — evaluate() endpoint 需要新解析器
- `frontend/src/pages/HomePage.tsx` — Both mode 导航逻辑
- `frontend/src/pages/RunningPage.tsx` — 假动画替换

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure/bug fix phase

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 13-critical-bug-fixes-api-contract-lock*
*Context gathered: 2026-03-18 via autonomous smart discuss*
