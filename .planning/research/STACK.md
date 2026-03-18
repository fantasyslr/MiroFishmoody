# Stack Research

**Domain:** Campaign evaluation engine — v2.1 deployment fix + brief-type evaluation weights
**Researched:** 2026-03-18
**Confidence:** HIGH (all code paths verified locally; deployment options verified via official docs)

---

## Scope

This document covers only what is new or changed for **v2.1**. Previous milestone stack entries (multi-agent, PersonaRegistry, font stack, ConsensusAgent, etc.) are already shipped in v2.0.

**v2.1 goals:**
1. Fix production `/` returning 404
2. Migrate deployment from Vercel to stateful platform (SQLite + file uploads require persistent disk)
3. Add brief-type-aware evaluation weights (brand / seeding / conversion)

---

## Focus 1: Static Asset 404 Fix

### Root Cause (Code-Verified)

The milestone context referenced `server/index.ts` — that file does not exist. This is a Flask/Python project. The actual static serving logic is in `backend/app/__init__.py`.

**Relevant code (`backend/app/__init__.py`, lines 117–136):**

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

**Path resolution at Docker runtime:**
- `__file__` = `/app/backend/app/__init__.py`
- `os.path.dirname(__file__)` = `/app/backend/app`
- `../../frontend/dist` resolves to `/app/frontend/dist`
- `Dockerfile` line: `COPY --from=frontend-build /app/frontend/dist /app/frontend/dist` ✓ correct

**Path logic is correct.** The `/` 404 happens when `os.path.isdir(dist)` returns `False` at container startup — the entire static-serving block is skipped, Flask has no route for `/`, and returns 404.

**Root cause candidates in order of likelihood:**

1. **Vite build failed silently during `docker build`** — `npm run build` exited non-zero but Docker cached the layer. Result: `/app/frontend/dist/index.html` missing. The `if os.path.isdir(dist)` evaluates to `False` because the directory is empty or absent.
2. **Deployment platform strips or resets volume contents** (if deployed to Vercel, which has no persistent filesystem — each function invocation gets a fresh read-only container).
3. **`gunicorn --chdir /app/backend`** shifts the working directory, but `FRONTEND_DIST` uses `os.path.dirname(__file__)` (absolute, not relative to cwd), so this is not the cause.

**Fix — two changes required:**

**Change 1:** Add Dockerfile assertion after frontend copy (prevents silent build failures):

```dockerfile
# In Dockerfile, after: COPY --from=frontend-build /app/frontend/dist /app/frontend/dist
RUN test -f /app/frontend/dist/index.html || \
    (echo "ERROR: frontend/dist/index.html missing — Vite build may have failed" && exit 1)
```

**Change 2:** Add explicit 503 fallback in `backend/app/__init__.py` when dist is absent (replaces silent 404):

```python
else:
    if should_log_startup:
        logger.error(f"FATAL: frontend dist not found at {dist}")

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def no_frontend(path):
        return {"error": "frontend not built", "expected_dist": dist}, 503
```

**No new libraries required.** Both fixes are configuration/code changes only.

---

## Focus 2: Deployment Platform

### Requirement Profile

| Requirement | Detail |
|-------------|--------|
| Persistent storage | SQLite at `/app/backend/uploads/tasks.db` |
| File uploads | `/app/backend/uploads/` — campaign images, results JSON |
| Long-running processes | Gunicorn, evaluation tasks 30–300s |
| Container format | Single Docker container, existing `Dockerfile` and `docker-compose.yml` |
| Current broken platform | Vercel — no persistent filesystem, 10s function timeout, incompatible |

### Platform Comparison

