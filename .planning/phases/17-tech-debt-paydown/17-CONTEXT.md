# Phase 17: Tech Debt Paydown - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning
**Source:** Autonomous smart discuss (infrastructure phase)

<domain>
## Phase Boundary

收窄 threading.Lock 范围（I/O 和 LLM 调用不在锁内），为 BrandStateEngine 写表征测试，提取 BacktestEngine 为独立类。纯后端重构，无前端变更。

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure/refactoring phase. Key constraints:
- TD-01: Lock 作用域仅覆盖 dict 读写操作，LLM 调用和文件 I/O 不在 lock 内
- TD-02: 先写 characterization tests（捕获现有行为），再提取 BacktestEngine
- Strangler fig 模式：BrandStateEngine 保留引用提取后的 BacktestEngine，现有测试不变

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `backend/app/services/brandiction_engine.py` — BrandStateEngine God class (~1319 lines)
- `backend/app/api/campaign.py` — _evaluation_store 使用 threading.Lock

### Established Patterns
- Phase 10 决策: Lock scopes minimal — only dict ops under lock, no I/O or LLM calls
- pytest for all backend testing

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase

</specifics>

<deferred>
## Deferred Ideas

None

</deferred>
