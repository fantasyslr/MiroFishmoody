# MiroFishmoody 使用教程

这份文档按“真正上手”的顺序写，覆盖两条日常使用路径：

- 路径 A：前端 Brandiction 赛马工作流
- 路径 B：后端 Campaign Evaluation API 工作流

如果你只是第一次跑项目，建议先看 [README](../README.md) 的“快速开始”，再回来按这里操作。

## 角色说明

| 角色 | 能做什么 |
|------|----------|
| `admin` | 登录、导入历史数据、查看 Dashboard、查看 Race History、执行 resolve、使用全部普通能力 |
| `user` | 登录、发起 race、查看结果、使用普通查询与评审接口 |

`MOODY_USERS` 示例：

```env
MOODY_USERS=admin:StrongPassword123:Admin:admin,analyst:StrongPassword123:Analyst:user
```

## 一、启动系统

### 本地开发

```bash
git clone https://github.com/fantasyslr/MiroFishmoody.git
cd MiroFishmoody
cp .env.example .env
```

编辑 `.env`，至少填入：

```env
LLM_API_KEY=your-api-key
SECRET_KEY=replace-with-a-random-string
MOODY_USERS=admin:StrongPassword123:Admin:admin
```

安装并启动：

```bash
npm run setup
npm run setup:backend
npm run dev
```

访问：

- 前端：<http://localhost:5173>
- 后端：<http://localhost:5001>

### Docker 启动

```bash
cp .env.example .env
docker compose up -d --build
```

访问：

- <http://localhost:5001>

## 二、登录

打开前端后直接输入 `MOODY_USERS` 里配置的用户名和密码。

登录后：

- 普通用户默认进入 `Campaign Lab`
- 管理员除首页外，还可以看到 Dashboard 和 History 入口

## 三、路径 A：Brandiction 前端赛马工作流

这是当前仓库最完整、最推荐的主路径。

### Step 1. 先准备历史数据

Brandiction 的排序核心依赖历史数据脊柱。管理员需要先导入数据，否则结果会大量走 cold start。

你有两种导入方式：

#### 方式 1：导入 JSON 历史数据

```bash
curl -c cookies.txt -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"StrongPassword123"}'

curl -b cookies.txt -X POST http://localhost:5001/api/brandiction/import-history \
  -H "Content-Type: application/json" \
  -d @history.json
```

支持的主对象：

- `interventions`
- `outcomes`
- `signals`
- `competitor_events`
- `evidence`

#### 方式 2：导入 CSV

导入 interventions：

```bash
curl -b cookies.txt -X POST \
  "http://localhost:5001/api/brandiction/import-csv?type=interventions&run_id=run_20260316" \
  -H "Content-Type: text/csv" \
  --data-binary @interventions.csv
```

导入 outcomes：

```bash
curl -b cookies.txt -X POST \
  "http://localhost:5001/api/brandiction/import-csv?type=outcomes" \
  -H "Content-Type: text/csv" \
  --data-binary @outcomes.csv
```

### Step 2. 检查数据是否真的进来了

管理员可以打开前端 Dashboard，也可以直接调用接口：

```bash
curl -b cookies.txt http://localhost:5001/api/brandiction/stats
```

重点看：

- `interventions_count`
- `outcomes_count`
- `market_coverage`
- `platform_coverage`
- `weakest_dimensions`

如果 `interventions_count` 和 `outcomes_count` 很低，结果页里的 `match_quality` 和 `cold_start_hint` 会更频繁出现。

### Step 3. 在首页发起一轮 race

登录后进入首页，依次配置：

- `Market Context`
- `Product Line`
- `Optimization Target`
- `Season Context`

然后填写 2 到 5 个策略方向，每个方向至少要有：

- `Plan Designation`
- `Cognitive Theme`
- `Primary Platform`
- `Channel Family`
- `Budget Allocation`

最后点击 `Initialize Race`。

### Step 4. 等待 Running 页面完成

Running 页面会轮询真实后端接口，不是假的进度条。

它会依次完成：

- Historical baseline 计算
- Perception model hypothesis 计算
- Recommendation 汇总

如果失败，会停留在错误页面并显示后端返回的错误信息。

### Step 5. 解读结果页

结果页分两条轨道：

#### Track 1：Observed Historical Baseline

这是当前真正驱动排名的主链。

重点看这些字段：

- `score`
- `sample_size`
- `match_quality`
- `match_dimensions`
- `roas_mean / purchase_rate / cpa / revenue_mean`
- `drift_30d`
- `seasonal_drift`
- `cold_start_hint`

如何理解：

- `sample_size` 越高，说明相似历史案例越多
- `match_quality=exact/partial/fallback` 表示匹配颗粒度
- `cross_category` 说明已经借用了跨品类迁移
- `cold_start` 说明相似历史不足，只能给出分位数估计
- `seasonal_drift` 会对比当前季节和 `regular` 样本

#### Track 2：Perception Model Hypothesis

这部分提供解释和风险提示，不直接改排名。

重点看：

- `reasoning`
- `confidence`
- `similar_interventions`
- `predicted_delta`

