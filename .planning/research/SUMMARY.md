# Project Research Summary

**Project:** MiroFishmoody — Brand Campaign Pre-testing Tool v2.1
**Domain:** AI-assisted campaign evaluation engine (Flask monolith + React SPA)
**Researched:** 2026-03-18
**Confidence:** HIGH (all architecture verified from codebase; stack choices confirmed via official docs)

## Executive Summary

MiroFishmoody is a multi-persona LLM evaluation engine that pre-tests brand campaign materials before production. v2.0 ships a complete evaluation pipeline — 9/8 persona pool, MultiJudge ensemble, ConsensusAgent, visual diagnostics, cross-path badges, and PDF export. v2.1 is a focused correctness milestone with three goals: fix a production 404 that prevents the app from loading, migrate from Vercel (incompatible, serverless) to Railway (Docker-native, persistent disk), and introduce brief-type-aware evaluation weights to stop the evaluator from systematically favoring conversion-optimized campaigns over brand/seeding campaigns.

The recommended approach for v2.1 is strictly incremental. No new dependencies, no architectural changes. The deployment fix requires two code changes (a Dockerfile assertion + a Flask startup fallback route) and a Railway volume mount at `/app/backend/uploads`. The brief-type weight feature threads one new `brief_type` parameter through five existing files plus one new config file. The benchmark dataset is a plain JSON collection that seeds a simple Python regression runner. All three workstreams are independent and can be developed in parallel; they share no file-level conflicts until the final integration test.

The key risk is data loss. Railway's volume mount path must match `Config.UPLOAD_FOLDER` exactly (`/app/backend/uploads`). A path mismatch writes SQLite and uploaded images to the container's ephemeral layer, which is silently correct during a session and silently destructive on restart. The second risk is result-ranking discontinuity: changing aggregation weights must be versioned in stored results so historical evaluations do not appear to have been re-scored. Both risks are low-cost to prevent at implementation time and high-cost to recover from after the fact.

---

## Key Findings

### Recommended Stack

v2.1 requires zero new dependencies. The existing Flask + SQLite + React/Vite + Docker stack handles all three workstreams. Railway is the recommended deployment target because its GitHub push-to-deploy model, persistent volume support, and direct Docker compatibility eliminate every Vercel constraint (10s timeout, ephemeral filesystem, no long-running processes). The fallback is any Linux VPS with Docker — the existing `docker-compose.yml` and `nginx.conf.template` work without modification.

**Core technologies:**
- Flask (`backend/app/__init__.py`) — static SPA serving + API blueprints — path logic is correct; needs startup assertion + fallback route only
- SQLite WAL (`backend/uploads/tasks.db`) — task state persistence — requires Railway volume mount at exact path `/app/backend/uploads`
- React 19 + Vite (`frontend/src/`) — SPA; build output must exist at `/app/frontend/dist` inside the container
- Railway (new deployment target) — Docker-native, persistent volumes, $5/mo Hobby + storage; replaces incompatible Vercel
- `brief_weights.py` (new file) — pure Python dict config for 3 brief-type weight profiles; zero pip packages

**What NOT to add:**
- PostgreSQL — SQLite WAL handles current load; migration adds ops overhead with no v2.1 benefit
- LLM-inferred brief types — adds latency and cost; explicit user selection is more reliable and auditable
- Node.js proxy layer — Flask static serving is already correct when `dist` exists; fix the build assertion instead

### Expected Features

**Must have (table stakes for v2.1):**
- `brief_type` enum field in campaign form (`brand` / `seeding` / `conversion`) — gates the entire weight feature; required field with enum validation at API boundary
- Per-brief-type weight profiles stored as auditable config in `brief_weights.py` — brand team must be able to review and adjust
- `brief_type` threaded through `EvaluationOrchestrator` → `CampaignScorer` → `DimensionEvaluator` — two touch points: weight selection + score aggregation
- `brief_type` threaded through `BaselineRanker` (Race path) — independent from Evaluate path; can be migrated separately
- Brief type badge visible on result page and in PDF export — users must verify which weight profile was applied
- `weight_profile_version` field in `EvaluationResult` — stored in result JSON at generation time; prevents silent re-scoring of historical results
- Benchmark dataset seed — minimum 30 labeled examples (10 per brief type) in `backend/tests/fixtures/benchmark/` as JSON
- Benchmark regression runner — `python benchmark/run.py` outputs `brand_accuracy`, `seeding_accuracy`, `conversion_accuracy` separately; aggregate metric is informational only
- Dockerfile assertion: `RUN test -f /app/frontend/dist/index.html` — prevents silent Vite build failures reaching production
- Flask 503 fallback route when `dist` is absent — replaces current silent 404 with actionable error

