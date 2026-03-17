# Codebase Concerns

**Analysis Date:** 2026-03-17

---

## Tech Debt

**In-memory evaluation store has no eviction policy:**
- Issue: `_evaluation_store: dict = {}` in `backend/app/api/campaign.py` (line 36) grows unbounded. Results are also persisted to disk as JSON files in `backend/uploads/results/`, but the in-memory dict never clears old entries.
- Files: `backend/app/api/campaign.py`
- Impact: Long-running server processes will leak memory proportional to number of evaluations.
- Fix approach: Add an LRU or TTL eviction to `_evaluation_store`; the disk JSON files already provide full persistence so eviction is safe.

**Singleton pattern on BrandictionStore and TaskManager breaks testability:**
- Issue: Both `BrandictionStore` and `TaskManager` use module-level singleton (`_instance = None` + `__new__`) that persists across test invocations. Test isolation requires explicit teardown.
- Files: `backend/app/services/brandiction_store.py`, `backend/app/models/task.py`
- Impact: Tests that mutate DB state can bleed into subsequent tests. Already caused repair scripts (`scripts/repair_brandiction_data.py`).
- Fix approach: Accept optional `db_path` constructor arg (already partially done in `BrandictionStore`) and expose a `reset_singleton()` classmethod for test fixtures.

**Calibration data stored as flat files, not in SQLite:**
- Issue: `JudgeCalibration` writes `predictions/{set_id}.json`, `resolutions.jsonl`, and `judge_stats.json` to `backend/uploads/calibration/` as raw files. This is a separate persistence layer from the main `brandiction.db` and `tasks.db`.
- Files: `backend/app/services/judge_calibration.py`
- Impact: Backup/restore requires handling three separate storage layers. No transactional consistency.
- Fix approach: Migrate calibration tables into `brandiction.db`.

**`brand_state_engine.py` is 1319 lines — God class risk:**
- Issue: `BrandStateEngine` handles state construction, replay, prediction, scenario simulation, diffusion, and backtesting in a single class.
- Files: `backend/app/services/brand_state_engine.py`
- Impact: Hard to test individual behaviors; any change to one prediction path risks breaking another.
- Fix approach: Extract `ScenarioSimulator`, `BacktestEngine`, and `DiffusionOrchestrator` as separate classes.

**`BaselineRanker` loads all interventions into memory on every call:**
- Issue: `_query_same_category()` calls `self.store.list_interventions()` with no filter, pulling the entire interventions table into Python memory, then filters in-application.
- Files: `backend/app/services/baseline_ranker.py` (lines 165-178)
- Impact: Scales linearly with DB size. At 10k+ historical interventions this becomes slow and memory-heavy.
- Fix approach: Push `product_line`, `audience_segment`, and `market` filters into the SQL query in `BrandictionStore.list_interventions()`.

---

## Known Bugs

**`image_paths` in Campaign evaluation flow are API URL strings, not filesystem paths — silent no-op:**
- Symptoms: When a campaign is submitted via `/api/campaign/evaluate` and includes `image_paths` (set to values like `/api/campaign/image-file/...`), the `AudiencePanel` and `PairwiseJudge` services call `os.path.exists(img_path)` on these URL strings. This always returns `False`, so images are silently ignored for the LLM-judge evaluation path even when the user uploaded assets.
- Files: `backend/app/services/audience_panel.py` (line 181), `backend/app/services/pairwise_judge.py` (line 129)
- Trigger: Any campaign submitted to `/api/campaign/evaluate` with image attachments.
- Note: The `/api/brandiction/race` path uses `ImageAnalyzer._resolve_image_url_to_path()` which correctly converts API URLs to disk paths. The `evaluate` path was not updated to use this resolver.
- Fix: Replace `os.path.exists(img_path)` in both files with a call to `_resolve_image_url_to_path()` from `image_analyzer.py`, or inline the same resolution logic.

**Password comparison is plaintext:**
- Symptoms: `auth.py` compares `user["password"] != password` with raw string equality. No hashing.
- Files: `backend/app/auth.py` (line 21 in `auth.py` api layer), `backend/app/api/auth.py` (line 22)
- Trigger: Any login attempt — the password stored in `MOODY_USERS` env var is stored and compared as plaintext.
- Note: This is an internal tool (closed beta, login-gated) so risk is currently low, but a production deployment with weak passwords and a public endpoint is exploitable.