建议把它当成：

- “为什么这个方向可能成立”
- “潜在的感知变化”

而不是把它当成最终拍板依据。

### Step 6. 查看历史记录与赛后结算

管理员可以进入：

- `Data Spine Overview`
- `Resolution Dossier`

如果要走 API resolve：

```bash
curl -b cookies.txt -X POST \
  http://localhost:5001/api/brandiction/race-history/race_20260316_123456/resolve \
  -H "Content-Type: application/json" \
  -d '{"status":"verified","hit":true}'
```

这一步的作用是把“模型当时的建议”和“真实世界是否命中”留在历史里，方便后续校准。

## 四、路径 B：Campaign Evaluation API 工作流

这条路径更像传统的“提交方案 -> 异步评审 -> 导出结果”流程，当前主要通过 API 使用。

### Step 1. 登录

```bash
curl -c cookies.txt -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"StrongPassword123"}'
```

### Step 2. 可选：先解析 brief

```bash
curl -b cookies.txt -X POST http://localhost:5001/api/campaign/parse-brief \
  -H "Content-Type: application/json" \
  -d '{
    "brief_text": "我们想做一轮强调硅水凝胶透氧科技的春季投放",
    "product_line": "moodyplus"
  }'
```

### Step 3. 可选：上传素材图

```bash
curl -b cookies.txt -X POST http://localhost:5001/api/campaign/upload-image \
  -F "file=@./creative-a.png" \
  -F "set_id=set_demo_001" \
  -F "campaign_id=campaign_1"
```

返回值里会包含：

- `image_id`
- `url`
- `size`

### Step 4. 提交异步评审

```bash
curl -b cookies.txt -X POST http://localhost:5001/api/campaign/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "set_id": "set_demo_001",
    "context": "春季重点 campaign，目标提高加购和转化",
    "campaigns": [
      {
        "id": "campaign_1",
        "name": "方案 A",
        "product_line": "moodyplus",
        "core_message": "硅水凝胶透氧黑科技",
        "target_audience": "长期佩戴隐形眼镜的上班族",
        "channels": ["redbook", "douyin"],
        "creative_direction": "白底实验室感 KV",
        "image_paths": []
      },
      {
        "id": "campaign_2",
        "name": "方案 B",
        "product_line": "moodyplus",
        "core_message": "舒服到忘记自己戴了隐形",
        "target_audience": "注重舒适感的日常用户",
        "channels": ["redbook", "bilibili"],
        "creative_direction": "生活化场景短视频",
        "image_paths": []
      }
    ]
  }'
```

会返回：

- `task_id`
- `set_id`

### Step 5. 轮询任务状态

```bash
curl -b cookies.txt \
  http://localhost:5001/api/campaign/evaluate/status/<task_id>
```

直到返回 `status=completed`。

### Step 6. 拉取结果和导出

获取结果：

```bash
curl -b cookies.txt \
  http://localhost:5001/api/campaign/result/set_demo_001
```

导出 JSON：

```bash
curl -b cookies.txt -OJ \
  http://localhost:5001/api/campaign/export/set_demo_001
```

### Step 7. 赛后结算与校准

```bash
curl -b cookies.txt -X POST http://localhost:5001/api/campaign/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "set_id": "set_demo_001",
    "winner_campaign_id": "campaign_1",
    "actual_metrics": {
      "ctr": 0.031,
      "cvr": 0.022
    },
    "notes": "方案 A 实际赢下 CTR 和 CVR"
  }'
```

查看校准状态：

```bash
curl -b cookies.txt http://localhost:5001/api/campaign/calibration
```

## 五、常见问题

### 1. 前端打开后一直回到登录页

优先检查：

- `.env` 里是否配置了 `MOODY_USERS`
- `SECRET_KEY` 是否为空
- 浏览器是否允许本地 cookie

### 2. 后端起不来，提示配置错误

后端启动前会校验 `LLM_API_KEY`。没填的话会直接退出。

### 3. 为什么结果里很多 `cold_start`

通常是因为：

- 历史 interventions / outcomes 太少
- 当前 `market / product_line / audience_segment` 太稀疏
- 输入的 `platform / channel_family / theme / landing_page` 和历史差异太大

### 4. 为什么管理员才看得到 Dashboard / History

这是当前前端的角色约束：

- 普通用户专注 race 发起和结果查看
- 管理员负责导数、数据质量和赛后结算

### 5. 我只想验证服务是否正常

可以先做最小检查：

```bash
curl http://localhost:5001/health
```

再做登录检查：

```bash
curl -c cookies.txt -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"StrongPassword123"}'
```

## 六、推荐的团队使用节奏

如果你要把这套系统放进团队日常，我建议按这个节奏：

1. 管理员每周补一次历史数据
2. 方案会前先跑一轮 Brandiction race
3. 预算讨论以 Track 1 为主，Track 2 做解释
4. 上线后一周内做一次 resolve
5. 每月看一次 Dashboard 和 calibration，确认数据脊柱是否在变稀

这样系统才不会变成“只在演示时打开，平时没人维护”的工具。
