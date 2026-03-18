# MiroFishmoody

Moody 内部 Campaign 推演引擎，帮助品牌/创意/媒介团队在 campaign 上线前，用 AI 对多套方案进行数据化推演对比，替代"拍脑袋"决策。

[English](./README-EN.md) | [使用教程](./docs/USAGE_GUIDE.md) | [部署说明](./DEPLOY.md) | [后端快速开始](./backend/QUICKSTART.md) | [Brandiction 路线文档](./docs/MOODY_BRANDICTION_ENGINE.md)

## 核心能力

### 双路径推演

| 路径 | 适用场景 | 输出 |
|------|---------|------|
| **Race（快速排名）** | 日常筛选，2-5 个方案快速对比 | 历史基线匹配 + 视觉分析 + 综合排名 |
| **Evaluate（深度评审）** | 重要 campaign，需要多维度深度分析 | 评审团人格打分 + 两两对比 + BT 综合排名 |
| **Both（双线并行）** | 同时获得快速排名和深度评审 | Race 结果 + 一键跳转查看 Evaluate 结果 |

### 按品类独立人格

- **moodyPlus（透明片）**：9 个评审人格，侧重功能性
- **colored_lenses（彩片）**：8 个评审人格，侧重美学表达
- 选择品类后系统自动加载对应人格预设

### Multi-Agent 评审

- **MultiJudge 位置交替 ensemble**：多 judge 位置轮换消除 position bias
- **Devil's advocate（品牌怀疑者）**：挑战正面结论，异见投票独立标记
- **ConsensusAgent**：检测人格间评分离群值，标记可疑评分
- **跨人格争议 badge**：评分分歧大的方案自动标记"争议"

### Brief 类型权重

- 发起推演时选择 Brief 类型：**品牌传播** / **达人种草** / **转化拉新**
- 系统自动加载对应维度权重（品牌侧重 storytelling + emotional_resonance，转化侧重 conversion_readiness）
- 权重混入最终 ranking，不仅是展示层

### 视觉分析

- 上传 KV 主视觉、产品图、模特图（最多 5 张/方案）
- ImageAnalyzer 多模态视觉评分 + 结构化诊断建议（qwen3.5-plus 视觉模型）
- 多张图片并行分析（ThreadPoolExecutor + 全局 LLM Semaphore 控速）
- PairwiseJudge 位置互换去偏

### 结果可视化与导出

- 多方案并排对比视图
- 多维度雷达图（recharts）
- 历史基线分位展示（PercentileBar）
- 诊断建议面板（DiagnosticsPanel）
- **导出 PDF 报告**（多页分页）/ **导出 PNG 截图**（适合微信/钉钉分享）
- **跨路径一致性 badge**：Race 与 Evaluate 冠军不一致时自动告警

### 方案迭代推演

- 结果页一键"迭代优化"，基于当前方案创建新版本
- 版本自动关联，支持版本历史查看
- **版本对比视图**：左右并排，↑↓ 箭头标注改善/退步维度

### 推演趋势 Dashboard

- 跨 campaign 推演分数趋势图（recharts LineChart）
- 按品类筛选（全部品类 / 透明片 / 彩片）
- 顶部导航"趋势"tab，全用户可见

### Brandiction Engine v3

历史证据驱动的赛马引擎：

- 历史数据导入（JSON / CSV）
- Baseline Ranking：基于 market × product_line × audience × platform × channel × theme × landing_page
- Season-aware weighting（618 / 双11 / 38 / 99 / CNY / regular）
- Cold-start fallback（跨品类迁移 / 全量分位数估计）
- BrandState Hypothesis Layer（predict / replay / simulate / compare-scenarios）

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | React 19, TypeScript, Vite, Tailwind, recharts, html2canvas, jsPDF, motion |
| 后端 | Flask, SQLite (WAL mode), Python 3.11+ |
| LLM | 通义千问 via 百炼 Coding Plan（文本: qwen3-coder-plus, 视觉: qwen3.5-plus） |
| 评审 | MultiJudge ensemble, Devil's advocate, ConsensusAgent, Brief-type 权重 |
| 安全 | bcrypt 密码哈希, 全局 LLM Semaphore 并发保护 |
| 部署 | Docker / Railway / Gunicorn |

## 目录结构

