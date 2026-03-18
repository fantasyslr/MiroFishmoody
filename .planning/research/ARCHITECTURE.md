# Architecture Research

**Domain:** AI campaign evaluation engine — Flask + React SPA, multi-agent backend
**Researched:** 2026-03-18
**Confidence:** HIGH (based on direct codebase analysis)

## Standard Architecture

### System Overview (Current v1.1)

```
┌─────────────────────────────────────────────────────────────────┐
│                    React SPA (frontend/src/)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │ HomePage │  │ResultPage│  │EvaluateRe│  │TrendDashboard│    │
│  │ (form)   │  │ (race)   │  │sultPage  │  │ Page         │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘    │
│       │             │             │               │             │
│  ┌────┴─────────────┴─────────────┴───────────────┴───────┐     │
│  │           lib/api.ts (all fetch calls here)             │     │
│  └────────────────────────┬────────────────────────────────┘     │
└───────────────────────────┼─────────────────────────────────────┘
                            │ HTTP / JSON
┌───────────────────────────┼─────────────────────────────────────┐
│                    Flask API Layer (api/)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ brandiction  │  │  campaign    │  │  auth                │   │
│  │ .py          │  │  .py         │  │  .py                 │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────┘   │
│         │                 │                                      │
├─────────┼─────────────────┼──────────────────────────────────────┤
│         │    Services Layer (services/)                          │
│  ┌──────┴───────┐  ┌──────┴────────────────────────────────┐    │
│  │  Race path   │  │  Evaluate path                         │    │
│  │  ─────────── │  │  ─────────────────────────────────────│    │
│  │  BaselineRan-│  │  EvaluationOrchestrator               │    │
│  │  ker         │  │    Phase 1: AudiencePanel (parallel)  │    │
│  │  ImageAnalyz-│  │    Phase 1.5: ImageAnalyzer           │    │
│  │  er          │  │    Phase 2: PairwiseJudge / Market-   │    │
│  │  BrandState- │  │             Judge                     │    │
│  │  Engine      │  │    Phase 3: CampaignScorer (BT model) │    │
│  └──────────────┘  │    Phase 4: SummaryGenerator          │    │
│                    └───────────────────────────────────────┘    │
│  Shared: PersonaRegistry, LLMClient, TaskManager, ImageHelpers   │
├─────────────────────────────────────────────────────────────────┤
│                         Storage                                  │
│  ┌───────────────────┐   ┌──────────────────────────────────┐    │
│  │  tasks.db (SQLite)│   │  brandiction.db (SQLite)         │    │
│  │  WAL mode         │   │  WAL mode                        │    │
│  └───────────────────┘   └──────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────────── ┐   │
│  │  uploads/results/<set_id>.json (flat file evaluation store)│   │
│  └────────────────────────────────────────────────────────── ┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Location |
|-----------|---------------|----------|
| `HomePage` | Mode selector, plan form, image upload, submit | `pages/HomePage.tsx` |
| `RunningPage` | Polls Race (sync) or Evaluate (async) progress | `pages/RunningPage.tsx` |
| `ResultPage` | Renders Race result (baseline + visual) | `pages/ResultPage.tsx` |
| `EvaluateResultPage` | Renders Evaluate result (3-tab scoreboard) | `pages/EvaluateResultPage.tsx` |
| `TrendDashboardPage` | Campaign trend aggregation over time | `pages/TrendDashboardPage.tsx` |
| `CompareVersionPage` | Side-by-side iteration version compare | `pages/CompareVersionPage.tsx` |
| `lib/api.ts` | All HTTP calls, localStorage cross-page state | `lib/api.ts` |
| `EvaluationOrchestrator` | Sequences Phase 1-4 async evaluate pipeline | `services/evaluation_orchestrator.py` |
| `AudiencePanel` | Parallel persona LLM scoring per campaign | `services/audience_panel.py` |
| `PairwiseJudge` | All-pairs LLM tournament, position-swap debias | `services/pairwise_judge.py` |
| `CampaignScorer` | Bradley-Terry model combining panel + pairwise | `services/campaign_scorer.py` |
| `BaselineRanker` | Historical evidence-based ranking | `services/baseline_ranker.py` |
| `ImageAnalyzer` | Multimodal visual profile + diagnostics | `services/image_analyzer.py` |
| `BrandStateEngine` | Cognitive brand state prediction (God class) | `services/brand_state_engine.py` |
| `PersonaRegistry` | DI-injected persona config by category | `services/persona_registry.py` |
| `TaskManager` | SQLite-backed singleton async task tracking | `models/task.py` |
| `AgentDiffusion` | Consumer agent simulation (social diffusion) | `services/agent_diffusion.py` |
| `SubmarketEvaluator` | Dimension extraction from panel scores | `services/submarket_evaluator.py` |

---

## v2.0 Integration Architecture

### Frontend Rewrite: Replace-in-Place Strategy

**Recommendation: Replace in-place, page by page — not gradual migration.**

Rationale: The existing pages are small (all < 500 lines), self-contained, and use a shared `lib/api.ts` client. The API contracts are stable. The MiroFish reference provides complete interaction logic. A gradual migration would require maintaining two routing trees simultaneously with no benefit for a codebase of this size.

**Rewrite order** (bottom-up, unblock dependencies first):

```
Phase A (no page dependencies):
  LoginPage.tsx          — standalone, simple
  components/layout/     — Layout, AppShell — affects all pages