| Criterion | Railway | Render | Fly.io | VPS + Docker (Hetzner) |
|-----------|---------|--------|--------|------------------------|
| Persistent disk | Yes — volumes, 5GB on Hobby | Yes — persistent disks, daily snapshots | Yes — block volumes per VM | Full filesystem control |
| SQLite suitability | Good — 3000 IOPS R/W | Good — daily snapshot backup | Good — single-region limitation | Best (no I/O restrictions) |
| Docker deployment | Yes (existing Dockerfile works) | Yes | Yes (native Machines API) | Native `docker compose up` |
| Long-running processes | Yes (300s+ supported) | Yes | Yes | Yes |
| Zero-downtime deploy with disk | No — brief restart on redeploy | No — same limitation | No — same limitation | Manual via nginx reload |
| Env var management | Dashboard UI | Dashboard UI | `fly secrets` CLI | `.env` file on server |
| Entry pricing | $5/mo Hobby + storage usage | $7/mo Starter + disk add-on | $0 + usage-based | ~€4/mo (Hetzner CX11) |
| DX / deployment speed | Excellent (GitHub push) | Good | Good, steeper CLI curve | Manual SSH + scripts |
| Volume attachment | 1 volume per service; mount to any path | Persistent disk add-on; attach to service | 1 volume per VM; mount via fly.toml | Host directory mount |

**Source:** Railway volumes documented at https://docs.railway.com/reference/volumes (verified 2026-03-18, HIGH confidence).

### Recommendation: Railway

**Recommended platform for v2.1 migration.** Rationale:

1. **Existing `Dockerfile` works without modification.** Railway deploys from GitHub using the existing Dockerfile.
2. **Volume mount aligns with existing Docker volume.** Mount Railway volume to `/app/backend/uploads` — same path as `docker-compose.yml` volume `uploads-data:/app/backend/uploads`.
3. **Env vars map directly.** `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL_NAME`, `SECRET_KEY`, `MOODY_USERS`, `FLASK_DEBUG` all set via Railway dashboard, no refactor.
4. **$5/mo Hobby plan + storage usage** is acceptable for an internal tool. SQLite WAL + uploads for <20 concurrent users will stay well under 5GB.
5. **No new infra skills required.** Team already has Docker experience; Railway is GitHub push-to-deploy.

**Migration — no code changes required for deployment itself:**

```bash
npm install -g @railway/cli
railway login
railway init        # in project root
# Create and attach volume in Railway dashboard:
# Service > Volumes > Add Volume > mount path: /app/backend/uploads
# Set env vars in Service > Variables (copy from .env)
railway up
```

**Known limitation:** Each redeploy causes ~5–15s container restart downtime (Railway volumes prevent zero-downtime deploys). For an internal tool this is acceptable. If this becomes a problem in a future milestone, use Railway's `startCommand` with gunicorn `--preload` and keep response queuing in flight.

### Fallback: VPS + Docker (Hetzner CX11, €4/mo)

If Railway becomes too expensive or ops team prefers full control, the existing `docker-compose.yml` and `nginx.conf.template` work identically on any Linux VPS. Requires: SSH access, Docker, Certbot for TLS, manual deploy script. Recommended as a fallback only — Railway removes this operational overhead.

---

## Focus 3: Brief-Type-Aware Evaluation Weights

### Current State (Code-Verified)

The evaluation pipeline uses **static, brief-type-agnostic weights**:

| File | Current behavior |
|------|-----------------|
| `probability_aggregator.py` | `W_PAIRWISE=0.55`, `W_PANEL=0.45` — fixed blend regardless of brief type |
| `submarket_evaluator.py` | 5 fixed dimensions; persona-to-dimension mapping is static |
| `campaign_scorer.py` | `judge_weights`/`persona_weights` from `JudgeCalibration` only (Brier-score based, not brief-type based) |
| `campaign.py` `Campaign` model | No `brief_type` field; `extra: Dict` is available as escape hatch |
| `campaign.py` `CampaignSet` | Has `context: str` but it is not parsed downstream |

**The `objective` field (awareness/traffic/conversion) exists only in `brandiction.py`**, not the main campaign evaluation pipeline.

### What Needs to Be Added

**No new Python packages required.** All changes are pure logic — dict config + a new enum.

#### Step 1: `BriefType` enum in `campaign.py`

```python
# backend/app/models/campaign.py — add before Campaign dataclass
class BriefType(str, Enum):
    BRAND = "brand"          # 品牌向：品牌认知，停留力 + 信任 优先
    SEEDING = "seeding"      # 种草向：KOC/社交种草，停留力 + 清晰度 优先
    CONVERSION = "conversion"  # 转化向：购买引导，转化就绪度 优先
```

Add to `Campaign` dataclass:

```python
brief_type: BriefType = BriefType.SEEDING  # default to seeding (most common brief)
```