```text
MiroFishmoody/
├── frontend/               # React 前端
│   └── src/
│       ├── pages/          # 页面组件
│       ├── components/     # 可复用组件（雷达图、诊断面板、StepIndicator、SplitPanel 等）
│       └── lib/            # API 客户端、导出工具
├── backend/                # Flask 后端
│   ├── app/api/            # auth / campaign / brandiction API
│   ├── app/services/       # 推演编排、图片分析、人格注册等
│   ├── app/models/         # 数据模型
│   └── tests/              # 后端测试
├── docs/                   # 使用教程与路线文档
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 快速开始

### 前置要求

- Node.js `18+`
- Python `3.11+`
- `uv`（推荐，用于后端依赖管理）
- 百炼 API Key（通义千问 OpenAI-compatible）

### 1. 克隆仓库

```bash
git clone https://github.com/fantasyslr/MiroFishmoody.git
cd MiroFishmoody
```

### 2. 准备环境变量

```bash
cp .env.example .env
```

至少配置：

```env
LLM_API_KEY=your-bailian-api-key
LLM_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
LLM_MODEL_NAME=qwen3-coder-plus
LLM_VISION_MODEL=qwen3.5-plus
SECRET_KEY=replace-with-a-random-string
MOODY_USERS=admin:StrongPassword123:Admin:admin,analyst:StrongPassword123:Analyst:user
```

> 密码支持明文和 bcrypt 哈希格式，明文密码在首次加载时自动哈希。

### 3. 安装依赖

```bash
npm run setup:all
```

### 4. 启动开发环境

```bash
npm run dev
```

- 前端：<http://localhost:5173>
- 后端 API：<http://localhost:5001>
- Vite 已代理 `/api` 到后端

### 5. 生产部署

```bash
docker compose up -d --build
```

访问 <http://localhost:5001>（Flask 托管前端构建产物）。

## 前端页面

| 页面 | 路由 | 说明 |
|------|------|------|
| 登录 | `/login` | 用户认证 |
| 首页 | `/` | 统一推演入口（Race / Evaluate / Both 模式选择 + 方案录入） |
| 推演中 | `/running` | 异步推演进度轮询 |
| Race 结果 | `/result` | 快速排名结果 + 雷达图 + 诊断 + 导出 |
| Evaluate 结果 | `/evaluate-result` | 评审团排名 + 人格打分 + 对比 + 导出 |
| 版本对比 | `/compare` | 两版本并排对比，标注改善/退步 |
| 趋势 Dashboard | `/trends` | 跨 campaign 推演趋势图 + 品类筛选 |
| Race History | `/history` | Brandiction 赛马历史 |
| 管理员 Dashboard | `/dashboard` | 数据管理与赛后结算 |

## API 总览

### 认证

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

### Campaign 推演

- `POST /api/campaign/parse-brief` — 自然语言 brief 解析
- `POST /api/campaign/upload-image` — 图片上传
- `POST /api/campaign/evaluate` — 发起推演（Race / Evaluate / Both）
- `GET /api/campaign/evaluate/status/<task_id>` — 进度轮询
- `GET /api/campaign/result/<set_id>` — 查看结果
- `GET /api/campaign/export/<set_id>` — 导出 JSON
- `POST /api/campaign/resolve` — 赛后结算
- `GET /api/campaign/version-history/<set_id>` — 版本历史
- `GET /api/campaign/compare?v1=<set_id>&v2=<set_id>` — 版本对比
- `GET /api/campaign/trends?category=<all|colored_lenses|moodyplus>` — 趋势数据

### Brandiction

- `POST /api/brandiction/import-history` / `import-csv`
- `GET /api/brandiction/history` / `stats` / `signals`
- `POST /api/brandiction/race`
- `GET /api/brandiction/race-history`
- `POST /api/brandiction/predict` / `replay` / `simulate` / `compare-scenarios`

## 环境变量

| 变量 | 必填 | 用途 |
|------|------|------|
| `LLM_API_KEY` | 是 | 百炼 API Key |
| `LLM_BASE_URL` | 否 | 百炼端点（默认 `coding.dashscope.aliyuncs.com/v1`） |
| `LLM_MODEL_NAME` | 否 | 文本模型（默认 `qwen3-coder-plus`） |
| `LLM_VISION_MODEL` | 否 | 视觉模型（默认 `qwen3.5-plus`） |
| `MAX_LLM_CONCURRENT` | 否 | LLM 并发上限（默认 `5`） |
| `SECRET_KEY` | 是 | Flask Session 密钥 |
| `MOODY_USERS` | 是 | 用户表（`username:password:display_name:role,...`） |
| `FLASK_DEBUG` | 否 | 调试模式 |
| `FLASK_HOST` | 否 | 监听地址（默认 `0.0.0.0`） |
| `FLASK_PORT` | 否 | 端口（默认 `5001`） |
| `JUDGE_TEMPERATURE` | 否 | 评审模型温度 |
| `PANEL_TEMPERATURE` | 否 | Panel 模型温度 |
| `MAX_CAMPAIGNS` | 否 | 最多方案数 |

## 常用命令

```bash
# 开发
npm run dev              # 前后端同时启动
npm run backend          # 仅后端
npm run frontend         # 仅前端

# 构建与测试
npm run build            # 前端生产构建
cd backend && uv run pytest  # 后端测试

# 部署
docker compose up -d --build
```

## 版本历史

| 版本 | 日期 | 主要内容 |
|------|------|---------|
| v1.0 | 2026-03-17 | MVP — 双路径推演 + 品类人格 + 统一入口 + 可视化 |
| v1.1 | 2026-03-17 | 加固与增强 — Bug fix + 线程安全 + bcrypt + 导出 + 迭代推演 + 趋势 Dashboard |
| v2.0 | 2026-03-18 | 大改造 — 前端交互重写 + MultiJudge ensemble + Devil's advocate + 争议 badge + BacktestEngine 提取 |
| v2.1 | 2026-03-18 | 部署修复 + 评审偏差修正 — Railway 部署 + Brief-type 权重接入 ranking + Benchmark 12 fixtures |

## 文档索引

- [使用教程](./docs/USAGE_GUIDE.md)
- [部署说明](./DEPLOY.md)
- [后端快速开始](./backend/QUICKSTART.md)
- [Brandiction 路线文档](./docs/MOODY_BRANDICTION_ENGINE.md)
- [更新日志](./CHANGELOG.md)

## License

`AGPL-3.0`
