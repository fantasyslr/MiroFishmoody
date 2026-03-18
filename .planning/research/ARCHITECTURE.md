# Architecture Research

**Domain:** AI-assisted campaign evaluation tool (Flask monolith + React SPA)
**Researched:** 2026-03-18
**Confidence:** HIGH — based on direct source inspection of the entire codebase

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        React 19 SPA (Vite)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  pages/  │  │components│  │  lib/    │  │  store.ts        │  │
│  │ (routes) │  │  (UI)    │  │  api.ts  │  │  sessionStorage  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────────────┘  │
└───────┴──────────────┴────────────┴──────────────────────────────┘
                                    │ HTTP /api/*
┌───────────────────────────────────▼──────────────────────────────┐
│                    Flask Application (app/__init__.py)             │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────────┐   │
│  │ auth_bp  │  │ campaign_bp  │  │     brandiction_bp        │   │
│  │/api/auth │  │/api/campaign │  │     /api/brandiction      │   │
│  └──────────┘  └──────┬───────┘  └───────────────────────────┘   │
│              Static: /assets/* + /* → frontend/dist/index.html    │
└──────────────────────┬────────────────────────────────────────────┘
                       │ dispatch (threading.Thread)
┌──────────────────────▼────────────────────────────────────────────┐
│                  EvaluationOrchestrator                            │
│  Phase 1:   AudiencePanel  → PersonaRegistry(category)            │
│             ThreadPoolExecutor(persona × campaign)                 │
│             ConsensusAgent (outlier detection)                     │
│  Phase 1.5: ImageAnalyzer  → ThreadPoolExecutor(campaign)         │
│  Phase 2:   MultiJudgeEnsemble → PairwiseJudge(pos. alternation)  │
│  Phase 3:   CampaignScorer → ProbabilityAggregator + DimEval      │
│  Phase 4:   SummaryGenerator                                       │
└──────────────────────┬────────────────────────────────────────────┘
                       │
┌──────────────────────▼────────────────────────────────────────────┐
│                  Persistence Layer                                  │
│  backend/uploads/tasks.db          — SQLite WAL, TaskManager      │
│  backend/uploads/results/{id}.json — EvaluationResult JSON        │
│  backend/uploads/images/{set_id}/  — Campaign image files         │
│  backend/uploads/calibration/      — JudgeCalibration predictions │
│                                                                     │
│  _evaluation_store: dict           — In-process result cache      │
│  _store_lock: threading.Lock       — Guards dict-only ops only    │
└────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| `app/__init__.py` | Flask factory, blueprint registration, static file serving | `backend/app/__init__.py` |
| `campaign_bp` | HTTP routes: evaluate, status, result, export, images, trends | `backend/app/api/campaign.py` |
| `EvaluationOrchestrator` | Coordinates all evaluation phases; runs in daemon thread | `backend/app/services/evaluation_orchestrator.py` |
| `AudiencePanel` | Dispatches persona × campaign LLM calls in ThreadPoolExecutor | `backend/app/services/audience_panel.py` |
| `PersonaRegistry` | Loads category-specific persona configs from JSON files | `backend/app/services/persona_registry.py` |
| `ConsensusAgent` | Detects outlier persona scores via `statistics.stdev` | `backend/app/services/consensus_agent.py` |
| `ImageAnalyzer` | base64-encodes images, sends to multimodal LLM | `backend/app/services/image_analyzer.py` |
| `MultiJudgeEnsemble` | Runs N pairwise judges with alternating position order | `backend/app/services/pairwise_judge.py` |
| `CampaignScorer` | Aggregates panel + pairwise → overall_score + verdict | `backend/app/services/campaign_scorer.py` |
| `TaskManager` | SQLite-backed async task state (PENDING/PROCESSING/COMPLETED/FAILED) | `backend/app/models/task.py` |
| `LLMClient` | Global Semaphore(MAX_LLM_CONCURRENT), OpenAI-compatible API calls | `backend/app/utils/llm_client.py` |
| `BriefParser` | LLM-based natural language → structured Campaign fields | `backend/app/services/brief_parser.py` |

---

## Recommended Project Structure

```
backend/
├── app/
│   ├── __init__.py          # Flask factory + static serving + blueprints
│   ├── config.py            # Config class (env vars)
│   ├── auth.py              # login_required decorator
│   ├── api/
│   │   ├── __init__.py      # campaign_bp registration
│   │   ├── campaign.py      # HTTP routes (no business logic)
│   │   ├── auth.py          # auth_bp
│   │   └── brandiction.py   # brandiction_bp
│   ├── services/
│   │   ├── evaluation_orchestrator.py  # Phase coordinator
│   │   ├── audience_panel.py           # Persona scoring
│   │   ├── persona_registry.py         # Config-driven persona loading
│   │   ├── pairwise_judge.py           # MultiJudgeEnsemble + PairwiseJudge
│   │   ├── campaign_scorer.py          # Score aggregation + verdict
│   │   ├── image_analyzer.py           # Visual analysis
│   │   ├── brief_parser.py             # NL → structured fields
│   │   ├── consensus_agent.py          # Outlier detection
│   │   └── judge_calibration.py        # Weight calibration
│   ├── models/
│   │   ├── campaign.py      # Campaign, CampaignSet, ProductLine
│   │   ├── evaluation.py    # PanelScore, PairwiseResult, CampaignRanking
│   │   ├── scoreboard.py    # ScoreBoard, CampaignScoreView
│   │   ├── task.py          # TaskManager, TaskStatus
│   │   └── agent_score.py   # AgentScore schema
│   ├── utils/
│   │   ├── llm_client.py    # LLMClient + global Semaphore
│   │   ├── image_helpers.py # resolve_image_path + image_to_base64_part
│   │   └── logger.py
│   └── config/
│       └── personas/
│           ├── default.json
│           ├── moodyplus.json
│           └── colored_lenses.json
├── uploads/
│   ├── tasks.db             # SQLite WAL
│   ├── results/             # {set_id}.json per evaluation
│   ├── images/              # {set_id}/{campaign_id}__{uuid}__{name}
│   └── calibration/
│       └── predictions/
├── tests/
│   └── fixtures/
│       └── benchmark/       # (v2.1 new) regression dataset
└── run.py
frontend/
├── src/
│   ├── pages/
│   ├── components/
│   ├── lib/
│   │   └── api.ts
│   └── store.ts
└── dist/                    # Vite build output (served by Flask in prod)
```

---

## Architectural Patterns

### Pattern 1: Flask-Serves-Frontend (Static SPA Hosting)

**What:** Flask detects `frontend/dist/` at startup via `os.path.isdir()` and mounts static routes. All non-API routes serve `index.html` as SPA fallback. Path is computed as `os.path.abspath(os.path.join(os.path.dirname(__file__), '../../frontend/dist'))`.

**When to use:** Single-container Docker where a separate nginx is not present.

**Current implementation in `app/__init__.py`:**
```python
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), '../../frontend/dist')
dist = os.path.abspath(FRONTEND_DIST)

if os.path.isdir(dist):
    @app.route('/assets/<path:filename>')
    def serve_assets(filename):
        return send_from_directory(os.path.join(dist, 'assets'), filename)

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        file_path = os.path.join(dist, path)
        if path and os.path.isfile(file_path):
            return send_from_directory(dist, path)
        return send_from_directory(dist, 'index.html')
```

**Docker path resolution:** `__file__` = `/app/backend/app/__init__.py` → `dist` = `/app/frontend/dist`. Dockerfile line 25 copies Vite build output to exactly `/app/frontend/dist`. Path is correct. Silent failure occurs only when the build step is skipped or `npm run build` fails in CI.

**v2.1 fix:** Add a startup log line that prints the resolved `dist` path regardless of whether it exists, so debugging a 404 is immediate. Optionally assert in production mode.

### Pattern 2: Async Task via Daemon Thread

**What:** `POST /api/campaign/evaluate` creates a SQLite task record (status=PENDING), spawns a `threading.Thread(daemon=True)` running `EvaluationOrchestrator.run()`, and returns 202 immediately. Frontend polls `GET /evaluate/status/{task_id}` every 2s.

**Trade-offs:** Zero external dependencies (no Celery/Redis). Daemon threads are killed on Gunicorn worker restart — acceptable because the disk-persisted result file provides crash recovery. Not suitable for >10 simultaneous evaluations.

### Pattern 3: Category-Routed Persona Loading

**What:** `PersonaRegistry.get_personas(category="moodyplus"|"colored_lenses")` selects persona config file at load time. `AudiencePanel` receives `category` at construction. Category flows from `POST /evaluate` payload field → `data.get("category")` → `orchestrator.run(category=...)` → `AudiencePanel(category=category)`.

**v2.1 brief_type extension follows the same pattern exactly:**
```
POST /evaluate body: { ..., "brief_type": "brand"|"awareness"|"conversion" }
    ↓
data.get("brief_type") in api/campaign.py
    ↓
orchestrator.run(task_id, campaign_set, category, brief_type)
    ↓
CampaignScorer(judge_weights, persona_weights, brief_type_weights=WEIGHTS[brief_type])
    ↓
DimensionEvaluator uses brief_type_weights to reweight dimension scores
```

No existing API contract breaks: `brief_type` is optional; `None` → current uniform weighting.

### Pattern 4: In-Process Result Cache with Disk Fallback

**What:** `_evaluation_store: dict` holds completed results in memory. On miss, reads from `uploads/results/{set_id}.json`. Lock (`_store_lock`) protects dict-only operations; all file I/O and LLM calls are outside the lock.

**Write sequence (TD-01 pattern, already implemented):**
```python
# Step 1: dict write under lock
with self.store_lock:
    self.evaluation_store[set_id] = result_dict

# Step 2: file I/O outside lock
self.save_result_fn(set_id, result_dict)
```

---

## Data Flow

### Evaluate Request Flow

```
User submits form (React)
    ↓
POST /api/campaign/evaluate
    {campaigns[], category, brief_type, set_id, parent_set_id}
    ↓
_parse_evaluate_campaigns()  — normalizes campaign_id, maps description→core_message
    ↓
TaskManager.create_task()    — writes PENDING row to tasks.db
    ↓
threading.Thread(EvaluationOrchestrator.run)  — returns 202 immediately
    │
    ├── AudiencePanel.evaluate_all()
    │     PersonaRegistry.get_personas(category)
    │     ThreadPoolExecutor: N_personas × N_campaigns LLM calls
    │     ConsensusAgent.detect()  — flags outlier scores
    │
    ├── ImageAnalyzer (if campaign has image_paths)
    │     resolve_image_path(url) → filesystem path
    │     image_to_base64_part()  → PIL resize + base64
    │     LLM multimodal call per campaign
    │
    ├── MultiJudgeEnsemble.evaluate_all()
    │     All (A,B) pairs × N judges, alternating A/B position per judge
    │     BT scores from Bradley-Terry model
    │
    ├── CampaignScorer.score()
    │     ProbabilityAggregator(judge_weights, persona_weights)
    │     DimensionEvaluator(brief_type_weights)   ← v2.1 new param
    │     _decide_verdict()
    │
    └── SummaryGenerator.generate()
    ↓
_evaluation_store[set_id] = result_dict  (under lock, dict-only)
save_result_fn(set_id, result_dict)       (outside lock, disk write)
TaskManager.complete_task()
    ↓
Frontend polls GET /api/campaign/evaluate/status/{task_id}
    ↓ status = COMPLETED
GET /api/campaign/result/{set_id}
    → result_dict + campaign_image_map injected
```

### Image Path Resolution (existing, must not break)

```
Upload: POST /api/campaign/upload-image
    → saved to: uploads/images/{set_id}/{campaign_id}__{uuid}__{filename}
    → returns:  {"url": "/api/campaign/image-file/{set_id}/{filename}"}

Evaluation:
    campaign.image_paths = ["/api/campaign/image-file/{set_id}/{filename}"]
    ↓
    resolve_image_path(url)
        if url starts with /api/campaign/image-file/:
            → uploads/images/{set_id}/{filename}  (filesystem path)
        elif absolute path: use directly
    ↓
    image_to_base64_part(path)
        PIL.Image.open() → resize to max 1024px → base64 encode
    ↓
    LLM multimodal call with {"type": "image_url", "image_url": {"url": "data:..."}}
```

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| 通义千问 via 百炼 | `LLMClient` wraps `openai.OpenAI(base_url=LLM_BASE_URL)` | Global `Semaphore(MAX_LLM_CONCURRENT=5)` prevents 429 |
| SQLite WAL | Direct `sqlite3` via `TaskManager` | WAL + busy_timeout; concurrent reads safe |

### Internal Boundaries

| Boundary | Communication | v2.1 change |
|----------|---------------|-------------|
| `api/campaign.py` ↔ `EvaluationOrchestrator` | Direct instantiation + thread dispatch | Add `brief_type` arg to `orchestrator.run()` |
| `EvaluationOrchestrator` ↔ `CampaignScorer` | Direct instantiation, passes `judge_weights/persona_weights` | Add `brief_type_weights` constructor arg |
| `EvaluationOrchestrator` ↔ `AudiencePanel` | Direct instantiation, passes `category` | No change |
| `PersonaRegistry` ↔ config files | File read at construction time | No change |
| Flask ↔ `frontend/dist` | `send_from_directory` via `os.path.abspath(FRONTEND_DIST)` | Add startup log of resolved path |

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-20 users (current) | Monolith is correct. ThreadPoolExecutor + global LLM Semaphore handles bursts. |
| 20-100 users | Gunicorn 2 workers × 4 threads (already configured). SQLite WAL handles concurrent reads. `_evaluation_store` is per-worker — disk fallback already implemented. |
| 100+ users | Migrate to Redis result cache, PostgreSQL task store, Celery queue. Out of scope. |

### Scaling Priorities

1. **First bottleneck:** LLM Semaphore (MAX_LLM_CONCURRENT=5 per worker = 10 total with 2 workers). Bailian rate limits are the real ceiling.
2. **Second bottleneck:** Per-worker in-process dict means cache misses always fall through to disk. Already handled correctly; adds ~1ms per result GET.

---

## Anti-Patterns

### Anti-Pattern 1: I/O or LLM calls inside `_store_lock`

**What people do:** Hold `_store_lock` while calling `_load_result()` or an LLM to "keep state consistent."

**Why it's wrong:** Blocks all other lock waiters for 30–300s. SQLite read or LLM call inside a threading.Lock will stall every concurrent result request.

**Do this instead:** Compute outside lock. Acquire lock only for dict read/write. File I/O always outside. Already implemented correctly as TD-01.

### Anti-Pattern 2: Silent failure when `frontend/dist` is missing

**What people do:** Rely on `if os.path.isdir(dist):` silently falling through when dist is absent. No error logged, no static routes mounted, `/` returns 404.

**Why it's wrong:** Impossible to diagnose in production without reading Flask logs carefully.

**Do this instead:**
```python
dist = os.path.abspath(FRONTEND_DIST)
if not os.path.isdir(dist):
    logger.warning(f"[STARTUP] frontend/dist not found at {dist} — / will 404")
else:
    logger.info(f"[STARTUP] frontend/dist found at {dist}")
    # ... mount routes
```

### Anti-Pattern 3: Embedding evaluation-level params in `campaign.extra`

**What people do:** Pass `brief_type` as `campaign.extra["brief_type"]` to avoid touching the evaluate payload schema.

**Why it's wrong:** `brief_type` is a CampaignSet-level concept. Putting it on individual campaigns creates inconsistency; campaigns within a set could have conflicting `brief_type` values. `extra` is for campaign-specific metadata, not evaluation routing.

**Do this instead:** Add `brief_type` as a top-level field on `POST /evaluate` payload. Extract with `data.get("brief_type")` in the route handler alongside the existing `category` extraction. Thread it through `orchestrator.run(brief_type=...)` → `CampaignScorer(brief_type_weights=...)`.

---

## v2.1 Specific Integration Points

### Fix 1: Static Serving 404

**Diagnosis:** In Docker, `__file__` = `/app/backend/app/__init__.py`. `FRONTEND_DIST` = `../../frontend/dist` relative to that → resolves to `/app/frontend/dist`. Dockerfile `COPY --from=frontend-build /app/frontend/dist /app/frontend/dist` targets exactly this path. The path computation is correct. Root cause of 404 is either: (a) `npm run build` failed silently in CI and an empty/missing `dist/` was copied, or (b) a deployment to Vercel/serverless where the filesystem is ephemeral and the `dist/` COPY never persists.

**Immediate fix:** Add startup log of resolved `dist` path in `app/__init__.py`. Platform migration (Vercel → Railway) is the structural fix.

### Fix 2: Brief-Type Dimension Weight Routing

**Insertion point:** `CampaignScorer.__init__()` already takes `judge_weights` and `persona_weights`. Add `brief_type_weights: Dict[str, float] = None`. Forward to `DimensionEvaluator` or apply as a post-weighting multiplier on `dimension_results`.

**Weight config location:** New file `backend/app/config/brief_type_weights.json`:
```json
{
  "brand":      {"thumb_stop": 0.35, "trust": 0.35, "clarity": 0.20, "conversion_readiness": 0.05, "claim_risk": 0.05},
  "awareness":  {"thumb_stop": 0.40, "clarity": 0.30, "trust": 0.20, "conversion_readiness": 0.05, "claim_risk": 0.05},
  "conversion": {"conversion_readiness": 0.40, "trust": 0.25, "clarity": 0.20, "thumb_stop": 0.10, "claim_risk": 0.05}
}
```

**No API breakage:** `brief_type=None` falls back to current uniform weighting. Frontend passes `brief_type` as an optional field on the evaluate form.

### Fix 3: Benchmark Dataset + Regression Test Runner

**Storage:** `backend/tests/fixtures/benchmark/{id}/` — one directory per benchmark case:
- `input.json` — `CampaignSet` serialized
- `expected.json` — `{winner_campaign_id, min_winner_score, max_runner_up_score}`
- `llm_responses.json` — pre-recorded LLM call/response pairs for deterministic replay

**Integration:** New pytest file `backend/tests/test_benchmark_regression.py`:
1. Loads all fixture directories
2. Patches `LLMClient.chat_json` and `chat_multimodal_json` to replay recorded responses
3. Calls `EvaluationOrchestrator.run()` in-process (no HTTP)
4. Asserts `winner_campaign_id` matches expected
5. Reports hit rate across all fixtures

**Hit rate target:** Establish baseline on first run; regression threshold = baseline - 10%.

---

## Sources

- Direct source inspection: `backend/app/__init__.py`, `api/campaign.py`, `services/evaluation_orchestrator.py`, `services/campaign_scorer.py`, `services/persona_registry.py`, `services/audience_panel.py`, `services/brief_parser.py`, `config.py`, `Dockerfile`
- Project constraints: `.planning/PROJECT.md` (v2.1 milestone goals, existing architecture decisions)
- Dockerfile: multi-stage build confirms `/app/frontend/dist` as the correct dist path inside the container

---
*Architecture research for: MiroFishmoody v2.1 deployment fix + brief-type evaluation*
*Researched: 2026-03-18*
