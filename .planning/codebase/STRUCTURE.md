# Codebase Structure

**Analysis Date:** 2026-03-17

## Directory Layout

```
MiroFishmoody/                     # Project root
├── backend/                       # Python/Flask backend
│   ├── app/                       # Application package
│   │   ├── __init__.py            # Flask app factory (create_app)
│   │   ├── auth.py                # Login/session decorators
│   │   ├── config.py              # Config class (reads .env)
│   │   ├── api/                   # HTTP route handlers (blueprints)
│   │   │   ├── __init__.py        # Exports campaign_bp
│   │   │   ├── auth.py            # /api/auth routes
│   │   │   ├── campaign.py        # /api/campaign routes
│   │   │   └── brandiction.py     # /api/brandiction routes
│   │   ├── models/                # Pure dataclasses (no I/O)
│   │   │   ├── campaign.py        # Campaign, CampaignSet, ProductLine
│   │   │   ├── task.py            # Task, TaskManager (SQLite singleton)
│   │   │   ├── evaluation.py      # EvaluationResult, PanelScore, etc.
│   │   │   ├── scoreboard.py      # Scoreboard, ScoreboardEntry
│   │   │   ├── brandiction.py     # HistoricalIntervention, OutcomeWindow, Signal, etc.
│   │   │   └── brand_state.py     # BrandState, PerceptionVector, StateTransition
│   │   ├── services/              # Business logic
│   │   │   ├── evaluation_orchestrator.py  # 4-phase async eval pipeline
│   │   │   ├── audience_panel.py           # 5-persona LLM scoring
│   │   │   ├── pairwise_judge.py           # All-pairs tournament judge
│   │   │   ├── market_judge.py             # Alt judge (USE_MARKET_JUDGE=true)
│   │   │   ├── campaign_scorer.py          # Bradley-Terry score aggregation
│   │   │   ├── summary_generator.py        # LLM narrative summary
│   │   │   ├── brief_parser.py             # NL brief → structured Campaign fields
│   │   │   ├── judge_calibration.py        # Judge/persona weight calibration
│   │   │   ├── resolution_tracker.py       # Post-campaign actual result tracking
│   │   │   ├── baseline_ranker.py          # Historical data–based ranking (Track 1)
│   │   │   ├── brand_state_engine.py       # Cognitive model / BrandState (Track 2)
│   │   │   ├── brandiction_store.py        # SQLite store for all historical data
│   │   │   ├── historical_importer.py      # JSON/CSV import into brandiction.db
│   │   │   ├── image_analyzer.py           # LLM vision → VisualProfile
│   │   │   ├── agent_diffusion.py          # Social diffusion simulation
│   │   │   ├── audience_panel.py           # Audience panel scoring
│   │   │   ├── probability_aggregator.py   # Probability board aggregation
│   │   │   ├── submarket_evaluator.py      # Sub-market evaluation
│   │   │   └── text_processor.py           # Text preprocessing utilities
│   │   └── utils/                 # Shared infrastructure
│   │       ├── llm_client.py      # LLMClient (OpenAI-compatible wrapper)
│   │       ├── logger.py          # Structured logger setup
│   │       ├── retry.py           # retry_with_backoff decorator
│   │       └── file_parser.py     # File parsing utilities
│   ├── scripts/                   # One-off admin/ETL scripts (not served)
│   │   ├── import_etl.py
│   │   ├── sync_etl_enrichment.py
│   │   ├── repair_brandiction_data.py
│   │   ├── collect_competitor_events.py
│   │   └── review_meta_ad_library.py
│   ├── tests/                     # pytest test suite
│   ├── uploads/                   # Runtime data (gitignored except structure)
│   │   ├── tasks.db               # SQLite: task tracking (TaskManager)
│   │   ├── brandiction.db         # SQLite: historical data spine (BrandictionStore)
│   │   ├── images/                # Uploaded campaign creative assets
│   │   │   └── <set_id>/          # Per-evaluation-set subdirectory
│   │   ├── results/               # Persisted evaluation results as JSON
│   │   │   └── <set_id>.json
│   │   ├── calibration/           # Judge calibration data
│   │   └── templates/             # Brief/report templates
│   ├── run.py                     # Dev server entry point
│   ├── pyproject.toml             # uv/Python project config
│   └── requirements.txt           # Python dependencies
├── frontend/                      # React/TypeScript SPA
│   ├── src/
│   │   ├── main.tsx               # DOM entry point
│   │   ├── App.tsx                # Auth gate + router definition
│   │   ├── store.ts               # Zustand store (useReviewStore)
│   │   ├── utils.ts               # uuid() and other helpers
│   │   ├── index.css              # Global styles + Tailwind base
│   │   ├── lib/
│   │   │   ├── api.ts             # ALL API calls + shared types + localStorage state
│   │   │   └── useAsync.ts        # Generic async hook
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx      # Auth form
│   │   │   ├── HomePage.tsx       # Campaign plan builder + race submit
│   │   │   ├── RunningPage.tsx    # Race progress (calls /api/brandiction/race)
│   │   │   ├── ResultPage.tsx     # Race result display
│   │   │   ├── DashboardPage.tsx  # Admin: stats + brandiction overview
│   │   │   └── HistoryPage.tsx    # Admin: race history + resolution
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Layout.tsx     # Shell with nav
│   │   │   │   └── AppShell.tsx   # Wrapper layout
│   │   │   └── ui/
│   │   │       ├── SectionCard.tsx
│   │   │       ├── StateOverlay.tsx
│   │   │       └── StatusBadge.tsx
│   │   └── data/
│   │       └── campaignDecisionData.ts  # Static reference data
│   ├── dist/                      # Built SPA (gitignored, served by Flask in prod)
│   ├── index.html                 # Vite HTML template
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── package.json
├── docs/                          # Documentation
├── static/                        # Legacy static assets (pre-SPA)
├── .env.example                   # Required env var template
├── .env.production                # Production env config
├── docker-compose.yml             # Docker deployment
├── Dockerfile
├── nginx.conf.template            # Nginx reverse proxy config
├── package.json                   # Root package.json (npm run dev, build, setup)
├── CLAUDE.md                      # Project contract (read before coding)
└── DEPLOY.md
```

