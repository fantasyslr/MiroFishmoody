# MiroFishmoody

Moody 内部营销决策系统，当前包含两条主线能力：

- `Campaign Evaluation Engine`：面向创意 / campaign 方案的异步评审、导出、赛后结算与校准
- `Brandiction Engine v3`：面向历史证据驱动赛马的 Baseline Ranking、BrandState Hypothesis、Race History

[English](./README-EN.md) | [使用教程](./docs/USAGE_GUIDE.md) | [部署说明](./DEPLOY.md) | [后端快速开始](./backend/QUICKSTART.md) | [Brandiction 路线文档](./docs/MOODY_BRANDICTION_ENGINE.md)

## 项目概览

这个仓库不是单一页面应用，而是一套前后端一体的内部工具：

- `frontend/` 是 React + Vite 的操作台，当前主界面聚焦 Brandiction 赛马流程
- `backend/` 是 Flask API，提供登录、方案评审、历史数据导入、Brandiction 赛马、赛后结算和校准能力
- `backend/uploads/` 保存 SQLite 数据库、评审结果、上传图片和运行产物
- Docker 部署时，Flask 会直接托管前端构建产物，所以生产环境默认只暴露 `5001`

### 当前最适合怎么用

- 如果你要做“多方案历史证据赛马”，优先用 `Brandiction Engine v3`
- 如果你要走“API 驱动的 campaign 评审与导出”，用 `/api/campaign/*`
- 如果你要做 BrandState / replay / predict / simulate，这些能力已进仓库，但其中一部分仍应视为实验层

## 主要能力

### 1. Campaign Evaluation Engine

后端提供一条完整的异步评审链路：

- 自然语言 brief 解析：`POST /api/campaign/parse-brief`
- 可选图片上传：`POST /api/campaign/upload-image`
- 异步评审：`POST /api/campaign/evaluate`
- 进度轮询：`GET /api/campaign/evaluate/status/<task_id>`
- 查看结果：`GET /api/campaign/result/<set_id>`
- 导出结果：`GET /api/campaign/export/<set_id>`
- 赛后结算：`POST /api/campaign/resolve`
- 校准查看 / 重校准：`GET /api/campaign/calibration`、`POST /api/campaign/recalibrate`

### 2. Brandiction Engine v3

这是当前前端主界面的核心路径：

- 历史数据导入：`/api/brandiction/import-history`、`/api/brandiction/import-csv`
- 数据脊柱查询：`history / interventions / signals / competitor-events / stats`
- Baseline Ranking：基于 `market × product_line × audience_segment × platform × channel_family × theme × landing_page`
- Season-aware weighting：支持 `618 / double11 / 38 / 99 / cny / regular`
- Cold-start fallback：同品类不足时尝试跨品类迁移或全量分位数估计
- Race History：自动保存每次赛马结果，并支持赛后 `resolve`
- Hypothesis Layer：`predict / replay / probability-board / simulate / compare-scenarios`

### 3. 前端工作台

当前前端已经提供：

- 登录页
- Campaign Lab / Brandiction Race Builder
- Running / Result 页面
- 管理员 Dashboard
- Race History 页面

当前路由使用 `Hash Router`，本地访问和 Flask 托管访问都可直接使用。

## 技术栈

- 前端：React 19、TypeScript、Vite、Tailwind、Zustand
- 后端：Flask、SQLite、Pydantic
- 模型接入：OpenAI 兼容接口
- 部署：Docker / docker compose / Gunicorn

## 目录结构

