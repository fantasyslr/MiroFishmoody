---
phase: quick
plan: 260318-nwv
subsystem: backend/health
tags: [health-check, llm-probe, smoke-test, gunicorn]
dependency_graph:
  requires: []
  provides: ["/api/health with llm field", "aligned smoke test routes", "gunicorn dep"]
  affects: ["backend/app/__init__.py", "backend/tests/test_smoke.py", "backend/tests/e2e_smoke.py", "backend/pyproject.toml"]
tech_stack:
  added: ["gunicorn>=21.0.0"]
  patterns: ["lazy import inside function body for LLM probe"]
key_files:
  modified:
    - backend/app/__init__.py
    - backend/tests/test_smoke.py
    - backend/tests/e2e_smoke.py
    - backend/pyproject.toml
decisions:
  - "LLM probe uses lazy import (from openai import OpenAI as _OpenAI) consistent with existing sqlite3 lazy import pattern"
  - "getattr(Config, 'OPENAI_MODEL', 'qwen-plus') fallback avoids AttributeError if Config lacks OPENAI_MODEL"
  - "llm probe failure degrades overall to 'degraded' via existing all() logic, no special casing needed"
metrics:
  duration: "4 min"
  completed: "2026-03-18"
  tasks_completed: 2
  files_changed: 4
---

# Phase quick Plan 260318-nwv: LLM Health Probe + Smoke Test Route Fix Summary

**One-liner:** Added openai SDK LLM connectivity probe to /api/health, aligned smoke test routes from /health to /api/health, and added gunicorn to production dependencies.

## What Was Done

### Task 1 — /api/health LLM 连通性探测 (commit: ee2885b)

Inserted LLM probe block in `health()` after disk check, before return:

- Instantiates `OpenAI` client with `Config.OPENAI_API_KEY` / `Config.OPENAI_BASE_URL`
- Sends `chat.completions.create(max_tokens=1, timeout=10)` with "ping" message
- On success: `checks["llm"] = "ok"`
- On any exception: `checks["llm"] = f"error: {_e}"`
- Existing `overall` logic automatically degrades to `"degraded"` when llm value is not "ok"

### Task 2 — 路由对齐 + gunicorn 依赖 (commit: a791ef9)

- `test_smoke.py` L170: `client.get('/health')` → `client.get('/api/health')`, added `assert "llm" in data`
- `e2e_smoke.py` L33: `api("GET", "/health")` → `api("GET", "/api/health")`
- `pyproject.toml`: added `"gunicorn>=21.0.0"` to `dependencies`

## Verification

```
uv run pytest tests/test_smoke.py -x -q
20 passed in 4.10s
```

## Deviations from Plan

**1. [Rule 2 - Missing functionality] Added llm key assertion to TestHealth**

- Found during: Task 2
- Issue: Plan only said to change the route path; TestHealth had no assertion for the new `llm` field
- Fix: Added `assert "llm" in data` to TestHealth to verify the LLM probe integration end-to-end
- Files modified: backend/tests/test_smoke.py
- Commit: a791ef9

## Self-Check

Files exist:
- backend/app/__init__.py — modified, contains "llm" key
- backend/tests/test_smoke.py — modified, contains "/api/health"
- backend/tests/e2e_smoke.py — modified, contains "/api/health"
- backend/pyproject.toml — modified, contains "gunicorn"

Commits:
- ee2885b — feat(260318-nwv): add LLM connectivity probe to /api/health
- a791ef9 — fix(260318-nwv): align smoke test routes + add gunicorn dependency

## Self-Check: PASSED
