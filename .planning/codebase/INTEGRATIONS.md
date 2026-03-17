# External Integrations

**Analysis Date:** 2026-03-17

## LLM / AI

**Primary LLM Provider:**
- OpenAI-compatible API — all inference calls go through `backend/app/utils/llm_client.py`
- Client: `openai>=1.0.0` SDK (`OpenAI(api_key=..., base_url=...)`)
- Auth env var: `LLM_API_KEY`
- Endpoint env var: `LLM_BASE_URL` (default: `https://api.openai.com/v1`)
- Model env var: `LLM_MODEL_NAME` (default: `gpt-4o-mini`)
- Actual deployment uses Qwen via Alibaba Bailian endpoint (documented in `CLAUDE.md`: "LLM: Qwen via OpenAI SDK (Bailian endpoint)")
- Supports multimodal (vision) via `chat_multimodal` / `chat_multimodal_json` methods — images encoded as base64 in OpenAI Vision message format
- Response cleaning strips `<think>...</think>` blocks for chain-of-thought models (e.g. MiniMax M2.5, noted in `llm_client.py`)
- Structured JSON output via `response_format: {"type": "json_object"}`

**LLM Usage Sites:**
- `backend/app/services/pairwise_judge.py` — 3-judge panel for campaign pair ranking (concurrent via `ThreadPoolExecutor`)
- `backend/app/services/image_analyzer.py` — visual asset analysis (multimodal, base64 images)
- `backend/app/services/audience_panel.py` — simulated consumer panel scoring
- `backend/app/services/brand_state_engine.py` — brand state construction from signals
- `backend/app/services/summary_generator.py` — human-readable evaluation summaries
- `backend/app/services/market_judge.py` — market-making judge (experimental, `USE_MARKET_JUDGE=false`)
- `backend/app/services/submarket_evaluator.py` — submarket scoring

## Data Storage

**Databases:**
- SQLite (stdlib `sqlite3`) — two separate database files:
  - `backend/uploads/brandiction.db` — historical intervention data, outcomes, signals, brand states, competitor events, evidence, race runs; managed by `backend/app/services/brandiction_store.py` (singleton, thread-safe)
  - `backend/uploads/tasks.db` — async task status tracking; managed by `backend/app/models/task.py` (TaskManager singleton)
- Both use WAL mode implicit behavior with `PRAGMA foreign_keys = ON`
- No external DB service; files are local to the container, persisted via Docker volume

**File Storage:**
- Local filesystem at `backend/uploads/` (absolute path from `Config.UPLOAD_FOLDER`)
- Uploaded files: PDF briefs, markdown docs, JSON, TXT (max 50MB per request)
- Images: stored under `backend/uploads/images/` — served back via URL for multimodal analysis
- Results/reports: stored under `backend/uploads/results/` and `backend/uploads/calibration/predictions/`
- In production: Docker named volume `uploads-data` mounts to `/app/backend/uploads`

**Caching:**
- None — no Redis, Memcached, or in-memory cache layer
- Race result state passed between frontend pages via `localStorage` (`RACE_STATE_KEY` in `frontend/src/lib/api.ts`)

## Authentication & Identity

**Auth Provider:**
- Custom — no external OAuth/SSO provider
- Implementation: Flask `session` (server-side signed cookie) + `SECRET_KEY`
- User table loaded from env var `MOODY_USERS` at startup — format: `username:password:display_name:role,...`
- Passwords stored in plaintext in env var (internal beta tool, noted limitation)
- Session invalidation on password change via SHA-256 version hash (`backend/app/auth.py`)
- Roles: `admin` (full access including `/admin/*` routes) and `user`
- Decorators: `@login_required`, `@admin_required` in `backend/app/auth.py`

## External Web Scraping / Browser Automation

**Meta Ad Library Reviewer (script, not production API):**
- Tool: Playwright with persistent Chromium session
- Script: `backend/scripts/review_meta_ad_library.py`
- Purpose: semi-automated evidence collection for competitor events from Meta Ad Library
- Persistent browser session stored at `backend/.playwright_meta_session/`
- Requires manual CAPTCHA solving on first run; subsequent runs reuse session
- Not integrated into the Flask API — run standalone via `uv run python review_meta_ad_library.py`

**Competitor Event Collector (script, not production API):**
- Script: `backend/scripts/collect_competitor_events.py`
- Purpose: scrapes competitor brand pages (HTTP only, no browser) to draft competitor event CSV
- Sources: `official_site`, `meta_ad_library`, `google_ads_transparency`, `tiktok_creative_center`, `manual_note`
- Uses stdlib `urllib.request` — no external HTTP client dependency
- Output: draft CSV at `backend/uploads/competitor_events_draft.csv` for human review before import

## Monitoring & Observability

**Error Tracking:**
- None — no Sentry, Datadog, or external error tracking service

**Logs:**
- Custom rotating file logger: `backend/app/utils/logger.py`
- Log files: `backend/logs/YYYY-MM-DD.log` (max 10MB per file, 5 backups)
- Dual output: file (DEBUG+) and stdout console (INFO+)
- Audit log: every write (`POST`/`PUT`/`DELETE`) and export request logged with user, method, path, status, IP via `after_request` hook in `backend/app/__init__.py`
- Logger names: `ranker`, `ranker.request`, `ranker.audit`, `ranker.pairwise_judge`, `ranker.image_analyzer`, etc.

## CI/CD & Deployment

**Hosting:**
- Docker container; deployment target is any Docker-capable host (VPS, cloud VM)
- Nginx optional reverse proxy with TLS (`nginx.conf.template`)

**CI Pipeline:**
- GitHub Actions: `.github/workflows/docker-image.yml`
- Trigger: git tag push or manual `workflow_dispatch`
- Steps: checkout → QEMU setup → Buildx setup → GHCR login → metadata extraction → multi-platform build + push
- Registry: `ghcr.io/{owner}/mirofish`
- Tags: git tag ref, SHA, `latest`

## Environment Configuration

**Required env vars:**
- `LLM_API_KEY` — LLM provider API key
- `SECRET_KEY` — Flask session signing key
- `MOODY_USERS` — user table (format: `username:password:display_name:role,...`)

**Optional env vars with defaults:**
- `LLM_BASE_URL` (default: `https://api.openai.com/v1`)
- `LLM_MODEL_NAME` (default: `gpt-4o-mini`)
- `JUDGE_TEMPERATURE` (default: `0.3`)
- `PANEL_TEMPERATURE` (default: `0.4`)
- `MAX_CAMPAIGNS` (default: `6`)
- `USE_MARKET_JUDGE` (default: `false`)
- `FLASK_DEBUG` (default: `True` in dev, overridden to `False` in docker-compose)
- `FLASK_HOST` (default: `0.0.0.0`)
- `FLASK_PORT` (default: `5001`)

**Secrets location:**
- `.env` file at project root (gitignored)
- `.env.production` present at project root (existence noted — contents never read)
- In CI: `GITHUB_TOKEN` (auto-provided) for GHCR push

## Webhooks & Callbacks

**Incoming:**
- None — no webhook endpoints

**Outgoing:**
- None — all LLM calls are synchronous request/response

---

*Integration audit: 2026-03-17*