---

## Security Considerations

**CORS wildcard `origins: "*"` with `supports_credentials=True` is rejected by browsers — but signals misconfiguration:**
- Risk: `CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)` in `backend/app/__init__.py` (line 39). Modern browsers reject `Allow-Origin: *` when credentials are included, so cookie auth silently breaks from external origins. However, the config sends the header anyway and could mislead security reviewers.
- Files: `backend/app/__init__.py`
- Current mitigation: Requests fail silently at browser level.
- Recommendation: Set `origins` to the explicit frontend origin (e.g., `http://localhost:5173` in dev, production domain in prod). The `FRONTEND_ORIGIN` value should come from an env var.

**Hardcoded `SECRET_KEY` fallback:**
- Risk: `SECRET_KEY = os.environ.get('SECRET_KEY', 'campaign-ranker-secret')` means Flask sessions are signed with a known key if the env var is missing. Session cookies can be forged.
- Files: `backend/app/config.py` (line 19)
- Current mitigation: Only affects deployments where `SECRET_KEY` is not set.
- Recommendation: Remove the default value and let `Config.validate()` raise an error if `SECRET_KEY` is absent.

**`FLASK_DEBUG=True` is the default:**
- Risk: `DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'` defaults to debug mode, which enables the Werkzeug interactive debugger. If the server is accidentally exposed on a public address in debug mode, arbitrary Python execution is possible via the debugger PIN.
- Files: `backend/app/config.py` (line 21)
- Recommendation: Default to `'False'`.

**User table loaded at module import time, not reloadable:**
- Risk: `USERS = _load_users()` runs at import of `backend/app/auth.py`. If `MOODY_USERS` changes, the server must restart to pick up new credentials or removed users. Revoked access does not take effect until restart.
- Files: `backend/app/auth.py` (line 47)
- Current mitigation: Low impact for a small-team internal tool.
- Recommendation: Reload `USERS` on each request (with caching), or use a proper user store (even a SQLite table).

**No upload directory isolation per user:**
- Risk: Uploaded images are stored in `backend/uploads/images/{set_id}/`. The `set_id` is provided by the client (`request.form.get('set_id', 'unsorted')`). While `secure_filename` and `realpath` checks prevent path traversal, two different users with the same `set_id` will write into the same directory and can read each other's uploaded files.
- Files: `backend/app/api/campaign.py` (lines 164-167)
- Recommendation: Prefix the `set_id` directory with the session username to isolate uploads per user.

---

## Performance Bottlenecks

**Evaluation pipeline is synchronous within its background thread — no parallelism across LLM phases:**
- Problem: `EvaluationOrchestrator.run()` executes Panel → Pairwise → Scoring → Summary in strict sequence. The Panel phase itself is parallelized with `ThreadPoolExecutor`, but the entire orchestrator blocks until each phase completes before starting the next.
- Files: `backend/app/services/evaluation_orchestrator.py`
- Cause: Sequential design; each phase depends on previous phase output which is correct, but summary generation could overlap with scoring.
- Impact: 6 campaigns × 5 personas = 30 LLM calls in Panel, plus C(6,2)×3 = 45 Pairwise calls. Total wall time ~90-150 seconds at typical API latency.

**Image analysis in `/race` is synchronous and serial:**
- Problem: `race_campaigns()` in `backend/app/api/brandiction.py` (lines 627-643) analyzes each plan's images sequentially in a for-loop before returning.
- Files: `backend/app/api/brandiction.py`
- Cause: No parallelism in visual analysis loop.
- Improvement path: Use `ThreadPoolExecutor` to analyze multiple plans' images concurrently.

**`BrandictionStore` opens a new SQLite connection on every read/write:**
- Problem: Every `_connect()` call creates a new `sqlite3.connect()`. Under concurrent requests (Flask runs threaded), this causes connection overhead on each operation.
- Files: `backend/app/services/brandiction_store.py`
- Cause: No connection pooling; SQLite limitations make this acceptable at small scale but degrades with traffic.
- Improvement path: Use a thread-local connection or `check_same_thread=False` with a mutex.

---

## Fragile Areas

