# Stack Research

**Domain:** Campaign evaluation engine — v2.0 frontend rewrite + multi-agent backend enhancement
**Researched:** 2026-03-18
**Confidence:** HIGH (existing stack verified from codebase; MiroFish patterns verified from source; new additions rely on stdlib only)

---

## Scope

This document covers ONLY what is new or changed for v2.0. The previous milestone (v1.x) STACK.md entries (bcrypt, structlog, @tanstack/react-query, recharts, asyncio) are already implemented or superseded.

**v2.0 goals:**
1. Frontend rewrite — translate MiroFish original Vue UX patterns into existing React/TypeScript stack
2. Multi-agent parallel evaluation backend — increase agent count, add cross-validation, improve accuracy

---

## What MiroFish Original Uses (Reference Architecture)

MiroFish frontend: Vue 3 + Vue Router 4 + D3.js (force-directed graph) + axios + Vite. No component library. Minimal CSS reset.

**Key UX patterns MiroFishmoody v2.0 should adopt:**

| Pattern | MiroFish Implementation | MiroFishmoody Translation |
|---------|------------------------|--------------------------|
| Step workflow indicator | 5-step numbered header, status dot (orange/green/red) | React component, existing Tailwind + lucide-react |
| Dual-panel split layout | CSS transitions `width 0.4s cubic-bezier`, view mode toggle | `motion.div animate={{ width }}` (motion 12.x already installed) |
| Task status polling | `setInterval` every 2s calling `getTaskStatus()` | Already in `EvaluatePage.tsx`, extend to `RunningPage.tsx` |
| Graph/data refresh polling | Separate `setInterval` every 10-30s | Separate interval per concern |
| Rolling log buffer | Array capped at 200 entries, `{ time, msg }` objects | `useReducer` with APPEND action, max 200 |
| Maximize/restore panel | Header click toggles between split and full-width | Zustand local state or `useState` |
| Font stack | JetBrains Mono + Space Grotesk + Noto Sans SC | Add to `tailwind.config.js` fontFamily, load via Google Fonts CDN |

Since MiroFishmoody already uses React 19 + TypeScript + Tailwind + motion, these patterns translate directly. No stack changes required.

---

## Recommended Stack

### Core Technologies — NO CHANGES

| Technology | Current Version | Status |
|------------|----------------|--------|
| React | 19.x | Keep as-is |
| TypeScript | 5.9 | Keep as-is |
| Tailwind CSS | 3.4 | Keep as-is (add font families) |
| Vite | 8.x | Keep as-is |
| React Router DOM | 7.x | Keep as-is |
| Zustand | 5.x | Keep as-is |
| motion (Framer fork) | 12.x | Keep as-is |
| Flask | 3.0+ | Keep as-is |
| SQLite WAL | — | Keep as-is |
| ThreadPoolExecutor | stdlib | Keep as-is, extend |
| openai SDK | >=1.0.0 | Keep as-is |

### New Frontend Libraries — NONE

No new npm packages are needed. All MiroFish UX patterns are achievable with the existing stack:

- Split-panel animations → `motion.div` (already installed)
- Step indicators + status dots → Tailwind + lucide-react (already installed)
- Polling → `setInterval` + `useEffect` (React stdlib)
- Log buffer → `useReducer` (React stdlib)
- Font additions → `tailwind.config.js` config change, no package

**Rationale:** Adding new libraries for UI patterns achievable with installed tools increases bundle size, adds upgrade surface, and creates inconsistency in animation/styling approach.

### New Backend Libraries — NONE

Multi-agent enhancement uses only Python stdlib:

- `concurrent.futures.ThreadPoolExecutor` — already in use
- `threading.Semaphore` — already in use (ImageAnalyzer pattern)
- `statistics.mean`, `statistics.stdev` — stdlib, for ConsensusAgent outlier detection
- `threading.Lock` — already in use (_evaluation_store)

**Rationale:** The multi-agent expansion is a structural change (more agents, cross-validation), not a dependency change.

---

## Supporting Libraries (Existing — Confirmed Adequate for v2.0)

### Frontend

| Library | Version | v2.0 Usage |
|---------|---------|------------|
| lucide-react | 0.577 | Status dot icons, workflow step icons |
| tailwind-merge + clsx | 3.5 + 2.1 | Panel mode toggle classes, agent status badges |
| motion | 12.x | Panel width transitions, step entry animations |
| recharts | existing | Radar charts (no change) |
| @tanstack/react-query | 5.x | Task polling (already in use in EvaluatePage) |

### Backend

| Library | Version | v2.0 Usage |
|---------|---------|------------|
| concurrent.futures | stdlib | Extend max_workers for multi-judge |
| threading | stdlib | Lock for ConsensusAgent result aggregation |
| statistics | stdlib | Mean/stdev for outlier detection in ConsensusAgent |
| openai | >=1.0.0 | No change (all LLM calls go through LLMClient) |

---

## Frontend Rewrite: Specific Implementation Decisions

### 1. Polling Parity (RunningPage fix)