```text
MiroFishmoody/
├── frontend/               # React 前端
├── backend/                # Flask 后端
│   ├── app/api/            # auth / campaign / brandiction API
│   ├── app/services/       # baseline ranker、orchestrator、brand state 等
│   ├── tests/              # 后端测试
│   └── uploads/            # SQLite、结果文件、图片、日志产物
├── docs/                   # 路线文档与使用教程
├── static/                 # README 资源
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 快速开始

### 前置要求

- Node.js `18+`
- Python `3.11+`
- `uv`（推荐，用于后端依赖管理）
- 一个可用的 OpenAI 兼容 LLM API Key

### 1. 克隆仓库

```bash
git clone https://github.com/fantasyslr/MiroFishmoody.git
cd MiroFishmoody
```

### 2. 准备环境变量

```bash
cp .env.example .env
```

至少要配置下面几项：

```env
LLM_API_KEY=your-api-key
SECRET_KEY=replace-with-a-random-string
MOODY_USERS=admin:StrongPassword123:Admin:admin,analyst:StrongPassword123:Analyst:user
```

### 3. 安装依赖

```bash
npm run setup
npm run setup:backend
```

### 4. 启动开发环境

```bash
npm run dev
```

默认地址：

- 前端：<http://localhost:5173>
- 后端 API：<http://localhost:5001>
- 健康检查：<http://localhost:5001/health>

Vite 已代理 `/api` 和 `/health` 到 `5001`，所以本地开发时直接打开前端即可。

### 5. 生产 / 演示部署

```bash
docker compose up -d --build
```

启动后直接访问：

- <http://localhost:5001>

生产模式下 Flask 会托管 `frontend/dist`。

## 环境变量

| 变量 | 是否必填 | 用途 |
|------|----------|------|
| `LLM_API_KEY` | 是 | 评审和模型相关能力的 API Key |
| `LLM_BASE_URL` | 否 | OpenAI 兼容接口地址 |
| `LLM_MODEL_NAME` | 否 | 默认模型名 |
| `SECRET_KEY` | 是 | Flask Session 密钥 |
| `MOODY_USERS` | 是 | 登录用户表，格式为 `username:password:display_name:role,...` |
| `FLASK_DEBUG` | 否 | 后端调试模式 |
| `FLASK_HOST` | 否 | 监听地址，默认 `0.0.0.0` |
| `FLASK_PORT` | 否 | 端口，默认 `5001` |
| `JUDGE_TEMPERATURE` | 否 | 评审模型温度 |
| `PANEL_TEMPERATURE` | 否 | Panel 模型温度 |
| `MAX_CAMPAIGNS` | 否 | Campaign Evaluation 最多方案数 |
| `USE_MARKET_JUDGE` | 否 | 是否启用实验性 Market-Making Judge |

## 常用开发命令

### 根目录

```bash
npm run setup
npm run setup:backend
npm run dev
npm run backend
npm run frontend
npm run build
```

### 后端

```bash
cd backend
uv run python run.py
uv run pytest tests -q
```

### 前端

```bash
cd frontend
npm run dev
npm run build
npm run lint
```

## 两条推荐使用路径

### 路径 A：Brandiction Web 工作流

1. 配置 `MOODY_USERS` 并启动项目
2. 用管理员账号登录
3. 导入历史数据
4. 在首页配置 `Market / Product Line / Optimization Target / Season Context`
5. 输入 2-5 个策略方向并发起 race
6. 在结果页查看：
   - `Observed Baseline`
   - `Match Quality`
   - `Seasonal Drift`
   - `Cold Start Hint`
   - `Model Hypothesis`
7. 管理员进入 Dashboard / History 做数据覆盖检查和赛后结算

完整操作说明见 [使用教程](./docs/USAGE_GUIDE.md)。

### 路径 B：Campaign Evaluation API 工作流

1. 登录：`POST /api/auth/login`
2. 可选上传图片：`POST /api/campaign/upload-image`
3. 提交异步评审：`POST /api/campaign/evaluate`
4. 轮询进度：`GET /api/campaign/evaluate/status/<task_id>`
5. 拉取结果：`GET /api/campaign/result/<set_id>`
6. 导出 JSON：`GET /api/campaign/export/<set_id>`
7. 赛后结算：`POST /api/campaign/resolve`

后端快速命令见 [backend/QUICKSTART.md](./backend/QUICKSTART.md)。

## API 总览

### 认证

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

### Campaign Evaluation

- `POST /api/campaign/parse-brief`
- `POST /api/campaign/upload-image`
- `GET /api/campaign/images/<set_id>`
- `POST /api/campaign/evaluate`
- `GET /api/campaign/evaluate/status/<task_id>`
- `GET /api/campaign/result/<set_id>`
- `GET /api/campaign/export/<set_id>`
- `POST /api/campaign/resolve`
- `GET /api/campaign/calibration`
- `POST /api/campaign/recalibrate`

### Brandiction

- `POST /api/brandiction/import-history`
- `POST /api/brandiction/import-csv`
- `GET /api/brandiction/history`
- `GET /api/brandiction/history/<run_id>`
- `GET /api/brandiction/interventions`
- `GET /api/brandiction/signals`
- `GET /api/brandiction/competitor-events`
- `GET /api/brandiction/stats`
- `POST /api/brandiction/race`
- `GET /api/brandiction/race-history`
- `GET /api/brandiction/race-history/<run_id>`
- `POST /api/brandiction/race-history/<run_id>/resolve`
- `GET /api/brandiction/brand-state`
- `GET /api/brandiction/brand-state/latest`
- `POST /api/brandiction/brand-state/build`
- `POST /api/brandiction/replay`
- `POST /api/brandiction/predict`
- `POST /api/brandiction/probability-board`
- `POST /api/brandiction/backtest`
- `POST /api/brandiction/simulate`
- `POST /api/brandiction/compare-scenarios`

## 数据与持久化

默认运行时数据保存在 `backend/uploads/`，包括：

- `tasks.db`：Campaign Evaluation 任务状态
- `brandiction.db`：Brandiction 数据脊柱
- `results/`：评审结果 JSON
- `images/`：上传的 campaign 素材
- 其他导出与日志文件

如果你用 Docker，`docker-compose.yml` 已将上传目录挂载为持久卷 `uploads-data`。

## 文档索引

- [使用教程](./docs/USAGE_GUIDE.md)
- [部署说明](./DEPLOY.md)
- [后端快速开始](./backend/QUICKSTART.md)
- [Brandiction 路线文档](./docs/MOODY_BRANDICTION_ENGINE.md)
- [更新日志](./CHANGELOG.md)

## 已验证的基础命令

当前仓库常用验证命令：

```bash
cd frontend && npm run build
cd backend && uv run pytest tests/test_v3_baseline_ranker.py -q
```

如果你要发版，建议至少再补一轮完整后端测试和一次手工烟测。

## License

`AGPL-3.0`