**`AudiencePanel` image path handling diverges from `ImageAnalyzer` path handling:**
- Files: `backend/app/services/audience_panel.py` (line 181), `backend/app/services/image_analyzer.py` (line 84)
- Why fragile: `AudiencePanel` and `PairwiseJudge` use `os.path.exists(img_path)` directly on whatever string is in `campaign.image_paths`, while `ImageAnalyzer` uses `_resolve_image_url_to_path()` to convert API URLs to disk paths. These two paths are not equivalent. Any change to how `image_paths` is populated will silently break one or the other.
- Safe modification: Centralize image path resolution by importing `_resolve_image_url_to_path` from `image_analyzer.py` in both Panel and Judge, and using it consistently.
- Test coverage: `backend/tests/test_visual_adjustment.py` covers `ImageAnalyzer` path, but does not test `AudiencePanel` with image URLs.

**`_evaluation_store` is a module-level dict shared across all requests:**
- Files: `backend/app/api/campaign.py` (line 36)
- Why fragile: Concurrent `evaluate()` calls writing to the same `set_id` (race condition) or `get_result()` reading while a background thread is writing are not protected by a lock. Python's GIL prevents data corruption but does not guarantee consistent reads of composite objects (dicts with nested structures).
- Safe modification: Wrap reads/writes to `_evaluation_store` with a `threading.Lock()`.

**`TaskManager` singleton persists across test runs:**
- Files: `backend/app/models/task.py`
- Why fragile: The singleton holds both the in-memory `_tasks` dict and the SQLite DB handle. Tests that instantiate `TaskManager` will share state unless the class-level `_instance` is explicitly reset. Already surfaced as flaky test behavior.
- Test coverage: `conftest.py` in `backend/tests/` should reset the singleton; currently unclear if it does.

**`BrandictionStore` singleton has the same cross-test contamination risk:**
- Files: `backend/app/services/brandiction_store.py`
- Why fragile: A single `_instance` is shared between the test run and any production fixtures. `test_brandiction_repair.py` exists specifically to address data corruption that likely resulted from this.

---

## Scaling Limits

**SQLite as primary data store:**
- Current capacity: Suitable for hundreds of interventions and evaluations for a single brand/team.
- Limit: SQLite write-locks the file for each write, so concurrent POST requests (evaluate + import + resolve simultaneously) can cause `OperationalError: database is locked`.
- Scaling path: Migrate to PostgreSQL when team grows beyond 3-5 concurrent users, or add WAL mode (`PRAGMA journal_mode=WAL`) as a short-term mitigation.

**No pagination on list endpoints:**
- Current capacity: `list_interventions()`, `list_signals()`, etc. return all rows with no limit.
- Files: `backend/app/services/brandiction_store.py`, `backend/app/api/brandiction.py`
- Limit: At 10k+ historical rows, API responses become large and slow.
- Scaling path: Add `limit`/`offset` parameters to store queries and expose via API query params.

**Calibration minimum set to 5 resolutions before activation:**
- Current capacity: Judge calibration (`JudgeCalibration.recalibrate()`) requires at least 5 resolved evaluation sets with prediction data. The system works uncalibrated until then.
- Files: `backend/app/services/judge_calibration.py` (line 32)
- Limit: Low data density early in usage means all evaluations run with uniform judge weights.

---

## Dependencies at Risk

**`sentence-transformers` in `.venv` but not in `pyproject.toml`:**
- Risk: `backend/.venv` contains `sentence_transformers` (detected via `CLIPModel.py` reference) but it is not listed as a project dependency in `backend/pyproject.toml`. If the venv is rebuilt, this implicit dependency will be missing.
- Impact: Any code that imports `sentence_transformers` at runtime will fail silently or with an `ImportError`.
- Migration plan: Audit actual imports across `backend/app/` and either add to `pyproject.toml` or confirm it is unused.

**`pymupdf` (PyMuPDF) in dependencies but no PDF processing in active code paths:**
- Risk: `PyMuPDF>=1.24.0` is a declared dependency in `pyproject.toml`. Active API code does not use it (no `fitz` import visible in `backend/app/`). It was likely inherited from the original MiroFish social simulation codebase.
- Impact: Bloated install size; potential supply chain risk from an unneeded large binary package.
- Migration plan: Grep for `import fitz` or `import pymupdf` across `backend/app/`. If absent, remove from `pyproject.toml`.

