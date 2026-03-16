# MiroFishmoody — 部署说明

## 前提

- 服务器有 Docker + Docker Compose
- 有一个可用的 LLM API Key（百炼/千问/OpenAI 兼容接口均可）
- 已准备至少一个登录账号（通过 `MOODY_USERS` 配置）

## 1. 配置 .env

```bash
cp .env.example .env
```

编辑 `.env`，填入真实配置：

```env
LLM_API_KEY=sk-xxxxx
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus
SECRET_KEY=随便写一串随机字符串
MOODY_USERS=admin:StrongPassword123:Admin:admin
```

> `FLASK_DEBUG` 已在 `.env.example` 中默认设为 `False`，不需要额外改。
> `SECRET_KEY` 生产环境必须替换成随机值。
> `MOODY_USERS` 是当前登录入口的唯一用户来源，不配置则无法登录。

## 2. 构建并启动

```bash
docker compose up -d --build
```

## 3. 验证

```bash
# 检查容器健康状态（docker-compose.yml 已配置 healthcheck）
docker compose ps

# 手动验证
curl http://localhost:5001/health
# 预期返回中至少包含 status / db / uploads_writable / disk_free_gb
```

浏览器打开 `http://<服务器IP>:5001` 即可使用前端页面。

## 4. 查看日志

```bash
docker compose logs -f
```

## 5. 停止

```bash
docker compose down
```

## 无 Docker 部署（备选）

```bash
cd frontend && npm ci && npm run build && cd ..
cd backend && pip install -r requirements.txt
# 确保项目根目录有 .env
gunicorn --chdir backend --bind 0.0.0.0:5001 --workers 2 --threads 4 --timeout 300 "app:create_app()"
```

## 必须配置的环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `LLM_API_KEY` | LLM API 密钥（必填） | `sk-xxxxx` |
| `LLM_BASE_URL` | OpenAI 兼容接口地址 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `LLM_MODEL_NAME` | 模型名 | `qwen-plus` |
| `SECRET_KEY` | Flask session 密钥（必填） | 任意随机字符串 |
| `MOODY_USERS` | 登录用户表 | `admin:StrongPassword123:Admin:admin` |
