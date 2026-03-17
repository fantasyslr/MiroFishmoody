# Testing Patterns

**Analysis Date:** 2026-03-17

## Test Framework

**Runner:**
- pytest >= 8.0.0
- Config: no `pytest.ini` or `pyproject.toml [tool.pytest]` section — pytest discovers tests from `backend/tests/`
- `pytest-asyncio >= 0.23.0` installed but async tests not yet in use

**Assertion Library:**
- pytest built-in `assert` statements only — no `unittest.TestCase` assertions

**Run Commands:**
```bash
cd backend && uv run pytest              # Run all tests
cd backend && uv run pytest tests/test_smoke.py   # Single file
cd backend && uv run pytest -v           # Verbose output
```

**No frontend test framework detected** — no Jest, Vitest, or `*.test.ts` files exist. Frontend testing is currently absent.

## Test File Organization

**Location:**
- All tests co-located in `backend/tests/` — separate from source, not co-located with modules

**Naming:**
- Pattern: `test_<domain>.py` — e.g., `test_smoke.py`, `test_scorer.py`, `test_brandiction.py`
- Domain maps to workstream/phase: `test_pr6_api.py`, `test_phase55.py`, `test_v3_baseline_ranker.py`

**Shared setup:**
- `backend/tests/conftest.py` — sets required environment variables before any app import:
  ```python
  os.environ.setdefault("MOODY_SECRET_KEY", "test-secret")
  os.environ.setdefault("MOODY_UPLOAD_FOLDER", tempfile.mkdtemp())
  os.environ.setdefault("MOODY_USERS", "slr:test-pass:Liren:admin,tester1:test-pass:Tester1:user")
  ```

**Structure:**
```
backend/tests/
├── conftest.py              # Shared env setup (must run before app import)
├── test_smoke.py            # Integration: full HTTP flow via Flask test client
├── test_brandiction.py      # Unit: models, store, importer
├── test_scorer.py           # Unit: campaign scoring logic + verdicts
├── test_calibration.py      # Unit: judge calibration loop
├── test_pr6_api.py          # Integration: all brandiction API endpoints
├── test_bradley_terry.py    # Unit: BT ranking algorithm
├── test_brand_state.py      # Unit: brand state engine
├── test_phase55.py, test_phase56.py  # Phase-tagged regression suites
├── test_v3_*.py             # V3 data spine and ranker tests
├── e2e_smoke.py             # Live E2E (requires real API key, not in CI)
└── last_live_result.json    # Committed artifact from last live run
```

## Test Structure

**Class-based organization for integration tests:**
```python
class TestAuth:
    def test_login_success(self, client):
        resp = _login(client)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["username"] == "slr"

    def test_login_wrong_password(self, client):
        resp = _login(client, password="wrong")
        assert resp.status_code == 401
```

**Function-based organization for unit tests:**
```python
def test_ship_rank1_dominant():
    """#1 + 明显胜出 + 低 objection → SHIP"""
    campaigns = [make_campaign("a", "A"), ...]
    rankings, board = CampaignScorer().score(campaigns, panel, pairwise, bt)
    assert rankings[0].verdict == Verdict.SHIP
```

**Section dividers in test files:**
```python
# ──────────────────────────────────────────────
# Auth & Session
# ──────────────────────────────────────────────
class TestAuth:
    ...
# ------------------------------------------------------------------
# Model tests
# ------------------------------------------------------------------
class TestModels:
    ...
```

**Patterns:**
- Each test method is self-contained — no shared state between tests
- pytest fixtures (`app`, `client`) defined per test file, not only in conftest
- Regression tests labeled with `# Regression: Fix N — description` comments
- Tests print `PASS: description` in unit tests with `if __name__ == '__main__'` runner blocks (legacy pattern from before pytest adoption)

## Mocking

**Framework:** `unittest.mock` — `patch`, `MagicMock`

**Patterns:**
```python
# Stack decorators for multiple service mocks (bottom decorator = first arg)
@patch('app.services.evaluation_orchestrator.LLMClient')
@patch('app.services.evaluation_orchestrator.AudiencePanel')
@patch('app.services.evaluation_orchestrator.PairwiseJudge')
@patch('app.services.evaluation_orchestrator.CampaignScorer')
@patch('app.services.evaluation_orchestrator.SummaryGenerator')
def test_submit_and_check_status(self, mock_summary, mock_scorer,
                                  mock_judge, mock_panel, mock_llm, client):
    ...
```

**What to Mock:**
- LLM client calls in integration/API tests (avoid network + cost)
- Service layer in API integration tests when testing HTTP behavior only

