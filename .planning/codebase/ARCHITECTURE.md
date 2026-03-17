# Architecture

**Analysis Date:** 2026-03-17

## Pattern Overview

**Overall:** Layered monolith with async task execution

**Key Characteristics:**
- Flask backend serves both REST API and (in production) the built React SPA from `frontend/dist/`
- Two distinct API subsystems with separate concerns: `/api/campaign` (LLM-based jury evaluation) and `/api/brandiction` (historical data spine + prediction engine)
- Long-running LLM evaluations run in daemon threads, tracked via SQLite-backed `TaskManager` (singleton)
- All business logic in `services/`, routes in `api/` contain only request parsing and response formatting
- Two SQLite databases: `uploads/tasks.db` (task tracking) and `uploads/brandiction.db` (historical data spine)

## Layers

**API Layer:**
- Purpose: HTTP routing, request validation, response serialization
- Location: `backend/app/api/`
- Contains: Flask blueprints — `campaign.py`, `brandiction.py`, `auth.py`
- Depends on: services layer, models, auth decorators
- Used by: React frontend via `fetch` in `frontend/src/lib/api.ts`
- Rule: No business logic here. Parse input, call service, return JSON.

**Services Layer:**
- Purpose: All business logic, LLM calls, scoring, data access
- Location: `backend/app/services/`
- Contains: Orchestrators, judges, scorers, stores, rankers, analyzers
- Depends on: models, utils (LLMClient, logger, retry)
- Used by: API layer only

**Models Layer:**
- Purpose: Data structures and enums — pure dataclasses
- Location: `backend/app/models/`
- Contains: `Campaign`, `CampaignSet`, `ProductLine`, `Task`, `EvaluationResult`, `BrandState`, `HistoricalIntervention`, etc.
- Depends on: nothing
- Used by: services and api layers

**Utils Layer:**
- Purpose: Shared infrastructure
- Location: `backend/app/utils/`
- Contains: `LLMClient` (OpenAI-compatible wrapper), `logger`, `retry`, `file_parser`
- Depends on: `Config`
- Used by: services layer

**Frontend:**
- Purpose: React SPA for campaign input, race execution, and result display
- Location: `frontend/src/`
- Contains: pages, shared UI components, API client (`lib/api.ts`), Zustand store
- Rule: All API calls go through `frontend/src/lib/api.ts` — never call `fetch` directly in components

## Data Flow

**Campaign Race (primary user flow):**

1. User fills campaign plans in `HomePage` (React), optionally uploads images
2. Images uploaded to `POST /api/campaign/upload-image`, stored in `uploads/images/<set_id>/`
3. On submit, payload saved to `localStorage` via `saveRaceState()`, user navigated to `/running`
4. `RunningPage` reads payload from `localStorage`, calls `POST /api/brandiction/race`
5. Backend `race_campaigns()` handler runs synchronously:
   - Track 1: `HistoricalBaselineRanker.rank_campaigns()` — matches historical intervention records, computes observed metrics (ROAS, CVR, purchase_rate, etc.)
   - Image analysis: `ImageAnalyzer.analyze_plan_images()` — LLM vision call per plan with images, returns `VisualProfile`
   - Visual adjustment: `apply_visual_adjustment()` — modifies baseline scores by visual quality delta
   - Track 2 (optional): `BrandStateEngine.predict_impact()` per plan — cognitive model hypothesis
6. Result returned as `RaceResult` JSON, saved to `localStorage` via `saveRaceState()`
7. Frontend navigated to `/result`, `ResultPage` reads from `localStorage`

**Async Campaign Evaluation (legacy/audit flow):**

1. `POST /api/campaign/evaluate` — parses `CampaignSet`, creates `Task`, spawns daemon thread
2. `EvaluationOrchestrator.run()` executes 4 phases:
   - Phase 1: `AudiencePanel.evaluate_all()` — 5 Moody Lenses personas score each campaign (parallel LLM calls)
   - Phase 2: `PairwiseJudge.evaluate_all()` (or `MarketJudge` if `USE_MARKET_JUDGE=true`) — all-pairs tournament
   - Phase 3: `CampaignScorer.score()` — Bradley-Terry model combining panel + pairwise scores
   - Phase 4: `SummaryGenerator.generate()` — LLM summary narrative
3. Result stored in memory `_evaluation_store` dict AND persisted to `uploads/results/<set_id>.json`
4. Frontend polls `GET /api/campaign/evaluate/status/<task_id>` → navigates to result on completion

**Brandiction Historical Data Flow:**

1. Admin imports via `POST /api/brandiction/import-json` or `POST /api/brandiction/import-csv`
2. `HistoricalImporter` parses and writes to `BrandictionStore` (SQLite `brandiction.db`)
3. `BrandStateEngine.replay_history()` processes interventions chronologically → builds `BrandState` time series
4. `HistoricalBaselineRanker.rank_campaigns()` queries `BrandictionStore` for matching historical groups → computes `BaselineStats`