## Directory Purposes

**`backend/app/api/`:**
- Purpose: HTTP layer only — parse request, call service, return JSON
- Contains: Flask Blueprint handlers; no business logic
- Key files: `campaign.py` (evaluate, upload-image, results, calibration), `brandiction.py` (race, predict, import, BrandState), `auth.py` (login/logout/me)

**`backend/app/services/`:**
- Purpose: All domain logic — LLM calls, scoring, data queries, state machine
- Contains: Orchestrators, judges, rankers, stores, analyzers
- Key files: `evaluation_orchestrator.py`, `baseline_ranker.py`, `brand_state_engine.py`, `brandiction_store.py`, `image_analyzer.py`

**`backend/app/models/`:**
- Purpose: Data model definitions — pure dataclasses with `to_dict()` / `from_dict()`
- Contains: No I/O, no business logic; just structure
- Key files: `campaign.py` (Campaign, CampaignSet), `task.py` (Task, TaskManager), `brandiction.py` (HistoricalIntervention, OutcomeWindow, Signal)

**`backend/uploads/`:**
- Purpose: All runtime-generated data — SQLite databases, uploaded images, results
- Generated: Yes (at runtime)
- Committed: No (gitignored), except directory structure markers

**`backend/scripts/`:**
- Purpose: Admin ETL and data maintenance scripts; run manually, not served
- Not imported by the application

**`frontend/src/lib/`:**
- Purpose: All backend communication and cross-page state
- Key file: `api.ts` — defines every API function, all TypeScript types mirroring backend, and localStorage helpers (`saveRaceState`/`getRaceState`)
- Rule: Components must import from here, never call `fetch` directly

