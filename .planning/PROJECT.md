# MiroFishmoody — 品牌 Campaign 推演引擎

## What This Is

基于 MiroFish（社会级推演平台）改造的品牌 campaign 推演工具，帮助 Moody Lenses 的品牌/创意/媒介团队在 campaign 上线前，将多套方案（含 KV 主视觉、产品图、模特图等视觉素材）进行推演对比，快速筛选最优方案。支持快速排名（Race）和深度评审（Evaluate）两条推演路径。

## Core Value

让每一次 campaign 在上线前都能得到数据化的推演对比，而非单纯靠直觉和会议拍板——用 AI 推演替代"拍脑袋"决策。

## Requirements

### Validated

<!-- 已有代码中已实现并可用的能力 -->

- ✓ 用户认证与角色权限（admin/user）— existing
- ✓ Campaign 信息录入（名称、描述、产品线、受众等）— existing
- ✓ 图片上传与存储（KV、产品图、模特图，最多5张/campaign）— existing
- ✓ Race 推演路径：历史基线匹配 + 视觉分析 + 快速排名 — existing
- ✓ 历史 campaign 数据导入（JSON/CSV）— existing
- ✓ 历史基线排名引擎（ROAS、CVR、purchase_rate 等维度）— existing
- ✓ LLM 视觉分析引擎（ImageAnalyzer，多模态视觉评分）— existing
- ✓ Brand State 认知模型（品牌状态预测）— existing
- ✓ Evaluate 推演后端：5 人格评审团 + 两两对比 + Bradley-Terry 模型 — existing (API only)
- ✓ 异步任务管理（TaskManager + SQLite 持久化）— existing
- ✓ 推演结果展示页面（排名 + 分数 + 维度对比）— existing (Race only)
- ✓ Docker 部署 + GitHub Actions CI — existing
- ✓ 审计日志（写操作 + 导出操作记录）— existing

### Active

<!-- 当前需要构建的改造目标 -->

- [ ] Evaluate 路径前端 UI — 用户可在前端发起深度评审推演，而非仅 API 调用
- [ ] 修复 Evaluate 路径图片静默失效 bug — image_paths 是 URL 但代码用 os.path.exists() 检查
- [ ] 按品类配置评审人格 — 透明片和彩片使用不同的用户画像评审团
- [ ] 统一推演入口 — 用户可选择 Race（快速）或 Evaluate（深度）或两者联合
- [ ] 并行图片分析 — 当前串行分析多张图片，需改为并发提升性能
- [ ] 跨团队协作体验 — 多用户同时使用时的基本稳定性（_evaluation_store 线程安全、SQLite WAL 模式）
- [ ] 密码安全 — 从明文改为哈希存储和比较

### Out of Scope

- 视频/GIF 素材推演 — 当前聚焦静态图片，视频分析复杂度和成本过高
- 移动端 App — Web 优先，内部工具不需要原生 App
- 实时协作编辑 — 内部工具，不需要 Google Docs 级别的实时协同
- 外部用户注册/OAuth — 内部工具，env var 用户表够用
- 大规模数据分析/BI 报表 — 推演工具不是 BI 平台

## Context

**产品背景：**
- Moody Lenses 是隐形眼镜品牌，有两个品类：moodyPlus（透明片）和 colored_lenses（彩片）
- 品牌竞争点是功能+美学，绝不以折扣/价格为卖点
- Campaign 以视觉素材为核心（KV 主视觉、产品图、模特图），推演必须纳入视觉分析

**技术背景：**
- Fork 自 MiroFish 开源项目（社会级推演），已做大量品牌场景改造
- 后端 Flask + SQLite + Qwen（通过百炼 OpenAI-compatible API）
- 前端 React 19 + TypeScript + Tailwind + Vite
- 已有一批历史 campaign 数据可导入做基线匹配

**使用场景：**
- 跨团队使用（品牌/创意/媒介）
- Campaign 上线前用推演对比多个方案
- 快速筛选用 Race，重要决策用 Evaluate

**已知问题：**
- Evaluate 路径的图片处理有 bug（`AudiencePanel` 和 `PairwiseJudge` 的 image_paths 处理不走 `_resolve_image_url_to_path()`）
- `_evaluation_store` 是内存 dict，无淘汰策略，无线程锁
- `BrandStateEngine` 是 1319 行的 God class
- `BaselineRanker` 每次调用加载全量历史数据到内存
- CORS 配置有误、SECRET_KEY 有硬编码 fallback、FLASK_DEBUG 默认开启

## Constraints

- **LLM Provider**: 通义千问 via 百炼 OpenAI-compatible API — 不可切换为直接 OpenAI
- **Multimodal**: 必须支持视觉分析（图片 base64 → LLM vision）— 核心能力
- **存储**: SQLite — 短期内不迁移到 PostgreSQL，用户量小
- **部署**: Docker 单容器 — 保持简单
- **UI 文案**: 中文，品类用"品类"不用"产线"

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 保留两条推演路径（Race + Evaluate） | Race 做日常快速筛选，Evaluate 做重要 campaign 深度分析 | — Pending |
| 按品类分人格画像 | 透明片和彩片用户群体差异大，同一套人格不够精准 | — Pending |
| 不迁移 PostgreSQL | 内部工具用户量小，SQLite + WAL 够用 | — Pending |
| Fork 而非重写 | 原项目已有大量推演基础设施，改造比重写快 | ✓ Good |

---
*Last updated: 2026-03-17 after initialization*
