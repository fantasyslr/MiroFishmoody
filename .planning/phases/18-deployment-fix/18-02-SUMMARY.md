---
phase: 18-deployment-fix
plan: 02
subsystem: infra
tags: [railway, docker, gunicorn, healthcheck, deployment]

# Dependency graph
requires:
  - phase: 18-01
    provides: /api/health route on /app/backend/app/api/health.py
provides:
  - Dockerfile with dynamic PORT binding via ${PORT:-5001} shell form CMD
  - railway.json with DOCKERFILE builder, /api/health healthcheck, ON_FAILURE restart policy
affects: [18-03, railway-deployment]

# Tech tracking
tech-stack:
  added: [railway.json]
  patterns: [shell-form-CMD-for-env-expansion, railway-healthcheck-convention]

key-files:
  created: [railway.json]
  modified: [Dockerfile]

key-decisions:
  - "Dockerfile CMD 从 exec form 改为 shell form，使 ${PORT:-5001} 能被 /bin/sh -c 展开"
  - "railway.json 不配置 volume mount（Railway Dashboard 不支持该字段），volume 需在 Dashboard 手动设置"
  - "healthcheckPath 使用 /api/health（与 18-01 路由迁移保持一致，且在 CORS /api/* 覆盖范围内）"

patterns-established:
  - "Shell form CMD pattern: 需要 env var 展开时必须用 shell form，不能用 exec form 数组"
  - "Railway volume 配置: 只能通过 Dashboard/CLI 配置，不能写入 railway.json"

requirements-completed: [DEPLOY-03, DEPLOY-04]

# Metrics
duration: 2min
completed: 2026-03-18
---

# Phase 18 Plan 02: Deployment Infrastructure Summary

**Dockerfile CMD 改为 shell form 动态绑定 PORT，railway.json 建立 DOCKERFILE builder + /api/health healthcheck + ON_FAILURE 重启策略**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-18T06:26:14Z
- **Completed:** 2026-03-18T06:27:45Z
- **Tasks:** 3 of 3 complete (Task 3 checkpoint:human-action approved — Railway deployment verified)
- **Files modified:** 2

## Accomplishments
- Dockerfile CMD 从 exec form 改为 shell form，`${PORT:-5001}` 在 Railway 注入 PORT 时自动使用，本地 fallback 5001
- 新建 railway.json，声明 DOCKERFILE builder、/api/health healthcheck（300s timeout）、ON_FAILURE 重启（最多 3 次）
- 消除 Railway PORT mismatch（gunicorn 不再硬编码 5001，Railway 代理 8080 可正常转发）

## Task Commits

1. **Task 1: Dockerfile CMD 改为 shell form** - `f365f07` (feat)
2. **Task 2: 创建 railway.json** - `934ee22` (feat)
3. **Task 3: Railway Dashboard 手动配置** - APPROVED (checkpoint:human-action — `/ → 200`, `/api/health → uploads_writable: ok`)

## Files Created/Modified
- `Dockerfile` — CMD 从 exec form 改为 shell form，`--bind "0.0.0.0:${PORT:-5001}"`
- `railway.json` — 新建 Railway 配置，builder=DOCKERFILE，healthcheckPath=/api/health

## Decisions Made
- exec form 不能展开 shell 变量（`$PORT`），必须使用 shell form（`/bin/sh -c` 执行），这是 Docker 的固有限制
- railway.json 的 `deploy` 块不支持 `volumes` 字段，volume mount 只能通过 Railway Dashboard 配置
- healthcheckTimeout 设为 300s，与 gunicorn --timeout 保持一致，避免 LLM 调用超时导致假性 unhealthy

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

**Task 3 (checkpoint:human-action) 需要手动完成 Railway Dashboard 配置：**

按顺序：
1. 访问 https://railway.com → 新建项目 → Deploy from GitHub repo → 选择 MiroFishmoody
2. 服务设置 → Volumes → Add Volume → Mount Path: `/app/backend/uploads`
3. 服务设置 → Variables → 添加：
   - `LLM_API_KEY` = [Bailian API key]
   - `LLM_BASE_URL` = `https://dashscope.aliyuncs.com/compatible-mode/v1`
   - `LLM_MODEL_NAME` = `qwen-vl-max`
   - `SECRET_KEY` = [随机 32 字符，如 `openssl rand -hex 16`]
   - `FLASK_DEBUG` = `false`
4. Push 当前分支或手动触发 Redeploy
5. 验证：`curl -s https://<railway-url>/api/health` 返回 `uploads_writable: ok`

## Next Phase Readiness
- 部署完全就绪：Dockerfile + railway.json 代码侧配置 + Railway Dashboard volume/env vars 全部完成
- 生产验证通过：`/` 返回 200，`/api/health` 返回 `uploads_writable: ok`
- Phase 18-02 fully complete — 可继续 Phase 19

---
*Phase: 18-deployment-fix*
*Completed: 2026-03-18*