**State Management (Frontend):**
- Session auth state: `useState` in `App.tsx`, passed via React Router `<Layout>`
- Campaign form state: page-local `useState` in `HomePage`
- Race payload/result cross-page: `localStorage` via `saveRaceState()`/`getRaceState()` in `lib/api.ts`
- Zustand store (`store.ts`): `useReviewStore` — alternative plan/image builder (used for the LLM jury flow, separate from the race flow in `HomePage`)

## Key Abstractions

**EvaluationOrchestrator:**
- Purpose: Coordinates the 4-phase async LLM jury pipeline
- Location: `backend/app/services/evaluation_orchestrator.py`
- Pattern: Takes injected dependencies (`task_manager`, `evaluation_store`, `save_result_fn`) — testable

**BrandStateEngine:**
- Purpose: Cognitive perception model — predicts how an intervention shifts brand state dimensions
- Location: `backend/app/services/brand_state_engine.py`
- Pattern: Queries `BrandictionStore`, applies delta model, supports replay/backtest/simulate

**HistoricalBaselineRanker:**
- Purpose: Evidence-based campaign ranking using real outcome data (ROAS, CVR, purchase_rate)
- Location: `backend/app/services/baseline_ranker.py`
- Pattern: Multi-dimension match → statistical aggregation → cold-start fallback chain

**TaskManager:**
- Purpose: Thread-safe singleton tracking async task status
- Location: `backend/app/models/task.py`
- Pattern: Singleton with SQLite persistence; tasks stuck in PROCESSING at startup are auto-marked FAILED

**BrandictionStore:**
- Purpose: SQLite persistence for all historical marketing data
- Location: `backend/app/services/brandiction_store.py`
- Pattern: Singleton; merge semantics on save (non-destructive upsert)

**LLMClient:**
- Purpose: Unified OpenAI-compatible wrapper for all LLM calls
- Location: `backend/app/utils/llm_client.py`
- Pattern: Instantiated per-service-call; reads config from `Config` class

## Entry Points

**Backend:**
- Location: `backend/run.py`
- Triggers: `uv run python run.py` or `npm run backend`
- Responsibilities: Calls `create_app()` factory, starts Flask dev server

**Application Factory:**
- Location: `backend/app/__init__.py`
- Triggers: Called by `run.py` and by gunicorn/production
- Responsibilities: Registers 3 blueprints (`/api/campaign`, `/api/auth`, `/api/brandiction`), configures CORS, sets up audit logging, serves `frontend/dist` as static SPA in production

**Frontend:**
- Location: `frontend/src/main.tsx`
- Triggers: Vite dev server (`npm run frontend`) or built into `frontend/dist/`
- Responsibilities: Mounts `<App>` into DOM

**Auth Check:**
- Location: `frontend/src/App.tsx`
- Triggers: Every page load
- Responsibilities: Calls `GET /api/auth/me`, gates all routes behind login, splits admin routes by `user.role === 'admin'`

## Error Handling

**Strategy:** Explicit try/except in API handlers; services raise ValueError for validation, RuntimeError for execution failures

**Patterns:**
- `ValueError` → 400 JSON `{"error": "..."}`
- `Exception` (unexpected) → 500 JSON `{"error": "内部错误: {str(e)}"}` + `logger.error(..., exc_info=True)`
- LLM failures in parallel calls (AudiencePanel) → individual failures logged, partial results used; if ALL fail → `RuntimeError` propagated
- Task stuck at restart → `TaskManager._load_all_from_db()` auto-marks PROCESSING/PENDING as FAILED

## Cross-Cutting Concerns

**Logging:** Structured via `backend/app/utils/logger.py`. Logger names follow `ranker.*` hierarchy (e.g., `ranker.api.campaign`, `ranker.services.orchestrator`). Audit log written on all write ops and export calls, recording user/method/path/status/IP.

**Validation:** Input validation in API handlers (request parsing) and service constructors. `CampaignSet` and `BrandictionStore` validate on write.

**Authentication:** Flask session-based (`session['user']`). User table loaded from `MOODY_USERS` env var at startup. Decorators: `@login_required`, `@admin_required` in `backend/app/auth.py`. Password change auto-invalidates existing sessions via `_pw_ver` hash.

**Image Handling:** Upload to `uploads/images/<set_id>/<campaign_id>__<uuid>__<filename>`. PIL resize to max 1024px if available. Path traversal guard on save. Images served authenticated via `GET /api/campaign/image-file/<set_id>/<filename>`.

---

*Architecture analysis: 2026-03-17*