Add to `Campaign.to_dict()`:

```python
"brief_type": self.brief_type.value,
```

#### Step 2: New `brief_weights.py` config file

New file: `backend/app/services/brief_weights.py`

```python
"""Brief-type-aware dimension weight tables."""

# Weights must sum to 1.0 per brief type.
# Higher weight = this dimension matters more for this brief type.
BRIEF_DIMENSION_WEIGHTS: dict[str, dict[str, float]] = {
    "brand": {
        "thumb_stop": 0.35,          # Must stop scroll to build awareness
        "clarity": 0.15,             # Message can be evocative, not necessarily explicit
        "trust": 0.30,               # Brand credibility is primary KPI
        "conversion_readiness": 0.05, # Not a conversion campaign
        "claim_risk": 0.15,          # Brand campaigns carry higher reputational risk
    },
    "seeding": {
        "thumb_stop": 0.35,          # KOC content must stop scroll
        "clarity": 0.30,             # Usage/product must be immediately understood
        "trust": 0.15,               # Authentic peer trust, lower bar than brand
        "conversion_readiness": 0.10, # Some purchase intent signal expected
        "claim_risk": 0.10,          # Lower regulatory sensitivity for seeding
    },
    "conversion": {
        "thumb_stop": 0.15,          # Intent-triggered placements — scroll-stopping less critical
        "clarity": 0.25,             # CTA and offer must be crystal clear
        "trust": 0.15,               # Some trust needed for purchase
        "conversion_readiness": 0.40, # Primary KPI for conversion briefs
        "claim_risk": 0.05,          # Lower weight — conversion copy is typically checked
    },
}

DEFAULT_BRIEF_TYPE = "seeding"
```

**Weight rationale:**
- **品牌向 (brand)**: `thumb_stop` + `trust` = 0.65 combined — brand campaigns measure memorability and credibility.
- **种草向 (seeding)**: `thumb_stop` + `clarity` = 0.65 combined — KOC content needs to stop scroll and be understood without context.
- **转化向 (conversion)**: `conversion_readiness` = 0.40 solo — conversion campaigns are measured by purchase intent signals first.

#### Step 3: Thread `brief_type` through `DimensionEvaluator`

In `submarket_evaluator.py`, modify `evaluate()` signature and apply weights:

```python
from .brief_weights import BRIEF_DIMENSION_WEIGHTS, DEFAULT_BRIEF_TYPE

class DimensionEvaluator:
    def evaluate(
        self,
        campaigns: List[Campaign],
        panel_scores: List[PanelScore],
        brief_type: str = DEFAULT_BRIEF_TYPE,   # ADD THIS
    ) -> List[DimensionScore]:
        weights = BRIEF_DIMENSION_WEIGHTS.get(brief_type, BRIEF_DIMENSION_WEIGHTS[DEFAULT_BRIEF_TYPE])
        # ... existing loop ...
        # After computing raw_scores per dimension, apply brief-type weight
        # as a post-hoc multiplier on the raw_score before softmax:
        for cid in all_ids:
            raw_scores[cid] *= weights.get(dimension_key, 1.0)
        probs = _softmax_probs(raw_scores, temperature=1.5)
```

#### Step 4: Thread into `CampaignScorer`

```python
# campaign_scorer.py
def score(
    self, campaigns, panel_scores, pairwise_results,
    bt_scores, agent_scores=None,
    brief_type: str = "seeding",   # ADD THIS
):
    dimension_results = self.dimension_eval.evaluate(
        campaigns, panel_scores, brief_type=brief_type
    )
```

#### Step 5: Thread into `EvaluationOrchestrator`

```python
# evaluation_orchestrator.py — run() signature
def run(self, task_id: str, campaign_set, category: str = None, brief_type: str = "seeding"):
    # pass brief_type through to CampaignScorer.score()
```

#### Step 6: API + Frontend

**Backend (`backend/app/api/campaign.py`):** Add `brief_type` to the evaluate endpoint payload deserialization. The field is already available at the `CampaignSet` level — add it as a top-level param alongside `category`.

**Frontend (`frontend/src/pages/HomePage.tsx`):** Add a `brief_type` field to the set-level form. The `DEFAULT_PLAN` already has `channel_family` — add `brief_type: 'seeding'` as default. A simple `<select>` with three options (品牌向 / 种草向 / 转化向) is sufficient.

