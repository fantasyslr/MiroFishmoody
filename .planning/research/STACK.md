# Technology Stack

**Project:** MiroFishmoody -- Brand Campaign Simulation Engine Enhancement
**Researched:** 2026-03-17
**Mode:** Subsequent (enhancing existing codebase, not greenfield)

## Current Stack (Keep As-Is)

These are already in place and working. No migration needed.

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| Python | 3.11+ | Backend runtime | Keep |
| Flask | 3.0+ | HTTP server | Keep |
| SQLite | built-in | Persistence | Keep (WAL mode needed) |
| OpenAI SDK | >=1.0.0 | LLM client (Qwen via Bailian) | Keep |
| Pydantic | >=2.0.0 | Data validation | Keep |
| Pillow | >=10.0.0 | Image preprocessing | Keep |
| React | 19.x | Frontend UI | Keep |
| TypeScript | 5.9 | Frontend language | Keep |
| Tailwind CSS | 3.4 | Styling | Keep |
| Vite | 8.x | Frontend build | Keep |
| Zustand | 5.x | Client state | Keep |

## Recommended Additions

### 1. Concurrent LLM Calls -- `asyncio` + `openai.AsyncOpenAI`

**Version:** Built-in (Python 3.11) + openai SDK (already installed)
**Purpose:** Parallel image analysis and pairwise judging
**Confidence:** HIGH

**Why:** The #1 performance bottleneck is serial image analysis (documented in PROJECT.md Active items). The project already uses `openai>=1.0.0` which ships `AsyncOpenAI` client. Flask 3.0 supports `async def` views. No new dependency needed -- just use what's already installed.

**Pattern:**
```python
from openai import AsyncOpenAI
import asyncio

async def analyze_images_concurrent(image_paths: list[str]) -> list[dict]:
    client = AsyncOpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)
    tasks = [analyze_single(client, path) for path in image_paths]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

**What NOT to do:** Don't add Celery or Redis for this. The workload is I/O-bound (waiting for LLM API responses), not CPU-bound. asyncio.gather() with 3-5 concurrent calls is sufficient for the scale (internal tool, <10 concurrent users). Celery adds operational complexity (broker, worker processes, monitoring) that this project doesn't need.

### 2. LLM Observability -- `langfuse` SDK

**Version:** 3.x (Python SDK v3, released June 2025)
**Purpose:** Trace LLM calls, track token costs, debug evaluation quality
**Confidence:** MEDIUM

**Why:** The platform makes 10-30+ LLM calls per evaluation (5 persona panels x N pairwise comparisons). Without observability, debugging "why did persona X score this campaign low?" is guesswork. Langfuse captures prompt/completion pairs, token usage, latency, and supports custom evaluation scores -- all critical for tuning the evaluation pipeline.

**Installation:**
```bash
pip install langfuse>=3.0.0
```

**Integration:** Uses `@observe()` decorator + automatic OpenAI SDK wrapping. Minimal code changes. Self-hosted option available (important since this is an internal tool with potentially sensitive campaign data). Cloud tier has a free plan for low volume.

**Alternative considered:** OpenTelemetry raw -- too generic, doesn't understand LLM-specific concepts (token usage, prompt/completion pairs). Langfuse is purpose-built for LLM apps and integrates with OpenAI SDK directly.

**What NOT to do:** Don't use DeepEval or RAGAS. Those are for evaluating RAG pipelines and LLM output quality at scale. This project's evaluation is the product itself (campaign scoring), not a meta-evaluation of LLM correctness.

### 3. Thread Safety for In-Memory State -- `threading.Lock`

**Version:** Built-in (Python stdlib)
**Purpose:** Fix `_evaluation_store` race conditions
**Confidence:** HIGH

**Why:** PROJECT.md documents `_evaluation_store` is an in-memory dict with no thread locks. Gunicorn runs 2 workers x 4 threads = 8 potential concurrent threads. This is a correctness bug, not a performance optimization.

**Pattern:**
```python
import threading
from collections import OrderedDict

