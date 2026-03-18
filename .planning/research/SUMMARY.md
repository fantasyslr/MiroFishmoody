# Project Research Summary

**Project:** MiroFishmoody v2.0 — Frontend Rewrite + Multi-Agent Backend Enhancement
**Domain:** Brand campaign pre-testing / 推演 engine (internal tool, LLM-based multimodal evaluation)
**Researched:** 2026-03-18
**Confidence:** HIGH

## Executive Summary

MiroFishmoody is a mature internal tool (v1.1 already ships race ranking, persona panel scoring, pairwise comparison, BT-model ranking, export, versioning, and trends) that needs two targeted upgrades: (1) a frontend interaction rewrite to fix known UX bugs and adopt cleaner patterns from the MiroFish reference codebase, and (2) a multi-agent backend enhancement that increases evaluation signal quality. This is not a greenfield build — the Flask + React + SQLite architecture is correct for the scale, and no new dependencies are needed. The rewrite is entirely additive: `lib/api.ts` and all backend route contracts remain frozen; only page components and orchestrator internals change.

The recommended approach is strictly sequential and dependency-aware. Frontend interaction bugs (form state loss, fake polling progress, Both mode race condition) must be fixed first because they block real usage without touching the backend. Multi-agent enhancements (expanded persona pool, devil's advocate judge, cross-persona disagreement surfacing) layer on top of a stable frontend. The architecture research confirms that EvaluationOrchestrator already accepts the new phases as additive inserts, AgentDiffusion already exists as a service, and MultiJudge / CrossAgentValidator can be written as standalone classes wired in through existing DI patterns.

The top risks are: (a) silent image dropout in AudiencePanel and PairwiseJudge — images are not currently resolved from API URL paths, making all visual evaluation effectively blind; this must be fixed before any other backend work; (b) API contract drift during the frontend rewrite, where MiroFish naming conventions get copied verbatim instead of mapped to Flask's snake_case contracts; and (c) missing global LLM semaphore in the multi-agent backend, where each new agent type spawns its own executor without a shared concurrency ceiling, causing 429 rate-limit failures at production campaign counts.

## Key Findings

### Recommended Stack

The existing stack requires zero new dependencies for v2.0. All MiroFish frontend UX patterns (step indicator, split-panel animation, polling, log buffer) are achievable with already-installed React 19 + Tailwind + motion 12.x. Multi-agent backend patterns use Python stdlib only (ThreadPoolExecutor, threading.Semaphore, statistics.stdev). The only config file changes needed are: font family additions to `tailwind.config.js`, Google Fonts link tags in `index.html`, and `MAX_LLM_CONCURRENT` added to `backend/app/config.py`.

**Core technologies:**
- React 19 + TypeScript 5.9 + Tailwind 3.4 + Vite 8: frontend — stable, no changes
- motion 12.x: split-panel animations — use `animate={{ width }}` with cubic-bezier `[0.4, 0, 0.2, 1]` matching MiroFish reference
- Flask 3.0 + SQLite WAL + ThreadPoolExecutor: backend — correct for internal tool at <10 concurrent users; never justify Celery/Redis
- Python `statistics` stdlib: ConsensusAgent outlier detection — `statistics.stdev` sufficient for ≤9 persona values; no scipy needed
- openai SDK (Bailian endpoint): all LLM calls — single provider; LiteLLM adds zero value here

**Explicitly do NOT add:** Vue.js, D3.js, WebSocket/Flask-SocketIO, Celery+Redis, LangChain/LangGraph, Zep Cloud, scipy/numpy, axios (frontend), LiteLLM.

### Expected Features

**Must have (table stakes — Phase 1, frontend-only, no backend deps):**
- Form state persistence across navigation — sessionStorage save/restore; current `useState` initializes fresh on every mount, causing data loss on navigation
- Honest polling progress on Evaluate path — add timeout + error recovery; RunningPage currently uses fake step animation with no real backend signal
- Both mode cross-path consistency badge — zero backend work; Race result and Evaluate result are both already stored, just need frontend comparison UI
- Winner-first result layout — restructure EvaluateResultPage so top campaign is visible without tab navigation
- Export reliability — test and fix html2canvas PDF generation on full 5-plan result sets
- Both mode race condition fix — `Promise.all` for Race + Evaluate POST before navigating; `evaluateTaskId` must be stored before navigation
- Category selector shows persona preview — display persona names/count in sidebar before submission

**Should have (Phase 2, multi-agent signal quality):**
- Cross-persona disagreement score — std dev of persona scores surfaced as "争议" badge (backend already has per-persona scores)
- Devil's advocate judge perspective — add to `JUDGE_PERSPECTIVES` in `pairwise_judge.py`, mark dissenting votes separately
- Expanded pairwise perspectives (+1 竞品视角) — brand differentiation signal, minimal code change

**Defer to v2.x (HIGH cost, needs validation first):**
- Persona confidence flagging — secondary LLM call per persona score doubles LLM cost; only build if users report score-reasoning contradictions
- Calibrated scoring against historical winners — requires historical outcome data pipeline not yet in place

### Architecture Approach

The existing Flask/React architecture is correct and stable. The frontend rewrite uses a replace-in-place strategy (not gradual migration): rewrite each page component in dependency order while keeping `lib/api.ts`, `store.ts`, and all `components/` render utilities frozen. The multi-agent backend enhancement inserts new phases (Phase 0: AgentDiffusion, Phase 1.75: CrossAgentValidator) into the existing EvaluationOrchestrator sequence behind feature flags, without changing any existing phase or API endpoint.

**Major components:**
1. `EvaluationOrchestrator` — sequences Phase 0-4 async pipeline; extend with AgentDiffusion (Phase 0) and CrossAgentValidator (Phase 1.75), both flag-gated
2. `AudiencePanel` — parallel persona LLM scoring; expand from 5-6 to 8-9 personas via config-only change to `PersonaRegistry`
3. `MultiJudge` / `CrossAgentValidator` — new services (~80 lines each), wired as peer services through EvaluationOrchestrator, NOT through BrandStateEngine
4. `lib/api.ts` (frontend) — frozen; the authoritative API contract; all new page components import from it, never duplicate call logic
5. `TaskManager` — add progress milestones for new phases (Phase 0: 5%, Phase 1.75: 55%)

**Key patterns:**
- Feature-flag gating for all new agent phases (`USE_AGENT_DIFFUSION`, `USE_CROSS_AGENT_VALIDATION` in config.py)
- Global `LLMSemaphore` at `LLMClient` level, not per-service (critical for multi-agent concurrency budget)
- Additive result schema: new fields in `EvaluationResult` are `Optional` with defaults; never remove/rename existing fields
- localStorage for cross-page state (not Zustand); Zustand scoped to in-page plan builder only

### Critical Pitfalls

1. **Silent image dropout (Pitfall 1, CRITICAL)** — `AudiencePanel` and `PairwiseJudge` call `os.path.exists()` on API URL strings, which always returns False; images silently skipped. Fix: extract single `resolve_image_path()` utility used by all services. Must fix before any other backend work — all current Evaluate results are computed without visual context.

2. **API contract drift during rewrite (Pitfall F1)** — MiroFish uses different naming conventions; developers copy field names from wrong source. Fix: create `contracts.ts` mirroring each Flask route's exact shape before writing any component; run `npm run build` after every component.

3. **Global LLM semaphore missing for multi-agent (Pitfall M1)** — each new agent type adds its own executor without a shared concurrency ceiling; 5-campaign evaluation with 3 agent types hits Bailian 429 limits. Fix: implement single `LLMSemaphore` at `LLMClient` level before adding any new agent type.

4. **Both mode race condition (Pitfall F4)** — `evaluateTaskId` may not be stored before navigation when Evaluate POST fails silently. Fix: `Promise.all` both Race and Evaluate POSTs; navigate only after both task IDs confirmed. Known debt explicitly flagged in PROJECT.md.

5. **Position bias compounding in judge ensemble (Pitfall M4)** — adding more judges with same ordering amplifies systematic bias (ACL 2025: 10-30% verdict flip rate from order swap). Fix: half of judge ensemble receives (A,B), half receives (B,A); majority vote only counts across orderings.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Critical Bug Fixes + Frontend Foundation
**Rationale:** Silent image dropout corrupts all Evaluate results; Both mode race condition loses task IDs; form state loss blocks multi-plan workflows. These are pre-conditions for everything else. Frontend foundation (contracts.ts, AppShell rewrite) must land before any page rewrites begin.
**Delivers:** Trustworthy Evaluate results with visual analysis; stable Both mode; contracts.ts API lock preventing future drift.
**Addresses:** Form state persistence, polling timeout/recovery, Both mode race condition fix, image path resolution, SQLite WAL + threading.Lock.
**Avoids:** Pitfall 1 (silent image dropout), Pitfall F1 (API contract drift), Pitfall F4 (Both mode race condition), Pitfall 4 (concurrent state corruption).

### Phase 2: Frontend Rewrite — Core Pages
**Rationale:** Once foundation is locked and critical bugs fixed, core page rewrites can proceed in dependency order. Layout/AppShell must land first. HomePage has highest bug count and is most complex — do early to unblock RunningPage.
**Delivers:** Complete frontend interaction rewrite: Layout + AppShell → LoginPage → HomePage → RunningPage → ResultPage → EvaluateResultPage.
**Uses:** motion `animate={{ width }}` for split-panel, `useReducer` log buffer (max 200 entries), step workflow indicators, real task status polling in RunningPage replacing fake animation.
**Addresses:** Winner-first result layout, category → persona preview, export reliability, cross-path (Race vs Evaluate) consistency badge.
**Avoids:** Pitfall F2 (MiroFish assumptions mismatch — treat as UX reference only, not code reference), Pitfall F3 (Zustand ghost state).

### Phase 3: Multi-Agent Foundation
**Rationale:** Backend enhancements require stable frontend first. Global LLM semaphore and AgentScore schema must be established before adding any new agent type — these are the pre-conditions that prevent M1-M3 pitfalls.
**Delivers:** Global LLM semaphore at LLMClient level; AgentScore dataclass schema; result_metadata in EvaluationResult; AgentDiffusion wired into orchestrator Phase 0 (flag-off by default); MAX_LLM_CONCURRENT config var.
**Avoids:** Pitfall M1 (agent count without concurrency budget), Pitfall M2 (score schema inconsistency), Pitfall M3 (cascade failure silent degradation).

### Phase 4: Multi-Agent Evaluation Enhancement
**Rationale:** With semaphore and schema in place, expand agent pool and add new judge types safely. Position-alternated ensemble must be enforced before any new judge implementations.
**Delivers:** Expanded PersonaRegistry (6→9 moodyPlus, 5→8 colored_lenses); MultiJudge with position-alternated ensemble; devil's advocate judge perspective; cross-persona disagreement score ("争议" badge); CrossAgentValidator (Phase 1.75) for debate-round reconciliation on high-variance campaigns.
**Addresses:** Cross-persona disagreement surfacing, devil's advocate judge, expanded pairwise perspectives (+竞品视角).
**Avoids:** Pitfall M4 (position bias compounding — alternate A/B order across judges), Pitfall M5 (calibration starvation — new agents start at 0.3x weight).

### Phase 5: Secondary Pages + Tech Debt
**Rationale:** TrendDashboard, CompareVersion, History, Dashboard pages are lower priority and independent. BrandStateEngine decomposition (1319-line God class) is tech debt that requires characterization tests first — never in same phase as feature additions.
**Delivers:** Remaining page rewrites (TrendDashboardPage, CompareVersionPage, HistoryPage, DashboardPage); BrandStateEngine incremental decomposition (BacktestEngine first, least coupled); JudgeCalibration schema extension for archetype predictions.
**Avoids:** Pitfall 3 (God class decomposition breaking Race path — characterization tests required before any extraction).

### Phase Ordering Rationale

- Image resolution fix (Phase 1) cannot be deferred — it silently corrupts product value proposition; all Evaluate results are currently partially blind.
- `contracts.ts` (Phase 1 frontend foundation) must precede all page rewrites — prevents API contract drift that TypeScript alone cannot catch at runtime.
- AppShell/Layout rewrite (Phase 2 start) blocks all other page rewrites — correct dependency order per ARCHITECTURE.md build graph.
- Global LLM semaphore (Phase 3) must precede all new agent types — without it, adding agents causes 429 failures at production scale (5 campaigns x 9 personas = 45 concurrent LLM calls without ceiling).
- AgentScore schema (Phase 3) must precede MultiJudge/CrossAgentValidator — without it, new agents are silently excluded from CampaignScorer aggregation.
- BrandStateEngine decomposition (Phase 5) must not happen concurrently with any feature phase — refactoring + features in same phase breaks characterization test coverage and is flagged as high recovery cost in PITFALLS.md.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Multi-Agent Foundation):** Bailian API rate limits for expanded concurrency — verify actual RPM/TPM for current account tier before setting `MAX_LLM_CONCURRENT` default. The conservative default of 8-12 may be too low or too high depending on account tier.
- **Phase 4 (Multi-Agent Enhancement):** CrossAgentValidator debate-round cost modeling — high-variance campaigns trigger expensive secondary LLM calls; validate variance threshold tuning against real campaign data before production enable.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Bug Fixes):** All fixes are mechanically straightforward with clear solutions documented in PITFALLS.md — path resolver extraction, Promise.all, threading.Lock, SQLite WAL pragma.
- **Phase 2 (Frontend Rewrite):** MiroFish reference patterns are fully documented in STACK.md with exact implementation details (cubic-bezier values, polling intervals, log buffer size).
- **Phase 5 (Tech Debt):** Strangler Fig pattern for BrandStateEngine decomposition is well-documented; BacktestEngine is confirmed as least coupled starting point.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified from actual codebase files; no new deps needed means no version compatibility guesswork |
| Features | HIGH | Based on direct codebase analysis (all 10 pages + 20 backend services) + 2025 multi-agent research literature |
| Architecture | HIGH | Based on direct reading of all service files and frontend pages; integration points verified against actual code |
| Pitfalls | HIGH | Image dropout and contract drift verified at specific code locations; multi-agent pitfalls grounded in ACL/arXiv 2025 research |