**Frontend type (`frontend/src/lib/api.ts`):** Add `brief_type?: string` to the `EvaluateRequest` type (or equivalent).

### Estimated Scope

| Change | File | Lines |
|--------|------|-------|
| Add `BriefType` enum + field | `backend/app/models/campaign.py` | ~10 |
| New weight config | `backend/app/services/brief_weights.py` | ~30 (new file) |
| Thread through `DimensionEvaluator` | `backend/app/services/submarket_evaluator.py` | ~10 |
| Thread through `CampaignScorer` | `backend/app/services/campaign_scorer.py` | ~5 |
| Thread through `EvaluationOrchestrator` | `backend/app/services/evaluation_orchestrator.py` | ~5 |
| API endpoint + deserialization | `backend/app/api/campaign.py` | ~5 |
| Frontend form + type | `frontend/src/pages/HomePage.tsx` + `lib/api.ts` | ~15 |

**No new pip or npm packages required.**

---

## No New Dependencies for v2.1

| What | Why No New Dep Needed |
|------|-----------------------|
| Static 404 fix | Code + Dockerfile change only |
| Railway deployment | Existing Dockerfile deploys directly |
| Brief-type weights | Pure Python dict config, stdlib only |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Node.js proxy layer | No need — Flask serves static files correctly when `dist` exists | Fix the dist assertion in Dockerfile |
| PostgreSQL migration | SQLite WAL handles current load; migration adds ops overhead not warranted for v2.1 | Keep SQLite, mount Railway volume |
| LLM-inferred brief weights | Adds latency and cost per evaluation run; weights should be auditable by brand team | Static dict config in `brief_weights.py` |
| Heroku | Ephemeral filesystem destroys SQLite on dyno restart; 2022 pricing changes make it expensive | Railway |
| Vercel | 10s function timeout, no persistent disk — already confirmed incompatible | Railway |

---

## Alternatives Considered

| Decision | Recommended | Alternative | When Alternative Wins |
|----------|-------------|-------------|----------------------|
| Deployment | Railway | VPS + Docker | If ops team prefers full control or Railway pricing grows; existing `docker-compose.yml` + `nginx.conf.template` works on any VPS |
| Deployment | Railway | Render | Render is valid; Railway's volume docs are clearer and Docker deployment is more direct |
| Deployment | Railway | Fly.io | Fly.io works well but steeper CLI curve; `fly.toml` config required; no benefit over Railway for a single-container internal tool |
| Brief weights | Static dict config | Env var overrides | If brand team wants runtime tuning without code deploys, each weight can be added as `os.environ.get('BRAND_WEIGHT_THUMB_STOP', '0.35')` |
| Brief type field | `BriefType` enum on `Campaign` | Reuse `extra` dict | `extra` is valid for a quick patch; enum provides type safety and IDE support for longer-term maintenance |

---

## Sources

- `backend/app/__init__.py` — static serving logic, verified locally (2026-03-18)
- `backend/app/models/campaign.py` — Campaign model, no `brief_type` field confirmed locally
- `backend/app/services/submarket_evaluator.py` — dimension weighting logic, verified locally
- `backend/app/services/probability_aggregator.py` — weight constants `W_PAIRWISE`, `W_PANEL`, verified locally
- `backend/app/services/campaign_scorer.py` — full scoring pipeline, verified locally
- `Dockerfile` — multi-stage build, path verification, verified locally
- `docker-compose.yml` — volume mount `uploads-data:/app/backend/uploads`, verified locally
- https://docs.railway.com/reference/volumes — Railway volume limits, IOPS, pricing (HIGH confidence, official docs, verified 2026-03-18)
- https://www.pkgpulse.com/blog/railway-vs-render-vs-fly-io-app-hosting-platforms-nodejs-2026 — platform comparison (MEDIUM confidence)
- https://fly.io/docs/rails/advanced-guides/sqlite3/ — Fly.io SQLite guidance (MEDIUM confidence, Rails context but principle applies)

---

*Stack research for: MiroFishmoody v2.1 — deployment fix + brief-type evaluation weights*
*Researched: 2026-03-18*