Phase B (depends on layout):
  HomePage.tsx           — plan form + mode selector (most complex, known bugs)
  RunningPage.tsx        — polling logic

Phase C (depends on HomePage data contract):
  ResultPage.tsx         — Race result display
  EvaluateResultPage.tsx — Evaluate 3-tab display (most render logic)

Phase D (standalone reads):
  TrendDashboardPage.tsx
  CompareVersionPage.tsx
  HistoryPage.tsx
  DashboardPage.tsx
```

**What stays unchanged during rewrite:**
- `lib/api.ts` — zero changes. All API types, fetch helpers, localStorage helpers are stable and correct.
- `store.ts` (Zustand) — keep as-is; only used by EvaluatePage flow.
- `components/` (RadarScoreChart, DiagnosticsPanel, PercentileBar) — keep; these are rendering-only utilities.
- All backend routes and response shapes.

**What gets rewritten:**
- Every page component in `pages/` — new interaction logic from MiroFish reference.
- `components/layout/AppShell.tsx` and `Layout.tsx` — new shell from MiroFish.

### Multi-Agent Backend: Extend EvaluationOrchestrator

**Pattern: Parallel agent pool inside existing orchestrator phases.**

The existing orchestrator runs phases sequentially. Multi-agent enhancement means:
1. Within Phase 1 (AudiencePanel): expand from 5-6 fixed personas to a larger pool with cross-persona debate rounds.
2. Add a new Phase 1.75: cross-agent validation — agents challenge each other's top objections, producing a reconciled consensus score per campaign.
3. `AgentDiffusion` (already exists as `services/agent_diffusion.py`) plugs in as an optional Phase 0 — social diffusion simulation that pre-weights persona sensitivities before scoring begins.

**Orchestrator extension (additive, no breaking changes):**

```python
# Extended EvaluationOrchestrator.run() — new phases shown

# Phase 0 (NEW): Agent diffusion pre-weighting
if Config.USE_AGENT_DIFFUSION:
    diffusion = AgentDiffusion(brand_state=current_brand_state)
    agent_weights = diffusion.run(campaign_set)   # -> persona sensitivity map

# Phase 1: AudiencePanel (EXTEND — more agents, pass agent_weights)
panel = AudiencePanel(llm_client=llm, category=category, agent_weights=agent_weights)
panel_scores = panel.evaluate_all(campaigns)  # internally fans out to 24-36 agents

# Phase 1.75 (NEW): Cross-agent consensus validation
if Config.USE_CROSS_AGENT_VALIDATION:
    validator = CrossAgentValidator(llm_client=llm)
    panel_scores = validator.reconcile(panel_scores, campaigns)

# Phase 2-4: unchanged
```

**Agent coordination pattern:**

```
AudiencePanel.evaluate_all()
  ├── ThreadPoolExecutor (max_workers = len(personas) * len(campaigns))
  ├── Semaphore controls LLM concurrency (Config.MAX_LLM_CONCURRENCY)
  ├── Each worker: persona_i x campaign_j -> PanelScore
  └── Result: List[PanelScore]   (N_personas x N_campaigns entries)

