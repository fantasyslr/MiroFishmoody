# Phase 19: Brief-Type Weight Profiles - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

新增 brief_type 字段贯穿前后端（Campaign 模型 → API → 前端表单），实现 3 套维度权重配置（品牌/种草/转化），CampaignScorer 按 brief_type 加载权重，结果记录 weight_profile_version。

</domain>

<decisions>
## Implementation Decisions

### Brief Type 选择器 UI
- Radio button 组（3 选 1），最直观
- 无默认值，强制选择，防止误用
- 放置在品类选择器下方，自然流程

### 权重配置策略
- 权重文件格式：Python dict（`brief_weights.py`），零依赖
- 品牌传播核心维度：storytelling(0.30) + emotional_resonance(0.25)
- 转化拉新核心维度：conversion_readiness(0.35) + execution_readiness(0.25)
- 达人种草核心维度：authenticity(0.30) + content_generation(0.25)
- Version 格式：`"brand-v1"` / `"seeding-v1"` / `"conversion-v1"`

### Claude's Discretion
- BriefType enum 的具体值名称
- 各维度的完整权重数值（在核心维度确定的基础上分配剩余权重）
- API 层参数验证的具体错误消息
- 前端 radio 组的具体 CSS 样式

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `category` 路由模式（`data.get("category")` → orchestrator → scorer）可照搬给 brief_type
- `backend/app/services/campaign_scorer.py` — 已有 agent_scores 参数模式

### Established Patterns
- Config enum 在 `backend/app/config.py`
- 前端表单在 `frontend/src/pages/HomePage.tsx`

### Integration Points
- `backend/app/api/campaign.py` — API 层接收 brief_type
- `backend/app/services/evaluation_orchestrator.py` — 传导 brief_type
- `backend/app/services/campaign_scorer.py` — 加载对应权重
- `frontend/src/pages/HomePage.tsx` — radio 选择器

</code_context>

<specifics>
## Specific Ideas

- 参考 `category` 字段的传导路径，brief_type 同构扩展
- `weight_profile_version` 格式统一为 `{brief_type}-v{N}`

</specifics>

<deferred>
## Deferred Ideas

None

</deferred>