**Should have (v2.1 differentiators):**
- Weight transparency panel — collapsible UI breakdown of `weight × score` per dimension; backend scores already exist, needs weight metadata added to result JSON
- Startup log of resolved `dist` absolute path — one line added to `app/__init__.py`; eliminates SSH-to-debug-404 workflow
- Post-deploy `/health` smoke test verifying `uploads_writable: ok` — endpoint already exists; must be in Railway deploy checklist

**Defer to v2.2+:**
- Benchmark hit rate in admin dashboard — runner script JSON output sufficient for v2.1
- Brief-type calibration history — requires post-campaign outcome collection pipeline; long-term only
- Sub-brief-types within brand/seeding/conversion — needs labeled data to validate; defer until benchmark reaches 50+ examples per type
- ML-based weight optimization — 30-50 labeled examples too small; expert-designed weights + hit rate measurement is correct approach until 200+ examples exist
- Image quality score (`visual_quality_score`) influencing `thumb_stop` dimension — `visual_diagnostics` is currently display-only; full integration is v2.2 work

### Architecture Approach

The existing monolith architecture requires only additive changes for v2.1. The `brief_type` parameter follows the same routing pattern as `category` — extracted from the POST payload in `api/campaign.py`, passed to `orchestrator.run()`, threaded to `CampaignScorer`, and applied in `DimensionEvaluator` as a post-hoc weight multiplier on raw scores before softmax. Backward compatibility is preserved: `brief_type=None` falls back to the current uniform weighting. The benchmark is a pytest fixture directory with pre-recorded LLM responses for deterministic replay — no HTTP, no live LLM calls in CI.

**Major components and v2.1 touch points:**
1. `Dockerfile` — add `RUN test -f /app/frontend/dist/index.html` assertion after frontend COPY
2. `app/__init__.py` — add startup log of resolved `dist` path; add 503 fallback route when `dist` absent
3. `models/campaign.py` — add `BriefType` enum; add `brief_type: BriefType = BriefType.SEEDING` field to `Campaign`
4. `services/brief_weights.py` (new) — `BRIEF_DIMENSION_WEIGHTS` dict for brand/seeding/conversion
5. `services/submarket_evaluator.py` — accept `brief_type` in `evaluate()` signature; apply weights as multiplier before softmax
6. `services/campaign_scorer.py` — accept and thread `brief_type` to `DimensionEvaluator`
7. `services/evaluation_orchestrator.py` — add `brief_type` to `run()` signature; thread to scorer
8. `api/campaign.py` — extract `brief_type` from POST payload; validate enum; return 400 for unknown types
9. `frontend/src/pages/HomePage.tsx` + `lib/api.ts` — add `brief_type` select field (3 options); add type annotation

**Key pattern for brief_type (mirrors existing category pattern):**
```
POST /evaluate body: { ..., "brief_type": "brand"|"seeding"|"conversion" }
    → data.get("brief_type") in api/campaign.py
    → orchestrator.run(task_id, campaign_set, category, brief_type)
    → CampaignScorer(brief_type_weights=BRIEF_DIMENSION_WEIGHTS[brief_type])
    → DimensionEvaluator applies weights before softmax
```

### Critical Pitfalls

1. **Railway volume path mismatch (D3)** — if volume is mounted at `/app/uploads` instead of `/app/backend/uploads`, the app silently writes to the ephemeral container layer; all SQLite data and uploaded images lost on restart. Prevention: use `Config.UPLOAD_FOLDER` as the authoritative path; add to Railway deploy checklist; verify with `/health` after first deploy.

2. **Weight profile not versioned in stored results (W2)** — adding brief-type weights without recording `weight_profile_version` in `EvaluationResult` means users viewing old results cannot tell they were scored with different weights; re-running the same campaigns shows different rankings with no explanation. Prevention: add `weight_profile_version: "v2.1-brief-type-weighted"` to result JSON before writing the first weight profile — zero cost at implementation, high cost retroactively.

3. **Flat weights systematically biasing conversion briefs (W1)** — current `DimensionEvaluator` uses equal weights regardless of brief type; conversion-brief campaigns structurally score higher on `conversion_readiness` even when the goal is brand awareness. This is the primary correctness bug v2.1 addresses; must be fixed before benchmark data collection, or the baseline hit rates are themselves biased.