CrossAgentValidator.reconcile()  [NEW]
  ├── Group scores by campaign_id
  ├── Find high-variance campaigns (std_dev > threshold)
  ├── For high-variance only: spawn debate round
  │     - Agents with minority opinion see majority reasoning
  │     - Single LLM call per debating agent: "revise or hold?"
  └── Return revised PanelScore list
```

**Key constraint:** Debate round only fires on high-variance campaigns. Cost scales with disagreement, not with total campaign count. Keeps LLM call budget bounded.

---

## Data Flow Changes (v2.0)

### Race Path — unchanged

```
HomePage (new UI) -> lib/api.ts (saveRaceState) -> RunningPage
  -> POST /api/brandiction/race (sync)
  -> BaselineRanker + ImageAnalyzer + BrandStateEngine
  -> RaceResult JSON -> localStorage -> ResultPage (new UI)
```

### Evaluate Path — orchestrator extended

```
HomePage (new UI) -> lib/api.ts (saveEvaluateState) -> RunningPage
  -> POST /api/campaign/evaluate (async, returns task_id)
  -> EvaluationOrchestrator.run() [extended with agent pool phases]
      Phase 0: AgentDiffusion (optional, flag-gated)
      Phase 1: AudiencePanel (24-36 agents via ThreadPoolExecutor + Semaphore)
      Phase 1.5: ImageAnalyzer (parallel per campaign)
      Phase 1.75: CrossAgentValidator (only for high-variance campaigns) [NEW]
      Phase 2: PairwiseJudge / MarketJudge
      Phase 3: CampaignScorer (Bradley-Terry)
      Phase 4: SummaryGenerator
  -> Result JSON -> memory store + uploads/results/<set_id>.json
  -> GET /api/campaign/evaluate/status/<task_id> polling
  -> EvaluateResultPage (new UI, 3-tab scoreboard)
```

### State Management (Frontend) — v2.0 unchanged

The localStorage cross-page state pattern is intentional and correct. No change.

```
lib/api.ts
  saveRaceState() / getRaceState()         -- Race payload + result
  saveEvaluateState() / getEvaluateState() -- Evaluate task + result
  saveBothModeState() / getBothModeState() -- Both mode coordination
  saveIterateState() / getIterateState()   -- Version iteration context
```

Zustand (`store.ts`) remains scoped to the in-page plan builder in EvaluatePage. Do not expand its scope.

---

## Component Boundaries

### Integration Points: Frontend Rewrite

| Boundary | v1.1 State | v2.0 Action |
|----------|-----------|-------------|
| `HomePage` <-> `lib/api.ts` | Uses `saveRaceState`, `evaluateCampaigns`, `uploadCampaignImage` | Keep all imports, rewrite JSX and state management logic |
| `ResultPage` <-> `lib/api.ts` | Reads `getRaceState()` | No change to data contract |
| `EvaluateResultPage` <-> API | Reads `getEvaluateResult(setId)` | No change to response shape |
| `RunningPage` <-> `getEvaluateStatus` | Polls task status | Keep polling interval and error handling, rewrite UI |
| `components/RadarScoreChart` | Used in EvaluateResultPage | Keep as-is, only change import in parent |
| `components/DiagnosticsPanel` | Used in ResultPage + EvaluateResultPage | Keep as-is |

### Integration Points: Multi-Agent Backend

| Boundary | v1.1 State | v2.0 Action |
|----------|-----------|-------------|
| `EvaluationOrchestrator` <-> `AudiencePanel` | Fixed 5-6 personas, direct call | Inject `agent_weights` param; AudiencePanel expands agent pool internally |
| `EvaluationOrchestrator` <-> new `CrossAgentValidator` | Does not exist | New class, injected via DI same as other services |
| `EvaluationOrchestrator` <-> `AgentDiffusion` | Exists but not wired into orchestrator | Add Phase 0 call behind `Config.USE_AGENT_DIFFUSION` flag |
| `TaskManager` <-> orchestrator | Progress updates at fixed points | Add milestones for new phases (Phase 0: 5%, Phase 1.75: 55%) |
| `JudgeCalibration` <-> new agents | Saves per-persona predictions | Extend schema to store per-archetype predictions from expanded pool |
| Flask `/api/campaign/evaluate` <-> orchestrator | Passes `category` | No change needed; new phases are internal to orchestrator |

---

## Recommended Project Structure (v2.0 additions)

```
backend/app/services/
├── evaluation_orchestrator.py     # MODIFY: wire Phase 0 + Phase 1.75
├── audience_panel.py              # MODIFY: support agent_weights param + larger pool
├── agent_diffusion.py             # EXISTS: wire into orchestrator
├── cross_agent_validator.py       # NEW: debate-round reconciliation
├── submarket_evaluator.py         # EXISTS: unchanged
├── pairwise_judge.py              # unchanged
├── campaign_scorer.py             # unchanged
└── ...

