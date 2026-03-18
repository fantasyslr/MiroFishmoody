# Phase 15: Multi-Agent Foundation - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning
**Source:** Autonomous smart discuss (infrastructure phase)

<domain>
## Phase Boundary

建立全局 LLM 并发控制和统一 agent 输出 schema，为 Phase 16 的多 agent 扩展打基础。纯后端基础设施，无前端变更。

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase. Key constraints from research:
- MA-01: 全局 LLMSemaphore 从 ImageAnalyzer 层提升到 LLMClient 层，`MAX_LLM_CONCURRENT` 在 config.py 可配置
- MA-02: AgentScore dataclass 统一 schema，CampaignScorer 自动注册新 agent 类型（无需手工 wiring）
- 现有 ThreadPoolExecutor + Semaphore 模式继续沿用
- Bailian API 并发限制保守设为 5（config 可调）

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/image_helpers.py` — 现有 Semaphore 模式参考
- `backend/app/services/evaluation_orchestrator.py` — agent 调度入口
- `backend/app/services/campaign_scorer.py` — 评分聚合

### Established Patterns
- Python type hints, dataclass for data models
- Services 层放在 `backend/app/services/`
- Config 在 `backend/app/config.py`

### Integration Points
- `LLMClient` 或等效调用点 — Semaphore 注入位置
- `CampaignScorer` — AgentScore 注册和聚合
- `EvaluationOrchestrator` — 新 agent 类型 wiring

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 15-multi-agent-foundation*
*Context gathered: 2026-03-18 via autonomous smart discuss*
