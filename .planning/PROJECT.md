# MiroFishmoody — 品牌 Campaign 推演引擎

## What This Is

品牌 campaign 推演工具，帮助 Moody Lenses 的品牌/创意/媒介团队在 campaign 上线前，将多套方案（含 KV 主视觉、产品图、模特图等视觉素材）进行推演对比，快速筛选最优方案。支持快速排名（Race）和深度评审（Evaluate）两条推演路径，统一入口一键发起。按品类（透明片/彩片）配置独立评审人格，多维度可视化对比结果。

## Core Value

让每一次 campaign 在上线前都能得到数据化的推演对比，而非单纯靠直觉和会议拍板——用 AI 推演替代"拍脑袋"决策。

## Requirements

### Validated

- ✓ 用户认证与角色权限（admin/user）— existing
- ✓ Campaign 信息录入（名称、描述、产品线、受众等）— existing
- ✓ 图片上传与存储（KV、产品图、模特图，最多5张/campaign）— existing
- ✓ Race 推演路径：历史基线匹配 + 视觉分析 + 快速排名 — existing
- ✓ 历史 campaign 数据导入（JSON/CSV）— existing
- ✓ 历史基线排名引擎（ROAS、CVR、purchase_rate 等维度）— existing
- ✓ LLM 视觉分析引擎（ImageAnalyzer，多模态视觉评分）— existing
- ✓ Brand State 认知模型（品牌状态预测）— existing
- ✓ 异步任务管理（TaskManager + SQLite 持久化）— existing
- ✓ Docker 部署 + GitHub Actions CI — existing
- ✓ 审计日志（写操作 + 导出操作记录）— existing
- ✓ Evaluate 路径图片正确解析（统一 resolve_image_path）— v1.0
- ✓ 高分辨率图片自动缩放（base64 前 max 1024px）— v1.0
- ✓ PersonaRegistry 服务（从硬编码提取为配置化）— v1.0
- ✓ 人格配置预设集 + schema 校验 — v1.0
- ✓ 按品类配置评审人格（moodyPlus 6人格 / colored_lenses 5人格）— v1.0
- ✓ 品类选择驱动人格自动加载 — v1.0
- ✓ 多张图片并行分析（ThreadPoolExecutor + Semaphore）— v1.0
- ✓ PairwiseJudge 位置互换去偏 — v1.0
- ✓ 视觉诊断建议结构化（issues[] + recommendations[]）— v1.0
- ✓ Evaluate 推演前端页面（发起、进度轮询、结果展示）— v1.0
- ✓ 评审团打分详情（3-tab: 排名/人格/对比）— v1.0
- ✓ 统一推演入口（Race/Evaluate/Both 模式选择器）— v1.0
- ✓ 统一方案录入表单 — v1.0
- ✓ 多方案并排对比视图 — v1.0
- ✓ 多维度雷达图可视化（recharts）— v1.0
- ✓ 历史基线分位展示（PercentileBar）— v1.0
- ✓ 诊断建议在 Race 结果页展示（DiagnosticsPanel）— v1.0

### Active

- [ ] Both 模式 ResultPage → EvaluateResultPage 导航链接（getBothModeState 未消费）
- [ ] Evaluate 结果页诊断面板数据接入（当前 diagnosticsMap 为空）
- [ ] _evaluation_store 线程安全（threading.Lock）
- [ ] SQLite WAL 模式 + busy_timeout
- [ ] 密码哈希存储（bcrypt）
- [ ] 结果导出 PDF/图片
- [ ] 方案迭代推演（版本对比）
- [ ] 推演趋势 Dashboard

### Out of Scope

- 视频/GIF 素材推演 — LLM vision 按帧计费，成本和复杂度过高
- 移动端 App — Web 优先，内部工具不需要原生 App
- 实时协作编辑 — 内部工具，不需要实时协同
- 外部用户注册/OAuth — 内部工具，env var 用户表够用
- AI 自动生成创意素材 — 推演工具定位是评估，不是生成
- 真人消费者 panel 调研 — 成本高，已有独立调研流程
- 眼动追踪/注意力热力图 — 需专用模型，非通用 LLM 能力
- BrandStateEngine 重构 — 当前能用，等 characterization tests 建好后再拆

## Current Milestone: v1.1 加固与增强

**Goal:** 修复 v1.0 遗留技术债，补全 Both 模式和 Evaluate 诊断，新增结果导出、迭代推演和趋势 Dashboard

**Target features:**
- Both 模式跨页导航
- Evaluate 诊断面板数据接入
- 线程安全 + SQLite WAL + 密码哈希
- 结果导出 PDF/图片
- 方案迭代推演（版本对比）
- 推演趋势 Dashboard

## Context

**产品背景：**
- Moody Lenses 是隐形眼镜品牌，有两个品类：moodyPlus（透明片）和 colored_lenses（彩片）
- 品牌竞争点是功能+美学，绝不以折扣/价格为卖点
- Campaign 以视觉素材为核心，推演已纳入视觉分析

**技术现状（v1.0 shipped）：**
- 后端 Flask + SQLite + Qwen（通过百炼 OpenAI-compatible API）
- 前端 React 19 + TypeScript + Tailwind + Vite + recharts
- 40 个 Python 文件（~10,100 LOC）+ 23 个 TypeScript 文件（~3,900 LOC）
- 两条推演路径（Race + Evaluate）完整可用
- 品类人格配置：moodyPlus 6 人格，colored_lenses 5 人格
- 并发图片分析 + Judge 去偏 + 结构化诊断

**已知技术债：**
- _evaluation_store 无线程锁（跨团队使用有风险）
- Both 模式缺少跨页面导航
- Evaluate 管线不产生图片诊断
- BrandStateEngine God class (1319 lines)
- BaselineRanker 全量加载历史数据

## Constraints

- **LLM Provider**: 通义千问 via 百炼 OpenAI-compatible API
- **Multimodal**: 必须支持视觉分析（图片 base64 → LLM vision）
- **存储**: SQLite — 短期内不迁移到 PostgreSQL
- **部署**: Docker 单容器
- **UI 文案**: 中文，品类用"品类"不用"产线"

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 保留两条推演路径（Race + Evaluate） | Race 做日常快速筛选，Evaluate 做重要 campaign 深度分析 | ✓ Good |
| 按品类分人格画像 | 透明片和彩片用户群体差异大，同一套人格不够精准 | ✓ Good |
| 不迁移 PostgreSQL | 内部工具用户量小，SQLite + WAL 够用 | ✓ Good |
| Fork 而非重写 | 原项目已有大量推演基础设施，改造比重写快 | ✓ Good |
| 共享 image_helpers 工具模块 | 统一图片路径解析和 base64 编码，避免三个服务各自实现 | ✓ Good |
| PersonaRegistry DI 模式 | 依赖注入让 AudiencePanel 可测试，人格配置可按品类切换 | ✓ Good |
| ThreadPoolExecutor + Semaphore 并发 | 复用现有模式，Semaphore 统一控制 LLM 并发 | ✓ Good |
| PairwiseJudge 位置互换去偏 | 正反序各评一次，标记不一致判断，不改变 winner 确定逻辑 | ✓ Good |
| recharts 用于雷达图可视化 | 轻量 SVG，React-native，适合多维度对比 | ✓ Good |

---
*Last updated: 2026-03-17 after v1.1 milestone started*
