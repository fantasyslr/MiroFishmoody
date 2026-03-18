# Phase 14: Frontend Rewrite — Core Pages - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning

<domain>
## Phase Boundary

用 MiroFish 参考模式重写全部核心页面交互：表单状态持久化、winner-first 结果布局、品类人格预览、跨路径一致性 badge、Step indicator 进度指示器、SplitPanel + LogBuffer 新组件。保持 `lib/api.ts` 和 `contracts.ts` 不动。

</domain>

<decisions>
## Implementation Decisions

### 表单与导航交互
- sessionStorage 在 onChange 时实时保存，零丢失风险
- 恢复时静默恢复，无弹窗提示（内部工具追求效率）
- 提交成功后清除 sessionStorage 数据

### 结果页布局
- Winner-first：顶部 hero card 显示冠军名称 + 得分 + 雷达图缩略
- 跨路径不一致 badge：结果页顶部固定横幅，最显眼
- Badge 文案："⚠ Race 与 Evaluate 冠军不一致" — 直接明了
- 品类人格预览：品类 select 下方展开列表，上下文关联

### Step Indicator 与进度展示
- 横向步骤条（数字+标签），当前步骤高亮，参考 MiroFish 模式
- 3 步划分：方案解析 → 评审分析 → 结果汇总
- SplitPanel 仅用于 RunningPage（左进度右日志），最小改动
- LogBuffer 自动滚到底部，200 行缓冲

### Claude's Discretion
- 具体组件拆分和文件结构
- CSS/Tailwind 实现细节
- 动画 timing 和 easing 参数
- 组件内部状态管理方式

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/lib/contracts.ts` — Phase 13 新建的 API 契约文件
- `frontend/src/lib/api.ts` — API client（FROZEN，不可修改）
- `frontend/src/components/` — 现有可复用组件（RadarChart, PercentileBar, DiagnosticsPanel）
- `motion` 12.x — 已安装，可用于 SplitPanel 动画

### Established Patterns
- React 19 + TypeScript strict + Tailwind
- Pages 在 `frontend/src/pages/`
- Components 在 `frontend/src/components/`
- Utilities 在 `frontend/src/lib/`

### Integration Points
- `HomePage.tsx` — 表单持久化 + 品类预览
- `RunningPage.tsx` — Step indicator + SplitPanel + LogBuffer
- `EvaluateResultPage.tsx` — Winner hero card + 跨路径 badge
- `ResultPage.tsx` — 跨路径 badge（Race 侧）

</code_context>

<specifics>
## Specific Ideas

- 参考 MiroFish 的横向步骤指示器模式（数字圆圈 + 连线 + 标签）
- SplitPanel 动画用 motion `animate={{ width }}` + cubic-bezier `[0.4, 0, 0.2, 1]`
- LogBuffer 参考 MiroFish 的 2s 轮询 + 200 条日志缓冲模式

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 14-frontend-rewrite-core-pages*
*Context gathered: 2026-03-18 via autonomous smart discuss*