Current `RunningPage.tsx` fakes progress with a `setInterval` visual animation. The actual API call result is the only real signal. MiroFish uses 2 separate intervals: 2s for task status, 10-30s for graph data.

**Decision:** Add real task status polling to `RunningPage.tsx` matching the pattern already in `EvaluatePage.tsx`. The visual step animation stays (good UX), but completion detection must come from the backend, not a timer.

**Implementation:** One `setInterval` at 2s calling `/api/tasks/{task_id}/status`, cleared on completion or error. Existing `getRaceState` / `saveRaceState` pattern handles state handoff.

### 2. Log Buffer Component

New component `LogBuffer` with:
- `useReducer` state: `{ entries: Array<{ time: string; msg: string }>, maxEntries: 200 }`
- Action `APPEND` prepends new entry, slices to maxEntries
- Renders as `font-mono text-xs` scrollable div
- No external dependency

### 3. Split Panel Layout

New component `SplitPanel` using `motion.div`:
- `viewMode: 'left' | 'split' | 'right'`
- Left panel width: `viewMode === 'left' ? '100%' : viewMode === 'split' ? '50%' : '0%'`
- `motion.div animate={{ width: panelWidth }} transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}`
- The cubic-bezier `[0.4, 0, 0.2, 1]` matches MiroFish's CSS `cubic-bezier(0.4, 0, 0.2, 1)` (Tailwind's default ease-in-out)

### 4. Font Stack Addition

Add to `frontend/tailwind.config.js`:

```js
fontFamily: {
  mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
  display: ['Space Grotesk', 'system-ui', 'sans-serif'],
  sans: ['Space Grotesk', 'Noto Sans SC', 'system-ui', 'sans-serif'],
}
```

Load in `frontend/index.html`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600&display=swap" rel="stylesheet" />
```

No npm package required.

---

## Backend Multi-Agent: Specific Implementation Decisions

### Current State

| Service | Agents | Concurrency |
|---------|--------|-------------|
| AudiencePanel | 6 personas (moodyPlus) / 5 (colored_lenses) | ThreadPoolExecutor(max_workers=4) |
| PairwiseJudge | 1 judge per pair | ThreadPoolExecutor(max_workers=4) |
| ImageAnalyzer | 1 analyzer | ThreadPoolExecutor + Semaphore(3) |

### Multi-Agent Enhancement Plan

**1. Expand PersonaRegistry (config-only change)**

Add 3-4 new personas per category in `PersonaRegistry`:
- moodyPlus: 6 → 9 personas
- colored_lenses: 5 → 8 personas

This is pure configuration. No code change in `AudiencePanel.evaluate_all()`. The ThreadPoolExecutor scales automatically to the persona count.

**2. MultiJudge Wrapper (new service, ~80 lines)**

New `MultiJudge` wraps `PairwiseJudge` to run each campaign pair through N independent judges:

```python
class MultiJudge:
    def __init__(self, llm_client, n_judges: int = 3):
        self.judges = [PairwiseJudge(llm_client) for _ in range(n_judges)]
        self._sem = threading.Semaphore(Config.MAX_LLM_CONCURRENT)

    def judge_pair(self, a, b):
        # Run n_judges in parallel, take majority vote
        with ThreadPoolExecutor(max_workers=self.n_judges) as ex:
            futures = [ex.submit(j.judge_pair, a, b) for j in self.judges]
            results = [f.result() for f in as_completed(futures)]
        return self._majority_vote(results)
```

Majority vote reduces single-LLM variance. With 3 judges, one outlier doesn't change the result.

**3. ConsensusAgent (new service, ~60 lines)**

After AudiencePanel completes, ConsensusAgent detects outlier persona scores:

```python
class ConsensusAgent:
    def flag_outliers(self, panel_scores: List[PanelScore]) -> dict:
        per_campaign_scores = defaultdict(list)
        for ps in panel_scores:
            per_campaign_scores[ps.campaign_id].append(ps.score)
        outliers = {}
        for cid, scores in per_campaign_scores.items():
            if len(scores) < 3:
                continue
            mean = statistics.mean(scores)
            stdev = statistics.stdev(scores)
            outliers[cid] = [s for s in scores if abs(s - mean) > 2 * stdev]
        return outliers
