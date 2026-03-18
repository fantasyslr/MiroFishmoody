# Phase 18: Deployment Fix - Context

**Gathered:** 2026-03-18
**Status:** Ready for planning
**Source:** Autonomous smart discuss (infrastructure phase)

<domain>
## Phase Boundary

修复生产入口 404（`__init__.py` 静态路由静默失败），Dockerfile 构建断言，Railway 部署配置（volume + env），健康检查双重验证。

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase. Key constraints from research:
- 404 根因：`__init__.py` 中 `os.path.isdir(dist)` 返回 False 时整个静态路由块被跳过，无日志
- 修复：加 `logger.warning` + 503 fallback 路由（而非静默 404）
- Dockerfile：`RUN test -f frontend/dist/index.html` 断言
- Railway：volume 挂载路径必须精确匹配 `Config.UPLOAD_FOLDER`（`/app/backend/uploads`）
- Railway PORT env var：gunicorn 启动命令需读取 PORT 环境变量
- 健康检查：`/api/health` 增加 `uploads_writable` 检查

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `backend/app/__init__.py` — Flask app factory，静态文件托管逻辑
- `Dockerfile` — 多阶段构建，frontend build → backend serve
- `docker-compose.yml` — 现有 volume 映射参考
- `backend/app/config.py` — UPLOAD_FOLDER 配置

### Integration Points
- `__init__.py` create_app() — 静态路由注册
- Dockerfile build stage — dist 产物验证
- Railway dashboard — env var + volume 配置

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase

</specifics>

<deferred>
## Deferred Ideas

None

</deferred>
