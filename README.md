# Moody Campaign Choice Engine

Moody Lenses 内部 campaign 决策引擎 —— 用 LLM 驱动的多维度评审，帮助营销团队在多个 campaign 方案之间做出数据化选择。

## 这是什么

Campaign Choice Engine 是一个**内部工具**，解决的问题是：当团队有多个 campaign 创意方案时，如何快速、结构化地评估和排序。

引擎通过 LLM 模拟多角色评审（Audience Panel + Pairwise 对比），结合 Bradley-Terry 排名模型和概率聚合，输出每个方案的综合得分和排名。支持赛后结算和评审校准（Brier Score / Log-Loss），持续提升评审质量。

## 当前已实现

- **多方案异步评审**：提交 2-6 个 campaign 方案，后台异步评审并返回排名
- **多维度评分**：Audience Panel 多角色打分 + Pairwise 两两对比
- **概率聚合**：Bradley-Terry + Panel 均值 + 异议惩罚，三信号 softmax 聚合
- **赛后结算与校准**：用真实结果反向校准评审模型，追踪 Brier Score 和 Log-Loss
- **评审员权重校准**：根据历史准确度调整各 persona 的评审权重
- **Web 前端**：React SPA，提交方案、查看进度、浏览结果
- **单端口生产部署**：Flask 同时托管前端和 API，Docker 一键启动

## 当前未实现 / 不是

- 不是通用预测平台
- 不是交易平台，不发币，不上链
- 不做社会模拟 / 舆情推演
- 无用户认证（内部信任网络使用）
- 评审结果存文件系统，非数据库

## 快速开始

### 源码运行

```bash
# 1. 配置
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY

# 2. 安装依赖
cd backend && pip install -r requirements.txt

# 3. 启动
python run.py
# http://localhost:5001
```

### Docker 部署（推荐）

```bash
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY
docker compose up -d --build
# http://<服务器IP>:5001
```

详细部署说明见 [DEPLOY.md](./DEPLOY.md)。

### 最小试用

```bash
# 健康检查
curl http://localhost:5001/health

# 提交评审
curl -X POST http://localhost:5001/api/campaign/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "campaigns": [
      {"name": "方案A", "core_message": "自然美瞳日抛新体验", "product_line": "colored_lenses"},
      {"name": "方案B", "core_message": "硅水凝胶透氧黑科技", "product_line": "moodyplus"}
    ]
  }'

# 查询状态
curl http://localhost:5001/api/campaign/evaluate/status/<task_id>

# 获取结果
curl http://localhost:5001/api/campaign/result/<set_id>
```

完整 API 流程见 [backend/QUICKSTART.md](./backend/QUICKSTART.md)。

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `LLM_API_KEY` | 是 | LLM API 密钥 |
| `LLM_BASE_URL` | 否 | OpenAI 兼容接口地址（默认 OpenAI） |
| `LLM_MODEL_NAME` | 否 | 模型名（默认 gpt-4o-mini） |
| `SECRET_KEY` | 建议 | Flask session 密钥 |

## 技术栈

- **后端**：Python 3.11+ / Flask / Gunicorn
- **前端**：React + Vite + TypeScript
- **部署**：Docker multi-stage build，单端口 5001
- **LLM**：OpenAI 兼容接口（百炼/千问/OpenAI 均可）

## 项目结构

```
backend/
  app/
    api/campaign.py      # API 路由
    services/            # 评分、校准、概率聚合
    models/              # 数据模型
    utils/               # LLM 客户端、重试、日志
  tests/                 # pytest 测试
  run.py                 # 开发启动入口
frontend/                # React SPA
Dockerfile               # 多阶段构建
docker-compose.yml       # 生产部署
```
