---
phase: 18-deployment-fix
plan: 01
subsystem: infra
tags: [flask, docker, railway, health-check, static-serving]

# Dependency graph
requires: []
provides:
  - Flask / route: 503 fallback when frontend dist is missing (prevents silent 404)
  - Flask / route: /api/health endpoint (Railway-compatible health check)
  - Flask / startup: dist absolute path + existence logged at startup
  - Dockerfile / build: assertion that frontend/dist/index.html exists before image finalizes
affects:
  - 18-railway-config
  - all phases requiring live deployment verification

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "503 fallback route registered in else-branch when dist dir absent"
    - "Health check on /api/health (not /health) per Railway convention"
    - "Build-time assertion via RUN test -f to catch empty Vite output early"

key-files:
  created: []
  modified:
    - backend/app/__init__.py
    - Dockerfile

key-decisions:
  - "Route named /api/health (not /health) — consistent with CORS /api/* wildcard and Railway health check path convention"
  - "503 fallback uses named function serve_frontend_fallback to avoid route name collision with serve_frontend in the if-branch"
  - "Dockerfile assertion placed immediately after COPY dist — fail fast, fail clearly"

patterns-established:
  - "Dual-defense: build-time assertion (Dockerfile) + runtime fallback (Flask 503)"

requirements-completed: [DEPLOY-01, DEPLOY-02, DEPLOY-04]

# Metrics
duration: 5min
completed: 2026-03-18
---

# Phase 18 Plan 01: Deployment Fix Summary

**Flask 503 fallback + /api/health route + Dockerfile build assertion to replace silent 404 on missing dist**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-18T00:00:00Z
- **Completed:** 2026-03-18
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `/` 路由在 dist 缺失时返回 503（JSON 含 dist_path），不再静默 404
- `/api/health` 路由替换原 `/health`，与 Railway 健康检查约定一致
- 启动日志输出 dist 绝对路径及 exists 状态
- Dockerfile 在 COPY dist 之后立即断言 index.html 存在，构建期拦截空白产物

## Task Commits

1. **Task 1: Flask 静态路由修复** - `0ea94fd` (fix)
2. **Task 2: Dockerfile 构建断言** - `7d26b67` (fix)

## Files Created/Modified

- `backend/app/__init__.py` - 添加 startup log、503 fallback 路由、/api/health 路由替换
- `Dockerfile` - 添加 RUN test -f 构建断言

## Decisions Made

- `/api/health` 而非 `/health`：与现有 CORS `r"/api/*"` 规则一致，Railway 健康检查配置只需指向 `/api/health`
- `serve_frontend_fallback` 函数名：避免与 if-branch 的 `serve_frontend` 在同一 app 作用域内重名

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 部署防线已就绪：Railway 可通过 `/api/health` 轮询，dist 缺失时 `/` 返回 503 而非 404
- 下一步：Phase 18 其余计划（Railway 环境变量、volume mount 路径、PORT 注入处理）

---
*Phase: 18-deployment-fix*
*Completed: 2026-03-18*