---

## Missing Critical Features

**No rate limiting on LLM-bound endpoints:**
- Problem: Any authenticated user can submit an arbitrarily large batch of evaluations. Each evaluation triggers 30-75 LLM API calls (Panel + Pairwise). A user could exhaust the LLM API quota with a single request.
- Blocks: Safe production deployment.
- Files: `backend/app/api/campaign.py`, `backend/app/api/brandiction.py`

**No image deletion endpoint:**
- Problem: Once an image is uploaded via `POST /api/campaign/upload-image`, there is no API endpoint to delete it. Users can remove the reference from the plan, but the file remains on disk indefinitely.
- Blocks: Disk space management, user data privacy.
- Files: `backend/app/api/campaign.py`

**No campaign form for the `/api/campaign/evaluate` path on the frontend:**
- Problem: The frontend `HomePage` only submits to `/api/brandiction/race` (via `raceCampaigns()`). The richer `/api/campaign/evaluate` path (with Pairwise Judge, Audience Panel, BT scoring, calibration) has no corresponding UI. It can only be used via direct API calls.
- Blocks: The full campaign evaluation workflow being accessible to non-technical users.
- Files: `frontend/src/pages/HomePage.tsx`, `frontend/src/lib/api.ts`

**No data export for historical baselines:**
- Problem: The Dashboard shows data stats but there is no export button or API endpoint to download the full intervention/outcome dataset as CSV or JSON for offline analysis.
- Blocks: Data portability, external reporting.

---

## Test Coverage Gaps

**`AudiencePanel` image integration path not tested:**
- What's not tested: The multimodal branch in `AudiencePanel.evaluate_campaign()` (lines 178-194) that injects base64 images. No test exercises a campaign with `image_paths` containing API URL strings to verify the `os.path.exists()` bug described above.
- Files: `backend/app/services/audience_panel.py`
- Risk: The silent no-op on images goes undetected.
- Priority: High

**`BrandictionStore` concurrent write behavior not tested:**
- What's not tested: Concurrent access to `brandiction.db` under load. All tests appear to be single-threaded.
- Files: `backend/app/services/brandiction_store.py`
- Risk: `OperationalError: database is locked` in production under concurrent usage.
- Priority: Medium

**`_evaluation_store` thread-safety not tested:**
- What's not tested: Concurrent read/write to the in-memory `_evaluation_store` dict during parallel evaluation threads.
- Files: `backend/app/api/campaign.py`
- Risk: Race condition on nested dict writes.
- Priority: Medium

**No frontend E2E tests:**
- What's not tested: Full user flow from login → image upload → race submission → result viewing. `backend/tests/e2e_smoke.py` is a backend smoke test, not a browser test.
- Files: `frontend/src/`
- Risk: UI regressions (broken form validation, failed uploads, display bugs) go undetected until manual review.
- Priority: Low (tool is internal/beta)

---

## Remaining Social Simulation Artifacts

**`agent_diffusion.py` uses social network terminology:**
- The `AgentDiffusion` layer in `backend/app/services/agent_diffusion.py` retains conceptual terms from the original MiroFish social simulation (`social_follower` archetype ID, `social_proof` dimension, neighbor-graph propagation). This is intentional repurposing, not dead code — but reviewers unfamiliar with the fork's origin may find it confusing.
- The diffusion layer is only invoked via `use_diffusion=True` in `POST /api/brandiction/predict`, which is not exposed in the current frontend. It is an opt-in experimental feature.
- Files: `backend/app/services/agent_diffusion.py`, `backend/app/api/brandiction.py` (lines 355-364)
- Risk: Low — code is functional and isolated. No action required unless the diffusion feature becomes a primary path.

**`MarketJudge` (market-making judge) is experimental and gated:**
- `backend/app/services/market_judge.py` implements an iterative market-maker/trader debate loop. It is only activated via `USE_MARKET_JUDGE=true` env var. Default is `false`.
- This is a more complex alternative to the default 3-judge majority vote. It is not tested under production load.
- Files: `backend/app/services/market_judge.py`, `backend/app/config.py` (line 34)
- Risk: Medium — enabling it in production without sufficient LLM quota could cause evaluation timeouts.

---

*Concerns audit: 2026-03-17*
