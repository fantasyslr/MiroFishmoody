# Phase 11: Export - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

结果页导出功能：Race ResultPage 和 EvaluateResultPage 均支持导出 PDF 报告和 PNG 图片截图。

</domain>

<decisions>
## Implementation Decisions

### Export 技术方案
- 前端生成：html2canvas 截图 + jsPDF 生成 PDF，零后端依赖
- 图片格式：PNG（无损，适合含图表截图）
- 导出范围：当前结果页可见内容（雷达图 + 分位条 + 诊断面板 + 方案对比）
- 触发方式：结果页顶部工具栏，"导出 PDF" + "导出图片" 两个独立按钮

### 导出内容排版
- PDF 布局：A4 竖版单页，标题 + 方案对比表 + 雷达图 + 诊断摘要
- 品牌元素：仅标题栏含 "MiroFishmoody 推演报告" + 日期，轻量不加 logo
- 图片截图区域：方案对比区域（雷达图 + 排名表），适合微信/钉钉分享

### 导出覆盖页面
- Race ResultPage：支持导出（含雷达图/分位/诊断）
- EvaluateResultPage：支持导出（含评审团排名/人格打分）
- 加载状态：按钮变 loading spinner + 禁用，截图 1-3 秒

### Claude's Discretion
- html2canvas 具体配置（scale、背景色、忽略元素）
- jsPDF 页面边距和字体大小
- 截图区域的 CSS selector 选择
- 导出文件命名规则

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/pages/ResultPage.tsx`: Race 结果页，含雷达图/分位/诊断
- `frontend/src/pages/EvaluateResultPage.tsx`: Evaluate 结果页，含排名/人格打分
- `frontend/src/components/RadarScoreChart.tsx`: recharts 雷达图
- `frontend/src/components/PercentileBar.tsx`: 百分位条
- `frontend/src/components/DiagnosticsPanel.tsx`: 诊断面板

### Established Patterns
- React 组件 + TypeScript strict
- Tailwind 样式
- recharts SVG 图表

### Integration Points
- ResultPage.tsx: 添加导出按钮和导出逻辑
- EvaluateResultPage.tsx: 添加导出按钮和导出逻辑
- package.json: 新增 html2canvas + jspdf 依赖

</code_context>

<specifics>
## Specific Ideas

- PDF 标题格式："MiroFishmoody 推演报告 — {campaign名称} — {日期}"
- 图片文件名："{campaign名称}_对比_{日期}.png"
- PDF 文件名："{campaign名称}_推演报告_{日期}.pdf"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>
