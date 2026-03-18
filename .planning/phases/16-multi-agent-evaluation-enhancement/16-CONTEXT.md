# Phase 16: Multi-Agent Evaluation Enhancement - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

扩展评审团规模（moodyPlus 6→9, colored_lenses 5→8），引入 MultiJudge 位置交替消除偏差，添加 devil's advocate 反面视角，实现跨人格争议分数并在前端展示 badge，ConsensusAgent 检测离群评分。

</domain>

<decisions>
## Implementation Decisions

### 争议 Badge 展示
- 争议阈值：stdev >= 2.0（10 分制），适中敏感度
- Badge 样式：橙色圆角标签 "争议"，醒目但不警报
- Badge 位置：方案名称旁边，一眼可见

### 新增人格配置
- moodyPlus 新增 3 个人格：科技感知者、医疗合规顾问、日常佩戴体验者（补全透明片功能维度）
- colored_lenses 新增 3 个人格：彩妆博主、摄影师/视觉创作者、亚文化爱好者（补全彩片美学维度）
- Devil's advocate 视角定位："品牌怀疑者" — 挑战所有正面结论

### Claude's Discretion
- MultiJudge 内部实现细节（线程池、投票聚合方式）
- ConsensusAgent stdev 阈值（可参考争议 badge 同用 2.0）
- 人格 JSON 配置的具体 prompt 措辞
- 前端 badge 的精确 CSS 样式

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/persona_registry.py` — 人格注册和加载
- `backend/app/services/pairwise_judge.py` — 已有 PairwiseJudge 位置互换
- `backend/app/models/agent_score.py` — Phase 15 新建的 AgentScore dataclass
- `backend/app/services/campaign_scorer.py` — 已有 agent_scores 参数

### Established Patterns
- 人格配置 JSON 在 `backend/app/data/persona_presets/`
- PairwiseJudge 已有位置互换逻辑（正反序各评一次）
- ThreadPoolExecutor + 全局 LLMSemaphore（Phase 15 建立）

### Integration Points
- PersonaRegistry — 新人格 JSON 配置
- PairwiseJudge — MultiJudge 包装器
- EvaluationOrchestrator — devil's advocate + ConsensusAgent wiring
- EvaluateResultPage — 争议 badge 渲染

</code_context>

<specifics>
## Specific Ideas

- MultiJudge 强制轮换呈现顺序：奇数 judge 收到 (A,B)，偶数 judge 收到 (B,A)
- Devil's advocate 异见投票标记 `dissent: true`，在结果 JSON 中独立可追踪
- ConsensusAgent 用 `statistics.stdev` 检测离群，标记 `suspect: true`

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 16-multi-agent-evaluation-enhancement*
*Context gathered: 2026-03-18 via autonomous smart discuss*