**What NOT to Mock:**
- Data model operations (store, importer) — unit tests run against real SQLite in-memory/temp files
- Business logic (scorer, calibration) — tested with real inputs and expected outputs

## Fixtures and Factories

**Flask App Fixture (per file):**
```python
@pytest.fixture
def app():
    application = create_app()
    application.config['TESTING'] = True
    TaskManager._instance = None   # Reset singleton to avoid cross-test pollution
    yield application

@pytest.fixture
def client(app):
    with app.test_client() as c:
        yield c
```

**SQLite Store Isolation (function-level helpers, not pytest fixtures):**
```python
def _fresh_store():
    """Returns new BrandictionStore backed by a temp file"""
    BrandictionStore._reset_instance()
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    store = BrandictionStore(db_path=path)
    return store, path

def _cleanup(store, path):
    BrandictionStore._reset_instance()
    try:
        os.unlink(path)
    except OSError:
        pass
```

Used with try/finally:
```python
def test_save_and_get_intervention(self):
    store, path = _fresh_store()
    try:
        iv = HistoricalIntervention(intervention_id="iv1", run_id="r1", theme="comfort")
        store.save_intervention(iv)
        got = store.get_intervention("iv1")
        assert got.theme == "comfort"
    finally:
        _cleanup(store, path)
```

**Domain Object Factories:**
```python
def make_campaign(id: str, name: str, pl=ProductLine.COLORED) -> Campaign:
    return Campaign(
        id=id, name=name, product_line=pl,
        target_audience="test", core_message="test",
        channels=["meta"], creative_direction="test",
    )

def make_panel(persona_id, campaign_id, score, n_objections=1, obj_texts=None):
    objs = obj_texts if obj_texts else [f"obj_{i}" for i in range(n_objections)]
    return PanelScore(
        persona_id=persona_id, persona_name=f"P_{persona_id}",
        campaign_id=campaign_id, score=score,
        objections=objs, strengths=["str_1"], reasoning="ok",
    )
```

**Location:** Factory functions defined at module level in each test file — not shared across files.

**Session Injection (API tests without going through login endpoint):**
```python
def _admin_session(client):
    from app.auth import _password_version
    with client.session_transaction() as sess:
        sess['user'] = {"username": "slr", "display_name": "Liren",
                        "role": "admin", "_pw_ver": _password_version("slr")}
```

## Coverage

**Requirements:** None enforced — no coverage config, no minimum thresholds.

**View Coverage:**
```bash
cd backend && uv run pytest --cov=app --cov-report=term-missing
```
(pytest-cov not in pyproject.toml dev deps — must install separately)

## Test Types

**Unit Tests (`test_scorer.py`, `test_brandiction.py`, `test_calibration.py`, `test_bradley_terry.py`):**
- Scope: single service or model in isolation
- No Flask app, no HTTP, no mocking of internal dependencies
- Real SQLite temp files for storage tests
- Fast — no I/O except temp file creation

**Integration Tests (`test_smoke.py`, `test_pr6_api.py`):**
- Scope: full HTTP request/response cycle via Flask `test_client`
- Creates Flask app with `TESTING=True`
- LLM calls mocked via `@patch`
- Tests auth, RBAC, upload security, task lifecycle, evaluation submission

**E2E Tests (`e2e_smoke.py`):**
- Requires live LLM API key and running server
- Not run in CI — manual execution only
- Result saved to `backend/tests/last_live_result.json`

## Common Patterns

**Async Testing:**
- `pytest-asyncio` installed but no async tests exist yet
- Async behavior (background threads) tested by inspecting state after submission, not by awaiting

**Error Testing:**
```python
# HTTP error codes
assert resp.status_code == 401
assert resp.status_code in (400, 413)

# Exception raised by service
import pytest
with pytest.raises(Exception):
    store.save_outcome(oc)  # expects FK violation
```

**State Isolation for Singletons:**
```python
# In fixture teardown or before each test:
TaskManager._instance = None
BrandictionStore._reset_instance()
```

**Chinese Docstrings in Tests:**
```python
def test_session_invalidation_on_password_change(self, client):
    """验证 Fix 5: 密码变更后旧 session 失效"""
    ...
```

**Regression Labeling:**
```python
# ------------------------------------------------------------------
# Regression: Fix 1 — merge upsert 不丢旧字段
# ------------------------------------------------------------------
class TestMergeUpsert:
    def test_sparse_update_preserves_old_fields(self):
        """二次导入只带 theme，budget/spend 不应丢失"""
```

---

*Testing analysis: 2026-03-17*
