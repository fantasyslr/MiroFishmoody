# MiroFishmoody — 品牌 Campaign 推演引擎

## What This Is

品牌 campaign 推演工具，帮助 Moody Lenses 的品牌/创意/媒介团队在 campaign 上线前，将多套方案（含 KV 主视觉、产品图、模特图等视觉素材）进行推演对比，快速筛选最优方案。支持快速排名（Race）和深度评审（Evaluate）两条推演路径，统一入口一键发起。按品类（透明片/彩片）配置独立评审人格，多维度可视化对比结果。支持推演结果导出 PDF/图片、方案迭代版本对比、跨 campaign 趋势追踪。

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
- ✓ Both 模式跨页导航（ResultPage → EvaluateResultPage）— v1.1
- ✓ Evaluate 诊断面板数据接入（visual_diagnostics）— v1.1
- ✓ _evaluation_store 线程安全（threading.Lock）— v1.1
- ✓ SQLite WAL 模式 + busy_timeout — v1.1
- ✓ 密码哈希存储（bcrypt）— v1.1
- ✓ 结果导出 PDF/图片（html2canvas + jsPDF）— v1.1
- ✓ 方案迭代推演（版本对比）— v1.1
- ✓ 推演趋势 Dashboard — v1.1

- ✓ Evaluate 模式 payload 字段映射修复（evaluate 端点可用）— v2.0
- ✓ Both 模式 race condition 修复（await + try/finally）— v2.0
- ✓ RunningPage 真实进度展示（假动画移除）— v2.0
- ✓ API 契约锁定（contracts.ts）— v2.0
- ✓ 表单状态 sessionStorage 持久化 — v2.0
- ✓ Winner-first 结果页布局（hero card）— v2.0
- ✓ 品类人格预览（sidebar 展示 9/8 人格）— v2.0
- ✓ 跨路径一致性 badge（Race vs Evaluate 冠军矛盾警示）— v2.0
- ✓ Step indicator + SplitPanel + LogBuffer 新组件 — v2.0
- ✓ PDF 多页导出修复 — v2.0
- ✓ 全局 LLM Semaphore（LLMClient 层）— v2.0
- ✓ AgentScore 统一 schema + CampaignScorer 自动注册 — v2.0
- ✓ PersonaRegistry 扩展（moodyPlus 9 / colored_lenses 8）— v2.0
- ✓ MultiJudge 位置交替 ensemble — v2.0
- ✓ Devil's advocate judge（品牌怀疑者）— v2.0
- ✓ 跨人格争议分数 + 前端 badge — v2.0
- ✓ ConsensusAgent 异常值检测 — v2.0
- ✓ threading.Lock 范围审计注释 — v2.0
- ✓ BrandStateEngine 表征测试 + BacktestEngine 提取 — v2.0

### Active

(None — all v2.0 requirements shipped. Define next milestone.)

### Out of Scope

- 视频/GIF 素材推演 — LLM vision 按帧计费，成本和复杂度过高
- 移动端 App — Web 优先，内部工具不需要原生 App
- 实时协作编辑 — 内部工具，不需要实时协同
- 外部用户注册/OAuth — 内部工具，env var 用户表够用
- AI 自动生成创意素材 — 推演工具定位是评估，不是生成
- 真人消费者 panel 调研 — 成本高，已有独立调研流程
- 眼动追踪/注意力热力图 — 需专用模型，非通用 LLM 能力
- BrandStateEngine 完整重构 — v2.0 已提取 BacktestEngine（第一刀），剩余方法待后续 milestone
- AgentScore→CampaignScorer 生产者接入 — v2.0 建立了 schema 和 scorer 参数，但无 producer 输出 AgentScore

## Context

**产品背景：**
- Moody Lenses 是隐形眼镜品牌，有两个品类：moodyPlus（透明片）和 colored_lenses（彩片）
- 品牌竞争点是功能+美学，绝不以折扣/价格为卖点
- Campaign 以视觉素材为核心，推演已纳入视觉分析

**技术现状（v2.0 shipped）：**
- 后端 Flask + SQLite (WAL mode) + Qwen（通过百炼 OpenAI-compatible API）
- 前端 React 19 + TypeScript + Tailwind + Vite + recharts + html2canvas + jsPDF + motion 12
- 两条推演路径（Race + Evaluate）完整可用，Both 模式稳定
- 品类人格配置：moodyPlus 9 人格，colored_lenses 8 人格
- MultiJudge 位置交替 ensemble + Devil's advocate judge
- 全局 LLM Semaphore（LLMClient 层，MAX_LLM_CONCURRENT=5）
- AgentScore 统一 schema + CampaignScorer 自动注册
- ConsensusAgent 异常值检测 + 前端争议 badge
- 前端：sessionStorage 持久化、Winner hero card、跨路径 badge、SplitPanel + LogBuffer
- 结果导出 PDF 多页 + 图片
- 方案迭代推演 + 版本对比 + 趋势 Dashboard

**已知技术债：**
- BrandStateEngine 仍然较大（BacktestEngine 已提取，剩余方法待分解）
- BaselineRanker 全量加载历史数据
- AgentScore→CampaignScorer 生产者未接入（schema 就位但死代码）
- contracts.ts 存在但无页面消费者（类型从 api.ts 直接导入）
- test_phase56.py MagicMock JSON 序列化失败（pre-existing）

## Constraints

- **LLM Provider**: 通义千问 via 百炼 OpenAI-compatible API
- **Multimodal**: 必须支持视觉分析（图片 base64 → LLM vision）
- **存储**: SQLite (WAL mode) — 短期内不迁移到 PostgreSQL
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
| 全局 LLM Semaphore 在 LLMClient 层 | 统一并发控制，防止 Bailian 429，各服务不再各自管理 | ✓ Good |
| MultiJudge 位置交替 ensemble | 奇偶 judge 收到不同顺序，消除 position bias | ✓ Good |
| Devil's advocate "品牌怀疑者" | 挑战正面结论，dissent 标记独立追踪 | ✓ Good |
| AgentScore schema + 自动注册 | 统一输出格式，新 agent 无需手工 wiring | ✓ Good (producer 待接入) |
| BacktestEngine strangler fig | 先写表征测试再提取，现有测试不变 | ✓ Good |
| recharts 用于雷达图可视化 | 轻量 SVG，React-native，适合多维度对比 | ✓ Good |
| 前端导出（html2canvas + jsPDF） | 零后端依赖，Docker 不需 headless browser | ✓ Good |
| 版本链靠 set 级 parent_set_id | Campaign 级 parent_campaign_id 过于复杂，set 级版本链够用 | ✓ Good |
| 趋势 API 聚合现有结果 JSON | 不需要新表，从已有推演结果文件提取趋势数据 | ✓ Good |

---
*Last updated: 2026-03-18 after v2.0 milestone complete*
