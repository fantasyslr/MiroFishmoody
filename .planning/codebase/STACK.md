# Technology Stack

**Analysis Date:** 2026-03-17

## Languages

**Primary:**
- Python 3.11+ — backend application, all business logic, services, models
- TypeScript 5.9 — frontend application, all UI components and API types

**Secondary:**
- CSS (Tailwind utility classes) — frontend styling
- SQL — SQLite schema definitions inline in `backend/app/services/brandiction_store.py` and `backend/app/models/task.py`

## Runtime

**Backend Environment:**
- Python 3.11+ (enforced in `backend/pyproject.toml`: `requires-python = ">=3.11"`)
- Package manager: `uv` (lockfile: `backend/uv.lock`)
- Dev run: `uv run python run.py`
- Production run: `gunicorn` (2 workers, 4 threads, 300s timeout)

**Frontend Environment:**
- Node.js >=18.0.0 (declared in root `package.json` `engines` field)
- Package manager: `npm` (lockfile: `frontend/package-lock.json`)
- Dev server: Vite 8.x (`npm run dev` → `vite --host`)
- Build: `tsc -b && vite build`

**Monorepo Orchestration:**
- Root `package.json` uses `concurrently` to run both processes
- `npm run dev` → launches backend (uv) + frontend (vite) together
- `npm run setup:all` — installs all dependencies

## Frameworks

**Backend Core:**
- Flask 3.0+ — HTTP server, routing, session management (`backend/app/__init__.py`)
- Flask-CORS 6.0+ — CORS headers for `/api/*` with `credentials: true`

**Backend Build:**
- Hatchling — build backend for `pyproject.toml` (`backend/pyproject.toml`)
- Gunicorn 22.0+ — production WSGI server (`Dockerfile`)

**Frontend Core:**
- React 19.x — UI rendering (`frontend/src/App.tsx`, `frontend/src/main.tsx`)
- React Router DOM 7.x — hash-based routing (`createHashRouter` in `App.tsx`)
- Zustand 5.x — client-side state management (`frontend/src/store.ts`)

**Frontend Build:**
- Vite 8.x — dev server + production bundler (`frontend/vite.config.ts`)
- `@vitejs/plugin-react` 6.x — React/JSX transform

**Frontend Styling:**
- Tailwind CSS 3.4 (`frontend/tailwind.config.js`, `frontend/postcss.config.js`)
- `tailwind-merge` 3.5 + `clsx` 2.1 — conditional class utilities
- `lucide-react` 0.577 — icon library
- `motion` 12.x — animation library (Framer Motion fork)

**Testing:**
- pytest 8.0+ — backend test runner (`backend/tests/`)
- pytest-asyncio 0.23+ — async test support

**Linting:**
- ESLint 9.x with `typescript-eslint` (`frontend/eslint.config.js`)
- `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`

## Key Dependencies

**Critical:**
- `openai>=1.0.0` — LLM API client (OpenAI SDK used for any OpenAI-compatible endpoint; `backend/app/utils/llm_client.py`)
- `pydantic>=2.0.0` — data validation
- `PyMuPDF>=1.24.0` — PDF parsing for campaign brief uploads
- `Pillow>=10.0.0` — image processing for visual analysis uploads
- `python-dotenv>=1.0.0` — `.env` file loading

**Infrastructure:**
- `charset-normalizer>=3.0.0` + `chardet>=5.0.0` — encoding detection for non-UTF-8 text file uploads
- `playwright` (scripts only, not in main requirements) — browser automation for Meta Ad Library review script (`backend/scripts/review_meta_ad_library.py`)
- `yaml` (pyyaml, scripts only) — competitor watchlist config parsing (`backend/scripts/collect_competitor_events.py`)

## Configuration

**Environment:**
- All config via `.env` file loaded by `backend/app/config.py` using `python-dotenv`
- Template: `.env.example` at project root
- Production template: `.env.production` at project root (existence only — not read)
- Config class: `backend/app/config.py` → `Config`
- Required vars: `LLM_API_KEY`, `SECRET_KEY`, `MOODY_USERS`
- Optional vars: `LLM_BASE_URL`, `LLM_MODEL_NAME`, `JUDGE_TEMPERATURE`, `PANEL_TEMPERATURE`, `MAX_CAMPAIGNS`, `USE_MARKET_JUDGE`, `FLASK_DEBUG`, `FLASK_HOST`, `FLASK_PORT`
- Frontend env: `VITE_API_BASE_URL` (optional, defaults to empty → relative paths)

**Build:**
- Backend: `backend/pyproject.toml` (hatchling)
- Frontend: `frontend/tsconfig.json`, `frontend/tsconfig.app.json`, `frontend/tsconfig.node.json`
- Docker: multi-stage `Dockerfile` (Node 20 build stage + Python 3.11-slim runtime)

## Platform Requirements

**Development:**
- Python 3.11+, Node.js 18+, `uv` installed globally
- `npm run setup:all` to bootstrap all dependencies
- `npm run dev` to start both backend (port 5001) and frontend (Vite default port)

**Production:**
- Docker + Docker Compose (`docker-compose.yml`) — single service `moody-campaign-engine`
- Flask serves frontend dist at runtime (no separate web server required for static files)
- Optional Nginx reverse proxy via `nginx.conf.template` (TLS termination, proxy to port 5001)
- Container: `ghcr.io/{owner}/mirofish` — published via GitHub Actions on tag push
- Uploads persisted via Docker named volume `uploads-data` → `/app/backend/uploads`
- Health endpoint: `GET /health` (checks DB connectivity, disk space, upload dir writability)

---

*Stack analysis: 2026-03-17*
