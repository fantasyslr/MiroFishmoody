---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: 大改造
status: planning
stopped_at: Completed 17-02-PLAN.md
last_updated: "2026-03-18T05:40:10.783Z"
last_activity: 2026-03-18 — Roadmap created, v2.0 phases 13-17 defined
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 13
  completed_plans: 13
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-18)

**Core value:** 让每一次 campaign 在上线前都能得到数据化的推演对比，用 AI 推演替代"拍脑袋"决策
**Current focus:** Phase 13 — Critical Bug Fixes + API Contract Lock

## Current Position

Phase: 13 of 17 (Critical Bug Fixes + API Contract Lock)
Plan: — (not yet planned)
Status: Ready to plan
Last activity: 2026-03-18 — Roadmap created, v2.0 phases 13-17 defined

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity (v1.0 + v1.1 history):**
- Total plans completed: 20 (v1.0: 12, v1.1: 8)
- Average duration: ~2.7 min
- Total execution time: ~54 min

**By Phase (v1.1):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| Phase 09 P01 | 1 | 1min | 1min |
| Phase 09 P02 | 1 | 1min | 1min |
| Phase 10 P01 | 1 | 4min | 4min |
| Phase 10 P02 | 1 | 2min | 2min |
| Phase 11 P01 | 1 | 3min | 3min |
| Phase 11 P02 | 1 | 3min | 3min |
| Phase 12 P01 | 1 | 5min | 5min |
| Phase 12 P02 | 1 | 2min | 2min |

**Recent Trend:**
- Last 5 plans: 3min, 3min, 5min, 2min, 2min
- Trend: Stable

*Updated after each plan completion*
| Phase 13 P01 | 4min | 2 tasks | 3 files |
| Phase 13-critical-bug-fixes-api-contract-lock P02 | 3min | 2 tasks | 3 files |
| Phase 14-frontend-rewrite-core-pages P02 | 5min | 2 tasks | 2 files |
| Phase 14-frontend-rewrite-core-pages P04 | 3min | 1 tasks | 1 files |
| Phase 14-frontend-rewrite-core-pages P01 | 3min | 2 tasks | 2 files |
| Phase 14-frontend-rewrite-core-pages P03 | 3min | 2 tasks | 5 files |
| Phase 15-multi-agent-foundation P01 | 8min | 2 tasks | 4 files |
| Phase 15-multi-agent-foundation P02 | 3min | 2 tasks | 4 files |
| Phase 16-multi-agent-evaluation-enhancement P02 | 3min | 2 tasks | 3 files |
| Phase 16-multi-agent-evaluation-enhancement P01 | 7min | 2 tasks | 5 files |
| Phase 16-multi-agent-evaluation-enhancement P03 | 2min | 2 tasks | 3 files |
| Phase 17-tech-debt-paydown P01 | 4min | 2 tasks | 2 files |
| Phase 17-tech-debt-paydown P02 | 2min | 2 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Phase 12]: Trends endpoint scans all result JSON files on each request (no caching, acceptable for MVP scale)
- [Phase 11]: Client-side PDF/PNG export via html2canvas + jsPDF, 2x retina scale
- [Phase 10]: Lock scopes minimal — only dict ops under lock, no I/O or LLM calls
- [v2.0 Roadmap]: lib/api.ts MUST NOT change during frontend rewrite — contracts.ts is the safety layer
- [v2.0 Roadmap]: Global LLMSemaphore at LLMClient level (not per-service) — Phase 15 pre-condition for all new agent types
- [Phase 13]: 新增 _parse_evaluate_campaigns() 而非修改 _parse_campaigns()，保持 /race 路径不受影响
- [Phase 13-02]: Both mode evaluate uses try/finally so navigate fires even if evaluate POST fails — Race path remains available
- [Phase 13-02]: contracts.ts frozen at 2026-03-18 — page components import API types from contracts.ts not api.ts directly; lib/api.ts must NOT be modified
- [Phase 14-02]: Cross-path conflict badges use try/catch for defensive cross-state reads; ResultPage badge gated on evalStatus=completed to prevent premature display
- [Phase 14-frontend-rewrite-core-pages]: PDF pagination via canvas slicing (drawImage with source offsets) — more compatible than negative-y single image approach
- [Phase 14-frontend-rewrite-core-pages]: 0.5mm trailing-page tolerance prevents float arithmetic adding a near-empty last PDF page
- [Phase 14]: loadHomeForm() called synchronously in component body (not useEffect) — useState initializer gets restored value without a flash of default state
- [Phase 14]: persistForm() spread-override pattern: each onChange passes only changed field, rest read from closure state
- [Phase 14-03]: LogBuffer is display-only — parent owns log state and appending logic
- [Phase 14-03]: Race path uses fixed RACE_CURRENT_STEP=1 (synchronous, no polling)
- [Phase 15-multi-agent-foundation]: Global LLMSemaphore at LLMClient level (not per-service) — Phase 15-01 delivers unified concurrency cap for all agent types
- [Phase 15-multi-agent-foundation]: AgentScore.score normalized to 0-1 by agent itself; AGENT_SCORE_WEIGHT=0.1 keeps agent influence modest; Phase 16 agents pass List[AgentScore] to scorer.score() without modifying scorer internals
- [Phase 16-multi-agent-evaluation-enhancement]: stdev_threshold=2.0 matches controversy badge threshold; suspect flag absent for clean scores (no False written); single-persona campaigns skip detection silently
- [Phase 16-multi-agent-evaluation-enhancement]: MultiJudgeEnsemble is PairwiseJudge subclass — inherits Bradley-Terry and evaluate_all() without duplication; all normalized votes in PairwiseResult.votes with position field
- [Phase 16-multi-agent-evaluation-enhancement]: EvaluationOrchestrator default judge switched to MultiJudgeEnsemble (USE_MARKET_JUDGE flag path unchanged)
- [Phase 16-multi-agent-evaluation-enhancement]: DEVIL_ADVOCATE_PERSPECTIVE separate from JUDGE_PERSPECTIVES; dissent flag in judge_pair() return; isControversial() pure frontend combining suspect+dissent; MultiJudgeEnsemble._perspectives includes 4 judge types
- [Phase 17-tech-debt-paydown]: TD-01 annotation pattern: comment-only enforcement with # TD-01 prefix, no logic changes required; step 1/step 2 separation in EvaluationOrchestrator makes lock/IO boundary explicit
- [Phase 17-tech-debt-paydown]: BacktestEngine receives engine instance via __init__ to reuse compute_intervention_impact and _inject_competitor_delta without copying them; lazy import inside method body prevents circular import

### Pending Todos

None yet.

### Blockers/Concerns

- BUG-05 (silent image dropout): All current Evaluate results are partially blind — AudiencePanel/PairwiseJudge calling os.path.exists() on API URLs. Must fix in Phase 13 before any backend work.
- Phase 15 research flag: Bailian account tier RPM/TPM limits should be verified before setting MAX_LLM_CONCURRENT default.
- Phase 16 research flag: CrossAgentValidator debate-round cost — validate variance threshold against real campaign data before enabling in production.

## Session Continuity

Last session: 2026-03-18T05:25:57.976Z
Stopped at: Completed 17-02-PLAN.md
Resume file: None