**Overall confidence:** HIGH

### Gaps to Address

- **Bailian account tier rate limits:** The global semaphore ceiling depends on actual RPM quota for this Alibaba Cloud account. Default of 8-12 concurrent calls is conservative but should be validated against actual account limits before Phase 4 enables expanded agent pool.
- **JudgeCalibration bootstrap data:** Calibration system requires 5+ resolved evaluation sets to activate weights. New agent types run uncalibrated indefinitely unless historical evaluation data is manually resolved. The 0.3x provisional weight for new agents mitigates this, but the calibration starvation timeline is unknown.
- **html2canvas export reliability on large result sets:** Failure condition not precisely documented. Needs real 5-plan result set testing in Phase 1/2 to determine whether scroll-capture or page-break logic is required.

## Sources

### Primary (HIGH confidence)
- `/Users/slr/MiroFishmoody/frontend/src/` (all pages + lib/api.ts) — direct codebase analysis
- `/Users/slr/MiroFishmoody/backend/app/services/` (all 20 services) — direct codebase analysis
- `https://github.com/666ghj/MiroFish` — MiroFish upstream: frontend patterns, polling intervals, log buffer (200 entries), cubic-bezier values
- `.planning/codebase/STACK.md`, `.planning/codebase/ARCHITECTURE.md` — verified existing stack (2026-03-17)
- `.planning/PROJECT.md` — v2.0 requirements and constraints

