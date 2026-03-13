# Moody Campaign Choice Engine — 后端快速试用

## 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
pip install pytest  # 可选，跑测试用
```

## 2. 配置 .env

```bash
cp .env.example .env
# 编辑 .env，填入真实的 LLM_API_KEY
# 支持任何 OpenAI 兼容 API，改 LLM_BASE_URL 和 LLM_MODEL_NAME 即可
```

## 3. 启动

```bash
cd backend
python run.py
# 默认 http://0.0.0.0:5001
```

## 4. 健康检查

```bash
curl http://localhost:5001/health
# {"service":"Campaign Ranker Engine","status":"ok"}
```

## 5. 最小试用流程

### 提交评审（异步）

```bash
curl -X POST http://localhost:5001/api/campaign/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "campaigns": [
      {"name": "方案A", "core_message": "自然美瞳日抛新体验", "product_line": "colored_lenses"},
      {"name": "方案B", "core_message": "硅水凝胶透氧黑科技", "product_line": "moodyplus"}
    ]
  }'
# 返回 task_id 和 set_id
```

### 查询进度

```bash
curl http://localhost:5001/api/campaign/evaluate/status/<task_id>
# progress=100, status=completed 时可取结果
```

### 获取结果

```bash
curl http://localhost:5001/api/campaign/result/<set_id>
```

### 赛后结算（可选）

```bash
curl -X POST http://localhost:5001/api/campaign/resolve \
  -H "Content-Type: application/json" \
  -d '{"set_id": "<set_id>", "winner_campaign_id": "campaign_1", "actual_metrics": {"ctr": 0.03}}'
```

### 查看校准状态

```bash
curl http://localhost:5001/api/campaign/calibration
```

## 6. 跑测试

```bash
cd backend
python -m pytest tests -q
```
