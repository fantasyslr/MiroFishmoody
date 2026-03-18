# Phase 20: Benchmark Dataset + Regression Runner - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning
**Source:** Autonomous smart discuss (infrastructure phase)

<domain>
## Phase Boundary

建立 benchmark 数据集 schema，创建种子数据（10 组已标注 campaign），实现 mock LLMClient 确定性回放 runner，按 brief_type 分别输出命中率。

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure testing infrastructure phase. Key constraints from research:
- Benchmark schema：inputs (campaign set JSON) + expected_winner + label_confidence + rationale + brief_type
- 种子数据至少 10 组：品牌/种草/转化各 3-4 组
- Runner mock LLMClient.chat_json，确定性回放，不需要 HTTP server
- 输出按 brief_type 分别报告命中率（brand/seeding/conversion 各自百分比）
- 数据放在 `backend/tests/fixtures/benchmark/`
- Runner 入口 `backend/benchmark/run.py`

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EvaluationOrchestrator.run()` — 纯 Python 方法，接受 CampaignSet
- `LLMClient` — mock `chat_json` 即可确定性回放
- `brief_weights.py` — Phase 19 新建的权重配置

### Integration Points
- `EvaluationOrchestrator` — benchmark runner 的入口
- `CampaignScorer` — 带 brief_type 的评分管道
- `LLMClient` — mock 注入点

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase

</specifics>

<deferred>
## Deferred Ideas

None

</deferred>