4. **Benchmark per-type labels missing (W5)** — a benchmark with unlabeled brief types produces a single aggregate hit rate that masks per-type regressions. A change that improves brand accuracy by 15% but worsens conversion accuracy by 10% passes as a net improvement. Prevention: every benchmark example must have `brief_type` label; report `brand_accuracy`, `seeding_accuracy`, `conversion_accuracy` separately — never report only aggregate.

5. **`brief_type` enum not validated at API boundary** — an unknown `brief_type` string causes an unhandled `KeyError` in the weight profile lookup. Prevention: validate enum in `api/campaign.py` before passing to orchestrator; return HTTP 400 for unknown types.

---

## Implications for Roadmap

Based on combined research, the natural phase structure is three phases matching the three independent workstreams. Phases 2 and 3 data collection can run in parallel; only Phase 3 runner integration requires Phase 2 completion.

### Phase 1: Deployment Fix
**Rationale:** The app returns 404 in production. Nothing can be user-validated until the deployment works. Blocking dependency for all downstream verification.
**Delivers:** Working production deployment on Railway with persistent SQLite and file uploads; `/` returns 200; task state survives container restarts.
**Addresses:** Static 404 (STACK Focus 1), Vercel incompatibility (STACK Focus 2), deployment smoke test.
**Avoids:** Pitfalls D1 (static path), D2 (serverless incompatibility), D3 (Railway volume mismatch).
**Verification gate:** `curl https://<railway-url>/` returns 200; submit campaign, restart Railway service, poll task status — result still visible; `/health` returns `uploads_writable: ok` and `db: ok`.

### Phase 2: Brief-Type Weight Profiles
**Rationale:** The evaluation engine produces systematically incorrect rankings without brief-type weights (Pitfall W1). Must be fixed before benchmark data is labeled — labels captured against a biased evaluator are biased labels.
**Delivers:** Three weight profiles (brand/seeding/conversion) threaded through full evaluation pipeline; `brief_type` required field in form; `weight_profile_version` in stored results; brief type badge on result page.
**Addresses:** FEATURES.md P1 items — brief type form field, `BriefTypeWeightProfile` config, `EvaluationOrchestrator` injection, `BaselineRanker` injection, result badge.
**Avoids:** Pitfalls W1 (flat weight bias), W2 (backward compatibility), W4 (wording sensitivity via structured brief_type field).
**Implementation order within phase:** (1) `BriefType` enum + `brief_weights.py` config, (2) thread through backend pipeline (orchestrator → scorer → evaluator), (3) API validation + 400 on unknown type, (4) frontend select field + result badge.

### Phase 3: Benchmark Dataset + Regression Runner
**Rationale:** Weight profiles without a regression safety net are unverifiable. The benchmark provides per-type hit rates so the brand team can assess calibration quality; future weight changes can be validated without manual re-evaluation.
**Delivers:** 30+ labeled benchmark examples with `brief_type` labels (10 per type minimum); `python benchmark/run.py` reporting `brand_accuracy`, `seeding_accuracy`, `conversion_accuracy`; pytest integration with pre-recorded LLM response fixtures.
**Addresses:** FEATURES.md benchmark schema, regression runner, annotation guidelines.
**Avoids:** Pitfall W5 (aggregate-only benchmark masking per-type regressions).
**Note:** Manual data labeling (brand team) is the human bottleneck. Begin labeling during Phase 2 development. Phase 3 scope is met when runner + schema exist with first labeled examples; runner is LOW complexity (~1 day of code work).

### Phase Ordering Rationale

- Phase 1 must come first: production is broken; no user-facing validation is possible.
- Phase 2 must precede benchmark data collection in Phase 3: labels captured against a flat-weight evaluator are biased ground truth; the weight profiles define what "correct" means for the benchmark.
- Phase 3 data collection (manual labeling) can run in parallel with Phase 2 development; only the runner script integration step waits for Phase 2 completion.
- Race path (`BaselineRanker`) and Evaluate path (`EvaluationOrchestrator`) weight injections are decoupled within Phase 2 and can be developed in parallel.

### Research Flags

Phases with well-documented patterns (no research-phase needed):
- **Phase 1 (Deployment Fix):** All code paths verified locally. Railway volume docs confirmed HIGH confidence. Two specific code changes identified with exact file/line locations. Gunicorn PORT env var note documented.
- **Phase 2 (Weight Profiles):** All five file touch points identified in ARCHITECTURE.md. Weight rationale cross-verified from industry sources. Implementation pattern mirrors existing `category` routing — no novel patterns.
- **Phase 3 (Benchmark Runner):** Benchmark schema fully specified. Pytest fixture pattern is standard. Only unknown is brand team availability for manual labeling — not a technical unknown.