```

Outlier flags surface in the result UI (DiagnosticsPanel) as "评审意见分歧明显" warnings. They do NOT exclude persona scores from ranking — they inform the human reviewer.

**4. `max_workers` Scaling**

Increase from `max_workers=4` to `max_workers=min(agent_count, 8)` in both AudiencePanel and MultiJudge. The Semaphore pattern from ImageAnalyzer (currently `Semaphore(3)`) should be applied to MultiJudge too, controlled by `Config.MAX_LLM_CONCURRENT` (new config var, default 5).

### Pipeline Integration

Multi-agent changes slot into `EvaluationOrchestrator.run()`:

```
Phase 1: AudiencePanel (9 personas → parallel)
Phase 1.5: ConsensusAgent flags outliers (sync, ~1ms)
Phase 1.5b: ImageAnalysis (unchanged)
Phase 2: MultiJudge (3 judges per pair → parallel)
Phase 3: CampaignScorer (unchanged)
Phase 4: SummaryGenerator (unchanged)
```

No new API endpoints needed. Existing `/api/evaluate/start` and `/api/tasks/{id}/status` cover the flow.

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Vue.js / vue-router | MiroFish uses Vue but MiroFishmoody is React — translating UX patterns is the goal, not migrating frameworks | React + motion for animations |
| D3.js | MiroFish uses D3 for knowledge graphs — MiroFishmoody has no graph visualization need | recharts covers existing radar/bar needs |
| WebSocket / Flask-SocketIO | 3-minute evaluation tasks don't need sub-second push — 2s polling is adequate | `setInterval` polling (existing) |
| Celery + Redis | Internal tool, <10 concurrent users — distributed task queue is operational overhead without benefit | Extend existing TaskManager |
| LangGraph / LangChain | Adds abstraction over direct LLM calls that are already well-structured; multi-agent here is simple parallel fan-out, not a stateful graph | ThreadPoolExecutor directly |
| Zep Cloud | MiroFish uses Zep for session memory across agent conversations — campaign evaluation is stateless per run | SQLite result storage sufficient |
| GraphRAG | MiroFish builds knowledge graphs from documents — not applicable to image/text campaign evaluation | N/A |
| scipy / numpy | `statistics.stdev` (stdlib) is sufficient for 1D outlier detection on ≤9 values | Python stdlib `statistics` module |
| LiteLLM | Single LLM provider (Qwen via Bailian) — routing/fallback abstraction has no value here | openai SDK directly |
| axios (frontend) | MiroFish uses axios but MiroFishmoody already has a well-structured `lib/api.ts` using fetch — adding axios creates two HTTP layers | Keep existing fetch-based api.ts |

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| Translate MiroFish UX patterns to React | Migrate frontend to Vue 3 | Full framework migration for existing 10-page React app — zero user-visible difference, 2-3 weeks of work |
| `statistics.stdev` for outlier detection | scipy stats | Stdlib avoids a heavy scientific computing dependency for a 5-line calculation |
| ThreadPoolExecutor for multi-judge | asyncio + async LLM calls | Flask is sync; asyncio in Flask 3.0 requires `async def` views throughout — partial async adoption creates bugs; ThreadPoolExecutor already proven in this codebase |
| Extend PersonaRegistry config | Separate MultiAgent orchestration framework | Persona expansion is configuration, not architecture — adding 3 personas is a `personas.yaml` edit |
| motion `animate={{ width }}` for panels | CSS transition classes in Tailwind | motion provides better control over cubic-bezier and play/stop; Tailwind transitions can't be driven by dynamic JS state as cleanly |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| React 19.x | React Router DOM 7.x | Confirmed compatible |
| motion 12.x | React 19 | Confirmed — Framer Motion fork explicitly supports React 19 |
| Tailwind CSS 3.4 | Vite 8.x | Confirmed — postcss pipeline |
| Python 3.11+ | statistics module | stdlib, no version concern |
| ThreadPoolExecutor | Python 3.11+ | stdlib, no version concern |

---

## Installation

No new packages required for v2.0. All new capabilities use already-installed libraries or Python stdlib.

```bash
# Verify deps are current — both commands should be no-ops
cd /Users/slr/MiroFishmoody/frontend && npm install
cd /Users/slr/MiroFishmoody/backend && uv sync
```

The only file changes needed before coding:
1. `frontend/tailwind.config.js` — add fontFamily entries
2. `frontend/index.html` — add Google Fonts `<link>` tags
3. `backend/app/config.py` — add `MAX_LLM_CONCURRENT` config var (default: 5)
4. `.env.example` — document `MAX_LLM_CONCURRENT`

---

## Sources

- MiroFish source: https://github.com/666ghj/MiroFish — frontend patterns (polling intervals, log buffer size 200, cubic-bezier values, step workflow)
- MiroFish `frontend/package.json` (verified): vue@^3.5.24, vue-router@^4.6.3, d3@^7.9.0, axios@^1.13.2
- `/Users/slr/MiroFishmoody/.planning/codebase/STACK.md` — verified existing stack (2026-03-17)
- `/Users/slr/MiroFishmoody/backend/app/services/audience_panel.py` — ThreadPoolExecutor(max_workers=4), 6/5 persona counts
- `/Users/slr/MiroFishmoody/backend/app/services/pairwise_judge.py` — single judge pattern, max_workers=4
- `/Users/slr/MiroFishmoody/backend/app/services/evaluation_orchestrator.py` — full pipeline structure
- `/Users/slr/MiroFishmoody/frontend/src/pages/RunningPage.tsx` — confirmed fake-step animation pattern (no real polling)
- `/Users/slr/MiroFishmoody/frontend/src/pages/EvaluatePage.tsx` — confirmed real polling pattern (2s setInterval)

---

*Stack research for: MiroFishmoody v2.0 — frontend rewrite + multi-agent backend*
*Researched: 2026-03-18*
