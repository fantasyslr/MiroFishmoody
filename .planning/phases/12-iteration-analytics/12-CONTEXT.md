# Phase 12: Iteration & Analytics - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

方案迭代推演（版本关联 + 对比视图）+ 推演趋势 Dashboard（跨 campaign 趋势图 + 品类筛选）。

</domain>

<decisions>
## Implementation Decisions

### 版本关联模型
- 存储：campaign 表新增 nullable parent_campaign_id FK 指向父 campaign
- 版本号：自动递增 v1, v2, v3，基于 parent chain 长度计算
- 迭代入口：结果页"迭代优化"按钮，预填父 campaign 信息到新建表单

### 版本对比视图
- 布局：左右并排两列，左侧旧版本，右侧新版本
- 改善/退步标注：维度分数旁用 ↑↓ 箭头 + 绿/红色，直观标注每个维度变化
- 对比范围：最近两个版本自动对比（不做任意版本选择）

### 趋势 Dashboard
- 入口：顶部导航新增"趋势"tab，与首页平级
- 图表：recharts LineChart，时间轴 x 总分 y，每条线一个 campaign
- 数据源：后端 API 聚合已有推演结果，不需要新表，从现有数据查询
- 品类筛选：顶部 SegmentedControl，全部/透明片/彩片 三选一

### Claude's Discretion
- 版本对比页面路由设计（/compare?v1=X&v2=Y 或 /campaign/:id/compare）
- Dashboard API 的聚合查询方式（SQL groupBy 或 Python 聚合）
- LineChart 颜色方案和 tooltip 格式
- "迭代优化"按钮的具体文案和位置

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/RadarScoreChart.tsx`: recharts 雷达图，可在对比视图中复用
- `frontend/src/lib/api.ts`: API 客户端，需扩展 campaign 版本和趋势 API
- `backend/app/api/campaign.py`: campaign CRUD，需扩展版本关联
- `backend/app/models/`: SQLite 模型层

### Established Patterns
- 前端路由：React Router，页面在 pages/ 目录
- 后端 API：Flask Blueprint，RESTful 风格
- 图表：recharts（已安装，用于雷达图）
- 样式：Tailwind CSS

### Integration Points
- campaign 表：新增 parent_campaign_id 字段
- ResultPage / EvaluateResultPage：新增"迭代优化"按钮
- App.tsx：新增 Dashboard 路由和导航 tab
- 后端：新增趋势聚合 API endpoint

</code_context>

<specifics>
## Specific Ideas

- "迭代优化"按钮应明确表达"基于此方案创建新版本"的含义
- Dashboard 的 LineChart 应该能看出每个 campaign 随时间的分数变化
- 品类筛选使用"品类"一词，不用"产线"（CLAUDE.md 要求）

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>