No phase in v2.1 needs `/gsd:research-phase`. All three workstreams are sufficiently specified for direct implementation.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All code paths verified from local codebase; Railway docs verified 2026-03-18 from official source; zero new dependencies |
| Features | MEDIUM | Weight proportions cross-verified across 3+ industry sources (Adstellar, SmartInsights, Motimatic); benchmark schema from LLM evaluation literature HIGH confidence for structure, MEDIUM for domain-specific field selection |
| Architecture | HIGH | Direct source inspection of all relevant files; v2.1 integration points identified with exact file references; mirrors existing category routing pattern |
| Pitfalls | HIGH | Grounded in codebase analysis + domain research + known issues from milestone context; deployment pitfalls confirmed against Railway official docs |

**Overall confidence:** HIGH

### Gaps to Address

- **Brief-type weight values:** The weight proportions in `brief_weights.py` are derived from industry research (MEDIUM confidence). They are reasonable starting points but not empirically validated against Moody's historical campaign data. The benchmark hit rate measurement in Phase 3 is the mechanism to validate or recalibrate. Accept initial values as defensible defaults; treat Phase 3 hit rates as the recalibration signal.

- **Gunicorn PORT env var on Railway:** PITFALLS.md notes Railway injects `PORT` env var but gunicorn may be hardcoded to `5001`. Either read `PORT` from env in the start command or configure Railway to expose `5001` explicitly. One-line change; must be handled during Phase 1 Railway setup to avoid a silent bind failure.

- **Benchmark data availability:** The benchmark requires brand team time to label 30 historical campaign examples with `brief_type` labels. This is the only non-code dependency in v2.1. Risk: if brand team cannot label during the sprint, the runner exists but has insufficient data for meaningful hit rates. Mitigation: start labeling during Phase 2 development; per FEATURES.md, 5 examples per type is the minimum for any statistical meaning; below that, do not report hit rates as meaningful.

---

## Sources

### Primary (HIGH confidence)
- `backend/app/__init__.py` — static serving path logic, verified locally 2026-03-18
- `backend/app/services/probability_aggregator.py` — flat weight constants `W_PAIRWISE=0.55`, `W_PANEL=0.45` confirmed
- `backend/app/services/submarket_evaluator.py` — dimension weighting structure confirmed
- `backend/app/services/campaign_scorer.py` — aggregation pipeline confirmed
- `Dockerfile` + `docker-compose.yml` — multi-stage build paths, volume mounts verified
- `backend/app/config.py` — `UPLOAD_FOLDER` authoritative path confirmed
- https://docs.railway.com/reference/volumes — Railway volume limits, IOPS, pricing (official docs, verified 2026-03-18)
- https://flask.palletsprojects.com/en/stable/tutorial/deploy/ — static file serving in production
- https://docs.gunicorn.org/en/stable/deploy.html — `--chdir` interaction with `os.getcwd()`

### Secondary (MEDIUM confidence)
- https://www.adstellar.ai/blog/meta-campaign-performance-scoring — weighted KPI framework for brief types
- https://www.smartinsights.com/goal-setting-evaluation/goals-kpis/ — brand evaluation KPIs, ISO 20671 reference
- https://motimatic.com/industry/other/kpis-in-digital-marketing/ — brief type KPI differentiation
- https://mightyscout.com/blog/the-ultimate-guide-to-influencer-marketing-kpis — seeding campaign KPIs
- https://www.getmaxim.ai/articles/building-a-golden-dataset-for-ai-evaluation — benchmark dataset methodology
- https://kili-technology.com/large-language-models-llms/ — domain-specific LLM benchmark patterns
- https://www.pkgpulse.com/blog/railway-vs-render-vs-fly-io — platform comparison 2026
- [Judging the Judges: Position Bias in LLM-as-a-Judge (ACL 2025)](https://aclanthology.org/2025.ijcnlp-long.18/) — 10-30% verdict flip rate; swap debiasing must not be regressed in v2.1
- [Why Do Multi-Agent LLM Systems Fail? (arxiv 2503.13657)](https://arxiv.org/abs/2503.13657) — evaluation sensitivity and aggregation failure modes

### Tertiary (LOW confidence / single source)
- ISO 20671 brand evaluation framework — storytelling dimension weighting basis (referenced via SmartInsights; full standard not reviewed)
- https://arxiv.org/abs/2507.00769 (LitBench) — benchmark methodology for subjective evaluation (methodological reference only)

---
*Research completed: 2026-03-18*
*Ready for roadmap: yes*