**`frontend/src/pages/`:**
- Purpose: Route-level page components — one per app route
- Key flow: `HomePage` → `RunningPage` → `ResultPage`

**`frontend/src/store.ts`:**
- Purpose: Zustand global store for the review/jury flow (separate from race flow)
- Used by: Pages that use the LLM jury evaluation pathway (`/api/campaign/evaluate`)

## Key File Locations

**Entry Points:**
- `backend/run.py`: Python dev server launch
- `backend/app/__init__.py`: Flask factory (`create_app`)
- `frontend/src/main.tsx`: React DOM mount
- `frontend/src/App.tsx`: Auth gate + route tree

**Configuration:**
- `backend/app/config.py`: All env var consumption (`LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL_NAME`, `MOODY_USERS`, etc.)
- `.env.example`: All required variables with documentation
- `package.json` (root): Dev scripts (`npm run dev`, `npm run build`, `npm run setup:all`)

**Core Logic:**
- `backend/app/services/evaluation_orchestrator.py`: Async jury pipeline
- `backend/app/services/baseline_ranker.py`: Historical data ranking (Track 1)
- `backend/app/services/brand_state_engine.py`: Cognitive model (Track 2)
- `backend/app/services/image_analyzer.py`: Visual asset LLM analysis
- `frontend/src/lib/api.ts`: Complete API contract + types

**Testing:**
- `backend/tests/`: pytest suite
- Run: `cd backend && uv run pytest`

## Naming Conventions

**Files (backend):**
- `snake_case.py` for all Python files
- Services named by responsibility: `<subject>_<verb>.py` (e.g., `campaign_scorer.py`, `brand_state_engine.py`)
- Models named by domain noun: `campaign.py`, `task.py`, `brandiction.py`

**Files (frontend):**
- `PascalCase.tsx` for React components and pages
- `camelCase.ts` for non-component TypeScript (e.g., `api.ts`, `store.ts`, `utils.ts`)
- Pages suffixed with `Page`: `HomePage.tsx`, `ResultPage.tsx`

**Directories:**
- Backend: lowercase with underscores where needed
- Frontend: lowercase (e.g., `pages/`, `components/`, `lib/`)

## Where to Add New Code

**New API endpoint:**
- Add route handler to appropriate file in `backend/app/api/` (or create new blueprint)
- Register new blueprint in `backend/app/__init__.py`
- Add corresponding function + TypeScript type in `frontend/src/lib/api.ts`

**New business logic:**
- Create service in `backend/app/services/<name>.py`
- Call from API handler; never put logic in route handler directly

**New data model:**
- Add dataclass to `backend/app/models/<domain>.py`
- Add `to_dict()` / `from_dict()` methods for JSON serialization

**New frontend page:**
- Create `frontend/src/pages/<Name>Page.tsx`
- Register route in `frontend/src/App.tsx` under `routes` array (add `admin_required` guard if admin-only)

**New reusable UI component:**
- Create in `frontend/src/components/ui/<ComponentName>.tsx`
- Layout-level wrappers go in `frontend/src/components/layout/`

**New admin ETL script:**
- Add to `backend/scripts/`
- Do not import from scripts in the application package

**New tests:**
- Add to `backend/tests/`
- Follow existing pytest patterns in that directory

## Special Directories

**`backend/uploads/`:**
- Purpose: All runtime data — SQLite DBs, uploaded images, results JSON, calibration data
- Generated: Yes (auto-created at startup by `os.makedirs`)
- Committed: No (in `.gitignore`)

**`frontend/dist/`:**
- Purpose: Vite production build output — served by Flask in production mode
- Generated: Yes (`npm run build`)
- Committed: No (in `frontend/.gitignore`)

**`backend/.playwright_meta_session/`:**
- Purpose: Playwright browser session cache for competitor event collection script
- Generated: Yes
- Committed: No

**`.claude/`:**
- Purpose: Claude agent skills, commands, and hooks for this project
- Generated: No (manually maintained)
- Committed: Yes

---

*Structure analysis: 2026-03-17*
