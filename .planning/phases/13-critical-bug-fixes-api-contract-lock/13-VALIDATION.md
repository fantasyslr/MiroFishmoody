---
phase: 13
slug: critical-bug-fixes-api-contract-lock
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), TypeScript compiler (frontend) |
| **Config file** | `backend/pyproject.toml`, `frontend/tsconfig.json` |
| **Quick run command** | `cd backend && uv run pytest -x -q` |
| **Full suite command** | `cd backend && uv run pytest && cd ../frontend && npm run build` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest -x -q`
- **After every plan wave:** Run `cd backend && uv run pytest && cd ../frontend && npm run build`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | BUG-05 | integration | `cd backend && uv run pytest tests/ -k "evaluate"` | ❌ W0 | ⬜ pending |
| 13-02-01 | 02 | 1 | BUG-06 | build | `cd frontend && npm run build` | ✅ | ⬜ pending |
| 13-02-02 | 02 | 1 | BUG-07 | build | `cd frontend && npm run build` | ✅ | ⬜ pending |
| 13-02-03 | 02 | 1 | FE-08 | build | `cd frontend && npm run build` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Backend test for evaluate payload parsing — stubs for BUG-05
- [ ] `frontend/src/lib/contracts.ts` — type export file for FE-08

*Existing pytest infrastructure covers backend; frontend uses TypeScript compiler as validation.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Both mode两个 taskId 导航前存储 | BUG-06 | Requires browser interaction | Start Both mode, check store before navigation |
| RunningPage 进度 vs 后端一致 | BUG-07 | Requires running backend | Start Race, observe spinner vs actual completion |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
