# MiroFishmoody Backend Quickstart

这份文档只讲后端最短启动路径。  
如果你想看完整操作流程，优先读 [使用教程](../docs/USAGE_GUIDE.md)。

## 1. 安装依赖

推荐使用 `uv`：

```bash
cd backend
uv sync
```

如果你不用 `uv`：

```bash
cd backend
pip install -r requirements.txt
pip install pytest
```

## 2. 准备环境变量

在项目根目录创建 `.env`：

```bash
cd ..
cp .env.example .env
```

至少配置以下变量：

```env
LLM_API_KEY=your-api-key
SECRET_KEY=replace-with-a-random-string
MOODY_USERS=admin:StrongPassword123:Admin:admin
```

说明：

- `LLM_API_KEY` 不填，后端启动时会直接报错退出
- `MOODY_USERS` 是登录用户表，不再写死在代码里
- `SECRET_KEY` 用于 Flask Session，生产环境必须替换

## 3. 启动后端

使用 `uv`：

```bash
cd backend
uv run python run.py
```

或使用系统 Python：

```bash
cd backend
python3 run.py
```

默认地址：<http://localhost:5001>

## 4. 健康检查

```bash
curl http://localhost:5001/health
```

健康检查会返回：

- `status`
- `db`
- `uploads_writable`
- `disk_free_gb`

`status=ok` 表示基本可用；`status=degraded` 说明数据库、上传目录或磁盘存在问题。

## 5. 登录验证

```bash
curl -c cookies.txt -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"StrongPassword123"}'
```

## 6. Brandiction 最小烟测

运行一轮最小 race：

```bash
curl -b cookies.txt -X POST http://localhost:5001/api/brandiction/race \
  -H "Content-Type: application/json" \
  -d '{
    "product_line": "moodyplus",
    "audience_segment": "general",
    "market": "cn",
    "sort_by": "roas_mean",
    "include_hypothesis": true,
    "plans": [
      {
        "name": "Science Plan",
        "theme": "science_credibility",
        "platform": "redbook",
        "channel_family": "social_seed",
        "budget": 50000,
        "market": "cn"
      },
      {
        "name": "Comfort Plan",
        "theme": "comfort_beauty",
        "platform": "douyin",
        "channel_family": "short_video",
        "budget": 50000,
        "market": "cn"
      }
    ]
  }'
```

查看历史记录：

```bash
curl -b cookies.txt http://localhost:5001/api/brandiction/race-history
```

## 7. Campaign Evaluation 最小烟测

提交一轮异步评审：

```bash
curl -b cookies.txt -X POST http://localhost:5001/api/campaign/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "campaigns": [
      {
        "name": "方案 A",
        "core_message": "自然美瞳日抛新体验",
        "product_line": "colored_lenses"
      },
      {
        "name": "方案 B",
        "core_message": "硅水凝胶透氧黑科技",
        "product_line": "moodyplus"
      }
    ]
  }'
```

返回值里会有 `task_id` 和 `set_id`。

轮询状态：

```bash
curl -b cookies.txt http://localhost:5001/api/campaign/evaluate/status/<task_id>
```

获取结果：

```bash
curl -b cookies.txt http://localhost:5001/api/campaign/result/<set_id>
```

导出 JSON：

```bash
curl -b cookies.txt -OJ http://localhost:5001/api/campaign/export/<set_id>
```

## 8. 运行测试

```bash
cd backend
uv run pytest tests -q
```

如果只想先看 Brandiction 排序链路：

```bash
cd backend
uv run pytest tests/test_v3_baseline_ranker.py -q
```