frontend/src/pages/
├── HomePage.tsx                   # REWRITE (MiroFish interaction logic)
├── RunningPage.tsx                # REWRITE
├── ResultPage.tsx                 # REWRITE
├── EvaluateResultPage.tsx         # REWRITE
├── TrendDashboardPage.tsx         # REWRITE (if buggy)
├── CompareVersionPage.tsx         # REWRITE (if buggy)
├── HistoryPage.tsx                # REWRITE (if buggy)
├── DashboardPage.tsx              # REWRITE (if buggy)
└── LoginPage.tsx                  # REWRITE (if buggy)

frontend/src/
├── lib/api.ts                     # DO NOT TOUCH
├── store.ts                       # DO NOT TOUCH
├── components/                    # DO NOT TOUCH (RadarScoreChart, DiagnosticsPanel, etc.)
└── components/layout/             # REWRITE (AppShell, Layout from MiroFish)
```

---

## Architectural Patterns

### Pattern 1: Feature-Flag Gating for New Agent Phases

**What:** Each new agent phase is controlled by a `Config` boolean flag. Phases default to `False` and are enabled in staging before production.

**When to use:** Every new LLM call path in v2.0. Prevents runaway cost if a new phase has bugs.

**Example:**
```python
# config.py
USE_AGENT_DIFFUSION: bool = os.getenv('USE_AGENT_DIFFUSION', 'false').lower() == 'true'
USE_CROSS_AGENT_VALIDATION: bool = os.getenv('USE_CROSS_AGENT_VALIDATION', 'false').lower() == 'true'
CROSS_AGENT_VARIANCE_THRESHOLD: float = float(os.getenv('CROSS_AGENT_VARIANCE_THRESHOLD', '2.0'))
```

### Pattern 2: Semaphore-Bounded Parallel Agent Calls

**What:** All LLM calls within a phase share a `threading.BoundedSemaphore` that caps concurrent inflight calls regardless of agent pool size.

**When to use:** Phase 1 (AudiencePanel). The expanded 24-36 agent pool must not flood the Bailian API. The existing `MAX_LLM_CONCURRENCY` env var already controls this — preserve it.

**Example:**
```python
# audience_panel.py (existing pattern, preserve it)
semaphore = threading.BoundedSemaphore(Config.MAX_LLM_CONCURRENCY)
with ThreadPoolExecutor(max_workers=len(all_agents)) as executor:
    futures = [executor.submit(_score_with_semaphore, agent, campaign, semaphore)
               for agent in all_agents for campaign in campaigns]
```

### Pattern 3: Additive Result Schema for Multi-Agent Output

**What:** New agent phases append optional fields to `EvaluationResult`. Never remove or rename existing fields — the result JSON is persisted to flat files and the frontend reads it directly.

**When to use:** Any time multi-agent produces new data (debate transcripts, consensus scores, diffusion deltas).

**Example:**
```python
# models/evaluation.py — add optional fields only
@dataclass
class EvaluationResult:
    # ... existing fields unchanged ...
    agent_consensus_scores: Optional[Dict[str, float]] = None   # NEW
    diffusion_deltas: Optional[Dict[str, Dict[str, float]]] = None  # NEW
    debate_rounds: Optional[Dict[str, List[dict]]] = None           # NEW