class EvaluationStore:
    def __init__(self, max_size: int = 100):
        self._store: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()
        self._max_size = max_size

    def set(self, key: str, value: dict):
        with self._lock:
            self._store[key] = value
            while len(self._store) > self._max_size:
                self._store.popitem(last=False)  # LRU eviction
```

**What NOT to do:** Don't add Redis for this. The store is session-scoped evaluation state, not shared cache. An in-process lock + LRU eviction is the right fix for the current scale.

### 4. Password Hashing -- `bcrypt`

**Version:** 4.x
**Purpose:** Replace plaintext password storage (documented in PROJECT.md Active items)
**Confidence:** HIGH

**Why:** `MOODY_USERS` env var currently stores plaintext passwords. bcrypt is the standard choice for password hashing in Python -- it's battle-tested, has built-in salt generation, and configurable work factor.

**Installation:**
```bash
pip install bcrypt>=4.0.0
```

**Alternative considered:** `passlib` -- heavier dependency, more features than needed. `argon2-cffi` -- technically superior algorithm but bcrypt has broader ecosystem support and the security difference is negligible for an internal tool with <50 users.

### 5. Structured Logging -- `structlog`

**Version:** 24.x+
**Purpose:** Replace ad-hoc logger with structured JSON logging for LLM call debugging
**Confidence:** MEDIUM

**Why:** The codebase already has a logger utility (`get_logger`), but debugging multi-step evaluation chains (persona panel -> pairwise judge -> Bradley-Terry scoring) requires structured context (evaluation_id, persona_name, campaign_pair) that string formatting handles poorly. structlog adds context binding without changing call sites.

**Installation:**
```bash
pip install structlog>=24.0.0
```

**What NOT to do:** Don't add a full ELK stack or log aggregation service. structlog outputs JSON to stdout, Docker captures it, that's sufficient for an internal tool.

## Recommended Frontend Additions

### 6. Server State Management -- `@tanstack/react-query`

**Version:** 5.x
**Purpose:** Async evaluation polling, cache invalidation, optimistic updates
**Confidence:** HIGH

**Why:** The Evaluate path runs async tasks (TaskManager + SQLite persistence). The frontend needs to poll for completion, handle loading/error states, and cache results. React Query provides this out of the box with configurable polling intervals, automatic retries, and cache invalidation. Currently the frontend likely uses raw `fetch` + `useEffect` which doesn't handle race conditions or stale data well.

**Installation:**
```bash
npm install @tanstack/react-query@^5
```

**What NOT to do:** Don't use SWR. React Query has better DevTools, more granular cache control, and built-in mutation support. SWR is simpler but lacks features needed for long-running async task polling.

### 7. Data Visualization -- `recharts`

**Version:** 2.x
**Purpose:** Render evaluation score comparisons, radar charts for dimension analysis, Bradley-Terry rankings
**Confidence:** MEDIUM

**Why:** The evaluation results have multi-dimensional scores (creative_style, product_visibility, aesthetic_tone, etc.) that need visual comparison across campaigns. Recharts is React-native, composable, and handles radar/bar/line charts well. Lightweight compared to D3 (which requires imperative DOM manipulation that fights React).

**Installation:**
```bash
npm install recharts@^2
```

**Alternative considered:** `nivo` -- more beautiful defaults but heavier bundle. `victory` -- good but less active maintenance. `chart.js` via react-chartjs-2 -- works but Canvas-based (harder to style with Tailwind). Recharts uses SVG, plays well with React's rendering model.

## Explicitly NOT Recommended

| Technology | Why Not |
|------------|---------|
| **Celery + Redis** | Overkill for <10 concurrent users. asyncio handles the I/O-bound LLM fan-out. Adds broker dependency to Docker compose. |
| **PostgreSQL** | PROJECT.md constraint: SQLite + WAL is sufficient for internal tool scale. Migration cost > benefit. |
| **LangChain** | The project has clean, direct OpenAI SDK usage. LangChain adds abstraction layers and dependency bloat for no clear benefit. The evaluation chain logic is domain-specific (persona panels, Bradley-Terry) and doesn't map to LangChain's generic chain/agent patterns. |
| **FastAPI migration** | Flask 3.0 async support is sufficient. The codebase has 20+ Flask routes and middleware. Migration cost is high, benefit is marginal for this use case. |
| **NIMA / image-quality-assessment** | The project uses LLM multimodal vision for image analysis, which provides richer, domain-specific insights (creative style, brand tone, trust signals) than generic IQA scores. NIMA gives a single aesthetic score -- useless for campaign comparison. |
| **DeepEval / RAGAS** | These evaluate LLM output quality. This project IS the evaluation product -- the LLM evaluates campaigns, not itself. Meta-evaluation frameworks don't apply here. |
| **choix library** | The hand-rolled Bradley-Terry implementation (20 iterations MM algorithm in `pairwise_judge.py`) works correctly and is well-tested (`test_bradley_terry.py`). choix adds a dependency for ~40 lines of code that's already battle-tested in this codebase. |
| **LiteLLM** | Only one LLM provider (Qwen via Bailian). LiteLLM's value is multi-provider routing/fallback. Single-provider + OpenAI SDK is simpler. |

## Updated Dependencies Summary

### Backend additions to `pyproject.toml`:

```toml
dependencies = [
    # ... existing ...

    # Security
    "bcrypt>=4.0.0",

    # Observability (optional, enable when needed)
    "langfuse>=3.0.0",

    # Structured logging
    "structlog>=24.0.0",
]
```

### Frontend additions:

```bash
npm install @tanstack/react-query@^5 recharts@^2
```

### No new infrastructure dependencies

The Docker single-container deployment model is preserved. No Redis, no message broker, no external services required (Langfuse cloud is optional; self-hosted is a separate container if needed later).

## Migration Notes

| Addition | Effort | Risk | Priority |
|----------|--------|------|----------|
| AsyncOpenAI for parallel image analysis | 1-2 days | Low (same SDK, just async client) | P0 -- directly fixes documented performance issue |
| threading.Lock for _evaluation_store | 0.5 day | Low (stdlib, isolated change) | P0 -- correctness bug |
| bcrypt password hashing | 0.5 day | Low (env var migration needed) | P1 -- security issue |
| @tanstack/react-query | 1-2 days | Low (additive, doesn't replace existing) | P1 -- needed for Evaluate UI |
| structlog | 1 day | Low (wraps existing logger) | P2 -- nice-to-have for debugging |
| Langfuse | 1 day | Low (decorator-based, opt-in) | P2 -- valuable after evaluation pipeline stabilizes |
| recharts | 1-2 days | Low (additive UI components) | P2 -- enhances result visualization |

## Sources

- [Flask async/await docs](https://flask.palletsprojects.com/en/stable/async-await/) -- Flask 3.x async view support
- [OpenAI Python SDK](https://github.com/openai/openai-python) -- AsyncOpenAI client documentation
- [Langfuse Python SDK](https://langfuse.com/docs/observability/get-started) -- v3 SDK with @observe() decorator
- [Langfuse overview](https://langfuse.com/docs/observability/overview) -- LLM observability architecture
- [choix PyPI](https://pypi.org/project/choix/) -- v0.4.1, Bradley-Terry library (evaluated but not recommended)
- [TanStack React Query](https://tanstack.com/query/latest) -- v5 server state management
- [Recharts](https://recharts.org/) -- React composable charting library
- [LLM Evaluation best practices](https://langfuse.com/blog/2025-03-04-llm-evaluation-101-best-practices-and-challenges) -- evaluation framework landscape
- [LiteLLM](https://docs.litellm.ai/docs/) -- multi-provider gateway (evaluated but not recommended)