### Secondary (MEDIUM confidence)
- [Multi-LLM-Agents Debate — Performance, Efficiency, and Scaling Challenges (ICLR 2025)](https://d2jud02ci9yv69.cloudfront.net/2025-04-28-mad-159/blog/mad/) — debate scaling: gains plateau after 3-5 diverse agents
- [Judging the Judges: Position Bias in LLM-as-a-Judge (ACL 2025)](https://aclanthology.org/2025.ijcnlp-long.18/) — 10-30% verdict flip rate from order swap, systematic not random
- [Beyond Consensus: Mitigating Agreeableness Bias in LLM Judge Evaluations (NUS 2025)](https://aicet.comp.nus.edu.sg/wp-content/uploads/2025/10/Beyond-Consensus-Mitigating-the-agreeableness-bias-in-LLM-judge-evaluations.pdf) — agreeableness bias mitigation
- [Why Do Multi-Agent LLM Systems Fail? (arxiv 2503.13657)](https://arxiv.org/abs/2503.13657) — 3-category, 14-failure-mode taxonomy; kappa=0.88 across 150 traces
- [Adversarial Multi-Agent Evaluation through Iterative Debates (arXiv 2410.04663)](https://arxiv.org/html/2410.04663v1) — devil's advocate patterns
- [Alibaba Cloud Model Studio Rate Limits](https://www.alibabacloud.com/help/en/model-studio/rate-limit) — Bailian API RPM/TPM limits
- [Strangler Fig Pattern pitfalls (AWS)](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/strangler-fig.html) — API contract maintenance during incremental rewrites

### Tertiary (LOW confidence)
- html2canvas PDF export behavior on large result sets — anecdotal; needs validation with actual 5-plan data in Phase 1/2

---
*Research completed: 2026-03-18*
*Ready for roadmap: yes*
