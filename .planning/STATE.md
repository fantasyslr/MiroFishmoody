---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: 部署修复 + 评审偏差修正
status: active
stopped_at: null
last_updated: "2026-03-18"
last_activity: 2026-03-18 — Roadmap created, Phase 18 ready to plan
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 7
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-18)

**Core value:** 让每一次 campaign 在上线前都能得到数据化的推演对比，用 AI 推演替代"拍脑袋"决策
**Current focus:** Phase 18 — Deployment Fix

## Current Position

Phase: 18 of 20 (Deployment Fix)
Plan: —
Status: Ready to plan
Last activity: 2026-03-18 — v2.1 roadmap created (Phases 18-20), 12/12 requirements mapped

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity (cumulative):**
- Total plans completed: 33 (v1.0: 12, v1.1: 8, v2.0: 13)
- Average duration: ~3.3 min
- Total execution time: ~109 min

**Recent Trend (v2.0 last 5 plans):**
- 4min, 3min, 7min, 2min, 2min
- Trend: Stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v2.1 Research]: Railway volume mount MUST use `/app/backend/uploads` (matches Config.UPLOAD_FOLDER exactly); path mismatch is silent at runtime but destructive on restart
- [v2.1 Research]: `weight_profile_version` field in EvaluationResult is zero-cost at implementation, high-cost retroactively — must be added in Phase 19 before first weight profile ships
- [v2.1 Research]: Phase 19 must complete before Phase 20 benchmark labeling; labels captured against flat-weight evaluator are biased ground truth
- [v2.1 Research]: Railway may inject PORT env var; gunicorn start command must read PORT from env or Railway must expose 5001 explicitly — handle in Phase 18
- [Phase 17]: BacktestEngine receives engine instance via __init__ to reuse compute_intervention_impact; lazy import inside method body prevents circular import

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 18 pre-condition]: Production / returns 404 — no user-facing validation possible until Phase 18 ships. All v2.1 verification depends on deployment fix.
- [Phase 20 dependency]: Benchmark labeling requires brand team time (10 historical campaigns). Begin labeling during Phase 19 development to avoid blocking Phase 20.

## Session Continuity

Last session: 2026-03-18
Stopped at: v2.1 roadmap created — Phases 18-20 written to ROADMAP.md, STATE.md initialized
Resume file: None