```

---

## Anti-Patterns

### Anti-Pattern 1: Changing `lib/api.ts` Response Types During Frontend Rewrite

**What people do:** Refactor TypeScript types in `lib/api.ts` to match new component needs.

**Why it's wrong:** `lib/api.ts` types are 1:1 mirrors of backend Python models. If they diverge, silent runtime failures occur — TypeScript won't catch missing JSON fields at runtime. These types are also the ground truth documentation for the backend contract.

**Do this instead:** If a new backend field is added, extend the type with optional fields. Never remove existing fields even if the new UI does not use them.

### Anti-Pattern 2: Synchronous Multi-Agent Evaluation

**What people do:** Run 24-36 agents sequentially inside a daemon thread to "keep things simple."

**Why it's wrong:** Sequential 36-agent execution at ~2s per LLM call = 72+ seconds minimum. Frontend polls on a 3-second interval — users will think the task hung.

**Do this instead:** `ThreadPoolExecutor` with `Semaphore` (existing pattern in `AudiencePanel`). 36 agents x 3 campaigns at `MAX_LLM_CONCURRENCY=6` runs in ~4 parallel batches = ~8s for panel phase.

### Anti-Pattern 3: Expanding Zustand Store for Cross-Page State

**What people do:** Extend `store.ts` to hold Race + Evaluate state during the frontend rewrite because it seems cleaner than localStorage.

**Why it's wrong:** Zustand state is in-memory and lost on hard refresh. Race and Evaluate paths use `localStorage` deliberately so a user can refresh `RunningPage` mid-evaluation and still recover their session.

**Do this instead:** Keep all cross-page state in `lib/api.ts` localStorage helpers. Zustand stays scoped to the in-page plan builder only.

### Anti-Pattern 4: Adding Multi-Agent Logic to BrandStateEngine

**What people do:** Add agent diffusion coordination to `brand_state_engine.py` since it already handles brand state cognition.

**Why it's wrong:** `BrandStateEngine` is already 1319 lines (known tech debt per PROJECT.md). Adding more to it creates a 2000+ line unmaintainable God class.

**Do this instead:** `AgentDiffusion` is already its own service at `services/agent_diffusion.py`. Wire it through `EvaluationOrchestrator` as a peer service, not through `BrandStateEngine`.

---

## Build Order (Dependency Graph)

```
1. Backend: feature flags in Config
   (gate all new phases — enables safe deployment of multi-agent code)

2. Backend: wire AgentDiffusion into EvaluationOrchestrator Phase 0
   (self-contained, no new APIs, flag off by default)

3. Backend: extend AudiencePanel for larger agent pool
   (touches existing service — existing tests must still pass)

4. Backend: CrossAgentValidator new service
   (depends on AudiencePanel output shape being finalized)

5. Frontend: Layout + AppShell rewrite
   (blocks all page rewrites — must land first)

6. Frontend: LoginPage rewrite
   (no page dependencies beyond Layout)

7. Frontend: HomePage rewrite
   (highest bug count, most complex — do early to unblock RunningPage)

8. Frontend: RunningPage rewrite
   (depends on HomePage form submission contract remaining stable)

9. Frontend: ResultPage rewrite
   (depends on Race result shape in lib/api.ts — stable, no changes)

10. Frontend: EvaluateResultPage rewrite
    (most render logic; depends on Evaluate result shape — stable)

11. Frontend: Remaining pages (Trend, Compare, History, Dashboard)
    (independent, lower priority)

12. Backend: JudgeCalibration schema extension for archetype predictions
    (last — not blocking any user-visible feature)
```

---

## Scaling Considerations

This is an internal tool. Current load is < 10 concurrent users. SQLite WAL + daemon threads is the correct architecture.

| Scale | Architecture Notes |
|-------|-------------------|
| Current (< 10 users) | SQLite WAL + daemon threads — no changes needed |
| If evaluate concurrency > 3 simultaneous | Add queue depth limit on TaskManager; reject 4th concurrent evaluate with 429 |
| If LLM costs spike with 36-agent pool | Tune `CROSS_AGENT_VARIANCE_THRESHOLD` to reduce debate rounds; lower `clone_count` in AgentDiffusion archetypes |
| Never | PostgreSQL migration, Redis, separate worker process — internal tool, not justified by user scale |

---

## Sources

- Direct codebase analysis: `/Users/slr/MiroFishmoody/backend/app/services/` (all service files)
- Direct codebase analysis: `/Users/slr/MiroFishmoody/frontend/src/` (all pages + lib/api.ts)
- `.planning/codebase/ARCHITECTURE.md` — existing architecture documentation (2026-03-17)
- `.planning/PROJECT.md` — v2.0 requirements and constraints
- MiroFish reference: https://github.com/666ghj/MiroFish (target interaction patterns for frontend rewrite)

---

*Architecture research for: MiroFishmoody v2.0 — frontend rewrite + multi-agent backend*
*Researched: 2026-03-18*
