# Phase 9: Bug Fixes - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix two v1.0 遗留缺陷: (1) Both 模式 ResultPage 无法跳转到 EvaluateResultPage, (2) Evaluate 结果页 diagnosticsMap 为空。

</domain>

<decisions>
## Implementation Decisions

### BUG-03: Both 模式跨页导航
- ResultPage 调用 getBothModeState() 读取 localStorage 中的 evaluateTaskId/evaluateSetId
- 如果 both-mode state 存在，显示"查看深度评审结果"链接跳转到 /evaluate-result?setId=X
- 导航后调用 clearBothModeState() 清理 localStorage
- 链接仅在 Evaluate 推演完成时显示（需轮询或检查任务状态）

### BUG-04: Evaluate 诊断面板数据接入
- Evaluate 管线（EvaluationOrchestrator）需在推演过程中调用 ImageAnalyzer 产出图片诊断
- 诊断数据附加到 evaluate 结果 JSON 中的 visual_diagnostics 字段
- EvaluateResultPage 从 API 响应中提取 visual_diagnostics 构建 diagnosticsMap
- 复用 Race 路径已有的 ImageAnalyzer + DiagnosticsPanel 基础设施

### Claude's Discretion
- ImageAnalyzer 在 Evaluate 管线中的调用时机（AudiencePanel 评分时并行 or 独立阶段）
- diagnosticsMap 的数据结构是否需要扩展（当前 VisualDiagnostics 类型已定义）

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/lib/api.ts`: saveBothModeState, getBothModeState, clearBothModeState (L391-410)
- `frontend/src/components/DiagnosticsPanel.tsx`: 已实现的可折叠诊断卡片组件
- `frontend/src/pages/EvaluateResultPage.tsx`: diagnosticsMap 基础设施已就绪（L67 空 map, L125 传入 RankingTab）
- `backend/app/services/image_analyzer.py`: ImageAnalyzer 已在 Race 路径中产出结构化诊断

### Established Patterns
- Race 路径: ImageAnalyzer → visual_profile.diagnostics → ResultPage DiagnosticsPanel
- localStorage 状态: save/get/clear 三件套模式 (api.ts)
- 异步推演结果: TaskManager + SQLite 持久化，轮询获取

### Integration Points
- ResultPage.tsx: 需读取 both-mode state 并渲染导航链接
- EvaluationOrchestrator: 需接入 ImageAnalyzer 调用
- Evaluate API 响应: 需包含 visual_diagnostics 字段
- EvaluateResultPage.tsx L67: diagnosticsMap 从空 map 改为从 API 响应构建

</code_context>

<specifics>
## Specific Ideas

No specific requirements — bug fixes with clear implementation path from v1.0 audit.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>
