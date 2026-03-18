# Pitfalls Research

**Domain:** Brand campaign simulation with LLM-based multimodal evaluation
**Researched:** 2026-03-18 (updated for v2.1: deployment fix + evaluation bias correction)
**Confidence:** HIGH (grounded in codebase analysis + domain research)

---

## v2.1 Milestone-Specific Pitfalls

The following pitfalls are specific to the three goals of this milestone:
(A) Fixing the Flask static file serving path that causes `/` to return 404 in Docker.
(B) Migrating from Vercel (serverless) to Railway/Docker (stateful long-running process).
(C) Adding brief-type-driven weighted scoring profiles to fix evaluator bias.

---

### Pitfall D1: Static Path Computed at Module Import Time, Not Runtime Working Directory

**What goes wrong:**
`FRONTEND_DIST = os.path.join(os.path.dirname(__file__), '../../frontend/dist')` is computed once when `app/__init__.py` is imported. `__file__` resolves to the Python source file's absolute path inside the container, which is `/app/backend/app/__init__.py`. The computed path becomes `/app/backend/app/../../frontend/dist` → `/app/frontend/dist`. The Dockerfile copies the frontend build to `/app/frontend/dist`, so this works in theory. The actual bug is that `os.path.abspath(FRONTEND_DIST)` collapses correctly, but gunicorn is launched with `--chdir /app/backend`, which changes the process working directory to `/app/backend`. If any code uses a **relative** fallback or the dist path is edited to be relative (e.g., `frontend/dist` without the `__file__`-based anchor), it resolves to `/app/backend/frontend/dist` which does not exist — and the `if os.path.isdir(dist)` check silently skips static file registration with no error, causing 404 on every non-API route.

**Why it happens:**
The distinction between `os.path.dirname(__file__)` (anchored to source file location) and `os.getcwd()` (anchored to process working directory) is invisible during local development because both resolve the same way when running from the project root. In Docker, gunicorn's `--chdir /app/backend` shifts `os.getcwd()` without affecting `__file__`.

**How to avoid:**
- Keep the `os.path.join(os.path.dirname(__file__), ...)` anchor. Never replace it with a relative string or `os.getcwd()`-based path.
- Add a startup log that prints the resolved absolute path of `dist` and whether `os.path.isdir(dist)` is `True`. This takes one line and makes the failure immediately visible in `docker compose logs`.
- Write a test: start the Flask app with `create_app()`, make a `GET /` request, assert the response is not 404. Run this test as part of the Docker build verification step (not just the unit test suite).

**Warning signs:**
- `docker compose logs` shows "前端 dist 目录不存在" at startup, or the log line for "前端静态文件托管" is missing.
- `GET /` returns 404 in production but works in local `npm run dev` (which uses Vite's dev server, not Flask static serving).
- `curl http://localhost:5001/health` succeeds (API routes work) but `curl http://localhost:5001/` fails (SPA routes broken).

**Phase to address:**
Phase D1 (Deployment Fix) — first change in the milestone, verified with `curl http://localhost:5001/` returning 200 before merging.

---

### Pitfall D2: Serverless Platform Silently Accepts a Stateful App and Fails at Runtime

**What goes wrong:**
Vercel accepts deployment of any Docker container or Node/Python app. The deployment succeeds. `DEPLOYMENT_NOT_FOUND` does not appear until a request is made that violates serverless constraints: any operation that requires persistent state on disk (SQLite writes, uploaded image files, task queue in `TaskManager`) fails or appears to succeed but does not persist across requests. Specifically:

- SQLite `tasks.db` is written to `/app/backend/uploads/tasks.db`. Each Vercel invocation may run in a fresh ephemeral container, so a task submitted in one request is invisible to the next request's status poll.
- Image files uploaded to `/app/backend/uploads/` disappear between invocations.
- Gunicorn with multiple workers is incompatible with Vercel's execution model (Vercel invokes a single function handler, not a long-running gunicorn process).
- Vercel's free tier has a 10-second function timeout; the evaluation pipeline takes 90-150 seconds.

The project's `docker-compose.yml` already uses a named volume `uploads-data` mounted at `/app/backend/uploads`, proving the design requires persistent disk. This is inherently incompatible with serverless.

**Why it happens:**
Vercel's UI and CLI successfully build and deploy the container. There is no pre-flight check that says "this app requires persistent disk." The failure only appears at runtime when SQLite tries to write, or when a user polls for a task that was created in a different ephemeral invocation.

**How to avoid:**
- Deploy to Railway (natively supports Docker containers with persistent volumes), a VPS with Docker + docker compose, or any container platform that provides persistent disk.
- On Railway: set a volume mount at `/app/backend/uploads` in the Railway dashboard. The `docker-compose.yml` volumes block translates directly to Railway's volume configuration.
- Verify persistence explicitly: submit a campaign, restart the container (`docker compose restart`), poll the task status — it must still be visible. This proves the database and uploads survived the restart.
- Do not attempt to make the app work on Vercel by moving state to external storage (Redis, S3, PostgreSQL). That is a larger architectural change than a v2.1 deployment fix.

**Warning signs:**
- `DEPLOYMENT_NOT_FOUND` on Vercel (the app compiled but the deployment target does not support long-running processes).
- Task status polling returns 404 or "task not found" for tasks that were definitely submitted.
- Uploaded images disappear after a browser refresh or after a few minutes.
- Evaluation takes longer than Vercel's function timeout and returns a cold timeout error with no log output.

**Phase to address:**
Phase D1 (Deployment Fix) — validate with the explicit persistence test before considering the migration complete.

---

### Pitfall D3: Railway Volume Mount Path Mismatch Silently Writes to Container Ephemeral Layer

**What goes wrong:**
Railway requires the volume mount path to match exactly what the application writes to. The Dockerfile creates `/app/backend/uploads/results` and `/app/backend/uploads/calibration/predictions`. If the Railway volume is mounted at `/app/uploads` (wrong) instead of `/app/backend/uploads` (correct), the application writes files to the correct path on the container's ephemeral layer, which appears to work during a session but loses all data on container restart. No error is raised; files just disappear silently.

**Why it happens:**
Railway's volume configuration is set manually in the dashboard and is disconnected from the Dockerfile's `RUN mkdir` commands. There is no schema validation between volume mount paths and what the app actually uses.

**How to avoid:**
- The authoritative path is `Config.UPLOAD_FOLDER` in `backend/app/config.py`. Check this before setting the Railway volume mount. The `healthcheck` endpoint already verifies `uploads_writable` — use it as the post-deploy smoke test.
- After the first deploy, write a test file, restart the service, and verify the file is still there.

**Warning signs:**
- `/health` returns `uploads_writable: error` immediately after deploy.
- Evaluation results are visible during a session but disappear after the next deploy or container restart.
- SQLite `tasks.db` is not found on the next startup, causing the app to re-initialize a blank database.

**Phase to address:**
Phase D1 (Deployment Fix) — part of the Railway migration checklist.

---

### Pitfall W1: Flat Dimension Weights Systematically Favor "Conversion-Ready" Campaign Descriptions

**What goes wrong:**
The current evaluator in `pairwise_judge.py` uses five dimensions: `reach_potential`, `conversion_potential`, `brand_alignment`, `risk_level`, `feasibility`. These dimensions have equal weight in the `DimensionEvaluator` and `ProbabilityAggregator`. For campaigns with a conversion-focused brief (e.g., 618 sale promo), the LLM judges naturally rate `conversion_potential` and `feasibility` higher because the brief explicitly describes conversion mechanics. For brand awareness campaigns, those same dimensions score lower (awareness briefs don't optimize for immediate purchase), but `brand_alignment` and `reach_potential` are more relevant. With flat weights, conversion-brief campaigns win systematically over awareness briefs even when the awareness campaign is better for its stated goal.

The milestone context identifies this concretely: the heuristic evaluator over-weights `conversionPotential` and `executionReadiness` (lines 271-272 of the prior evaluator version). The same structural problem exists in the current `DimensionEvaluator._compute_raw()` — `conversion_readiness` is computed from `price_conscious` and `daily_wearer` personas, which are structurally more engaged with conversion signals than brand-awareness signals.

**Why it happens:**
The initial dimension set was designed when the primary use case was conversion campaign evaluation. Brand awareness and content seeding campaigns were added later without revisiting the weight structure.

**How to avoid:**
- Introduce a `brief_type` field in the campaign submission payload: `brand` (品牌), `seeding` (种草), `conversion` (转化). This field should be a required enum, not a free-text field.
- Define a `WeightProfile` per brief type that adjusts the contribution of each dimension when aggregating the final score. Example: for `brand` briefs, `brand_alignment` and `reach_potential` should be 2x weight; `conversion_potential` and `feasibility` should be 0.5x. For `conversion` briefs, invert this.
- Store `brief_type` alongside the campaign submission so that historical evaluations can be filtered by type when doing trend analysis.
- Do NOT change the dimension computation logic (what each dimension measures) — only change how dimensions are aggregated. This preserves backward compatibility with existing results.

**Warning signs:**
- Conversion-brief campaigns consistently winning evaluations against brand-brief campaigns in the same evaluation set (category mismatch).
- Users saying "the tool always recommends the most promotional-sounding campaign, even for brand campaigns."
- `conversion_readiness` scores are the most discriminating dimension across all brief types (when they should only be discriminating for conversion briefs).

**Phase to address:**
Phase W1 (Weight Profile) — introduce `brief_type` and `WeightProfile` before running any benchmark regression tests, since benchmark results are meaningless without brief-type-aware scoring.

---

### Pitfall W2: Adding Brief-Type Weights Without Preserving Backward Compatibility of Historical Results

**What goes wrong:**
Once `brief_type`-driven weight profiles are introduced, re-running an old campaign evaluation set produces different rankings because the weight profile changes the aggregated score even with identical LLM outputs. Users who saved results from before the weight change see different rankings if they re-run the same campaigns. This breaks trust in the system's consistency.

**Why it happens:**
Changing aggregation weights is treated as a bug fix ("the old weights were wrong") rather than a schema change that requires versioning. There is no mechanism to record which weight profile was used when a result was generated.

**How to avoid:**
- Record the `weight_profile_version` (a string like `"v2.1-brief-type-weighted"`) in `EvaluationResult` at the time the result is generated. Old results retain `"v2.0-flat-weights"` (or `null`).
- Never retroactively re-score stored results. If a user views an old result, show a banner: "This result used v2.0 equal weights. Re-run to apply the current brief-type profile."
- The `ScoreBoard.to_dict()` method must include `weight_profile_version` in its output so the frontend can display it.

**Warning signs:**
- Users reporting that re-running the same campaign gives different rankings with no explanation.
- Historical trend dashboard showing discontinuous jumps in scores across the v2.1 deploy date.
- `EvaluationResult` JSON files missing any reference to which scoring profile was used.

**Phase to address:**
Phase W1 (Weight Profile) — add versioning before writing the first weight profile. Zero additional cost at implementation time; high cost to add retroactively.

---

### Pitfall W3: Image Content Is Counted as a Quantity Bonus, Not Analyzed for Semantic Content

**What goes wrong:**
The current `DimensionEvaluator._compute_raw()` does not use `visual_diagnostics` at all. Image analysis results are computed in `EvaluationOrchestrator.run()` and stored in `visual_diagnostics`, but they are passed to `EvaluationResult` as a separate field and never fed into `DimensionEvaluator` or `ProbabilityAggregator`. The practical effect: campaigns with images and campaigns without images receive equivalent dimension scores. If the `ImageAnalyzer` returns a quality signal (e.g., "poor thumbnail clarity" or "visual-brand alignment: low"), that signal is shown only as a diagnostic note in the UI but does not influence ranking.

The milestone context states: "Images only count as quantity bonus, not content analysis (line 264)." This confirms that somewhere in the scoring path, image presence adds a small bonus (likely a count-based multiplier) but image content quality does not.

**Why it happens:**
`visual_diagnostics` was added as a supplementary diagnostic feature. The scoring pipeline was not updated to consume it because the data model for `ImageAnalyzer` output is unstructured (a dict of diagnostics, not a numeric signal). Integrating unstructured diagnostics into a numeric scoring model requires a mapping decision that was deferred.

**How to avoid:**
- Extract a numeric `visual_quality_score` from `ImageAnalyzer` output alongside the existing `diagnostics`. This score should represent overall visual clarity + brand alignment on a 0-10 scale.
- Pass `visual_quality_score` per campaign to `DimensionEvaluator.evaluate()` and let it influence `thumb_stop` (and optionally `brand_alignment`) if the score is present. Default to neutral (5.0) when no images exist.
- The mapping must be explicit: `thumb_stop += visual_quality_score * 0.3` is a reasonable blend. Document the weight so it can be adjusted independently.
- If `visual_quality_score` is missing (image analysis failed for a campaign), do not penalize. Log a warning and use the fallback persona-based heuristic.

**Warning signs:**
- Identical dimension scores for two campaigns where one has high-quality KV images and one has no images.
- `visual_diagnostics` is populated in the result JSON but the `dimension_scores` for `thumb_stop` are identical across campaigns with and without images.
- Users uploading images but noticing rankings do not change compared to submissions without images.

**Phase to address:**
Phase W2 (Image Content Integration) — after `brief_type` weight profiles are stable, add image quality scoring as the second signal. Do not combine both changes in one PR.

---

### Pitfall W4: Evaluator Sensitivity to Brief Phrasing Causes Ranking Instability

**What goes wrong:**
Two campaigns with identical strategy but different wording in their brief/description fields receive significantly different scores. For example:

- Campaign A brief: "提升品牌认知，触达18-25岁年轻女性，通过小红书内容种草建立品类教育"
- Campaign B brief: "小红书内容营销，目标人群18-25女性，核心目标是品牌声量和用户教育"

These briefs express the same intent. But the LLM judges, reading the brief as part of their evaluation prompt, produce different `conversion_potential` and `reach_potential` scores because one brief mentions "内容种草" (implies softer conversion) and the other mentions "声量" (implies reach). The final ranking may differ despite equal strategic merit.

This is not a failure of position bias (which is addressed by swap debiasing) — it is a failure of **wording sensitivity** in the evaluation prompt.

**Why it happens:**
The LLM judges receive the raw brief text as part of the campaign description. The LLM is asked to compare campaigns, and phrasing differences activate different evaluation heuristics even when intent is identical.

**How to avoid:**
- Structure the campaign submission: require separate fields for `objective` (品牌/种草/转化), `target_audience`, `core_message`, and `channels` rather than a single free-text `description`. The LLM judges receive the structured fields, not free-form prose.
- Alternatively, add a normalization step: before sending the campaign to judges, run a brief parser (`BriefParser` already exists in the codebase) to extract structured fields and use those for evaluation. Free-text description is for human reference only.
- Add wording-sensitivity to the regression benchmark: include pairs of semantically equivalent briefs with different wording and assert they receive rankings within the `CONFIDENCE_THRESHOLD` margin.

**Warning signs:**
- Users reporting that editing the campaign description text changes the ranking without changing the actual strategy.
- The benchmark regression test shows high variance when brief wording is changed while keeping all other fields constant.
- `JudgeCalibration` consistency metrics show inconsistency correlated with brief length or use of specific marketing jargon.

**Phase to address:**
Phase W1 (Weight Profile) — structured brief fields and the `brief_type` enum together eliminate most wording sensitivity. The BriefParser is already available for the normalization step.

---

### Pitfall W5: Benchmark Dataset Without Brief-Type Labels Produces Misleading Regression Metrics

**What goes wrong:**
The benchmark dataset is built from historical campaign data. If the benchmark includes campaigns from multiple brief types (brand, seeding, conversion) without labels, the regression test computes a single hit-rate metric that mixes all types. A change that improves brand campaign ranking accuracy by 15% but worsens conversion campaign accuracy by 10% produces a net improvement in the aggregate metric, but the regression test passes. Users of conversion briefs experience degraded accuracy that the test does not catch.

**Why it happens:**
Building a benchmark feels like a data collection problem (gather enough examples), not a labeling problem (label each example by type). The first version of the benchmark collects whatever historical data is available without adding type labels.

**How to avoid:**
- Every benchmark example must have a `brief_type` label (`brand`/`seeding`/`conversion`).
- Report per-type hit rates separately: `brand_accuracy`, `seeding_accuracy`, `conversion_accuracy`. The aggregate metric is informational only; per-type metrics are the gatekeeping metrics.
- Minimum benchmark size per type: 5 examples. Do not run regression tests until each type has at least 5 labeled examples. Running tests on 2 examples per type produces hit rates of 0%, 50%, or 100% with no statistical meaning.

**Warning signs:**
- Benchmark JSON contains no `brief_type` field on examples.
- Regression report shows only a single `hit_rate` number without breakdown by type.
- The team considers the regression passing when `hit_rate >= 0.7` without knowing the per-type distribution.

**Phase to address:**
Phase W3 (Benchmark + Regression) — label the benchmark before running any regression tests. Per-type metrics should be the first output of the benchmark runner.

---

## Original Pitfalls (v1.x–v2.0, still applicable)

### Pitfall 1: Silent Image Dropout in LLM Evaluation

**What goes wrong:**
Images are silently ignored during evaluation. The Evaluate path receives `image_paths` as API URL strings (e.g. `/api/campaign/image-file/...`), but `AudiencePanel` and `PairwiseJudge` call `os.path.exists()` on these strings. This always returns `False`, so images are quietly skipped. The evaluation completes without error — users see scores that appear valid but were computed without visual context.

**Why it happens:**
The Race path was built first with `ImageAnalyzer._resolve_image_url_to_path()`. When the Evaluate path was added, it duplicated the image-handling pattern without importing the resolver.

**How to avoid:**
- Use the shared `resolve_image_path` utility from `image_helpers.py` in all services that process images.
- Add a validation step in `EvaluationOrchestrator.run()` that logs a WARNING if zero images were successfully resolved for a campaign that has `image_paths`.

**Warning signs:**
- Evaluate results show identical scores for campaigns with wildly different visuals.
- No `image_url` content parts in LLM request logs during Evaluate runs.

**Phase to address:**
Phase 1 (Bug Fix) — already fixed in v1.0 via `resolve_image_path`; do not regress in v2.1.

---

### Pitfall 2: LLM Judge Bias — Position and Single-Model Amplification

**What goes wrong:**
Single-model LLM judges exhibit systematic position bias (10-30% verdict flip when order is swapped). Multiple calls to the same model with the same order produce the same biased result. Bradley-Terry then amplifies this into confident-looking rankings.

**How to avoid:**
- Position-swap already implemented via `PairwiseJudge` and `MultiJudgeEnsemble`. Do not remove this when adding brief-type weight profiles.
- Track per-judge consistency metric. A judge with less than 70% consistency across swapped pairs should be flagged.

**Phase to address:**
Already addressed in v2.0. Maintain in v2.1 — do not remove swap debiasing while adding weight profile logic.

---

### Pitfall 3: Concurrent Access Corruption on Shared Mutable State

**What goes wrong:**
`_evaluation_store` is a module-level dict shared across Flask threads. Python's GIL prevents segfaults but does not prevent inconsistent reads of composite structures.

**How to avoid:**
- `threading.Lock()` on `_evaluation_store` writes — already implemented in v1.1 and audited in v2.0.
- SQLite WAL mode + `busy_timeout` — already enabled. Do not regress in v2.1 deployment changes.

**Phase to address:**
Already addressed. Verify it survives the Railway migration (container restart should not lose the WAL journal).

---

### Pitfall 4: Base64 Token Overflow

**What goes wrong:**
High-resolution campaign images blow up the LLM token budget, causing silent truncation or API errors.

**How to avoid:**
- Resize to max 1024px before base64 encoding — already implemented. Do not regress.

**Phase to address:**
Already addressed in v1.0. Regression test: 5MB image is resized to less than 500KB before encoding.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Flat dimension weights for all brief types | No UX change needed | Conversion briefs win systemically over brand briefs | Never — fix in v2.1 |
| Free-text brief description as evaluation input | Flexible for users | Wording sensitivity causes ranking instability | MVP only; move to structured fields in v2.1 |
| `visual_diagnostics` as display-only, not scoring input | Simpler evaluation pipeline | Images have no effect on ranking despite being the core campaign asset | Acceptable until v2.1 |
| Single `hit_rate` metric in benchmark | Quick to implement | Masks per-type accuracy regressions | Never for a multi-brief-type product |
| `brief_type` not recorded in stored results | No migration needed | Cannot filter historical results or run per-type analysis | Never — add before first benchmark run |
| Railway volume path set manually in dashboard | No code change | Mismatch causes silent data loss on restart | Never — document the exact path in DEPLOY.md |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Railway volume mounts | Set volume mount at `/app/uploads` instead of `/app/backend/uploads` | Use `Config.UPLOAD_FOLDER` as the authoritative path; paste its value directly into Railway's volume config |
| Flask static file serving in Docker | Relative path for `FRONTEND_DIST` resolves wrong under gunicorn `--chdir` | Always anchor with `os.path.dirname(__file__)`; log resolved absolute path at startup |
| Gunicorn on Railway | Railway injects `PORT` env var; gunicorn bind is hardcoded to `5001` | Either read `PORT` from env or configure Railway to expose `5001` explicitly |
| Qwen Vision API (Bailian) | Sending unstructured brief text with visual context makes judge output sensitive to phrasing | Normalize briefs to structured fields before passing to judge prompt |
| `brief_type` weight profile | Changing aggregation weights retroactively changes stored result rankings | Version the weight profile; stored results are immutable |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `BaselineRanker` loading all historical data | Slow API response for Race evaluations as history grows | Push category/audience filter into SQL WHERE clause | >1000 historical entries |
| Benchmark regression running all brief types as one job | Test duration grows with benchmark size; failures not attributable to type | Run per-type regression as separate test cases | >50 benchmark examples total |
| Image analysis in parallel without semaphore | 429 from Bailian when 5+ campaigns have images | Global LLM semaphore already in place; verify it covers `ImageAnalyzer` calls | >3 campaigns with 5 images each |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Railway environment variables visible in dashboard logs | LLM API key, SECRET_KEY leaked in build logs | Use Railway's secret variables (not plain env vars) for sensitive values |
| `brief_type` enum not validated on intake | Attacker submits arbitrary string, weight profile lookup fails with unhandled KeyError | Validate enum at the API route layer before passing to orchestrator; return 400 for unknown types |
| SQLite database file on Railway ephemeral disk (no volume) | All task history lost on every deploy | Verify volume is mounted at `/app/backend/uploads` before accepting v2.1 as done |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| `brief_type` field not shown in evaluation results | Users cannot tell which weight profile was used | Show "品牌权重模式" / "转化权重模式" badge on the result card |
| Weight profile change breaks historical trend dashboard | Dashboard shows a scoring discontinuity at the v2.1 deploy date with no explanation | Add an annotation event to the trend dashboard: "权重模式升级至 v2.1" |
| Image quality score changes ranking but diagnostics panel does not explain why | Users see the ranking change but cannot trace it to the image quality signal | When `visual_quality_score` affects the ranking, show it as a contributing factor in the verdict rationale |
| Benchmark hit-rate shown as a single number | Brand team cannot tell if their brief type is covered | Show per-type coverage ("品牌命中率 8/10, 转化命中率 7/10") in the benchmark report |

## "Looks Done But Isn't" Checklist

- [ ] **Static file path fix:** Verify `docker compose logs` shows "前端静态文件托管: /app/frontend/dist" (not "目录不存在"). Verify `curl http://localhost:5001/` returns 200, not 404.
- [ ] **Railway migration:** Submit a campaign, restart the Railway service, poll the task status — it must still return the result. Verify `/health` shows `uploads_writable: ok` and `db: ok` after restart.
- [ ] **Brief-type weight profiles:** Verify a brand brief campaign and a conversion brief campaign in the same evaluation set do not produce identical dimension scores. Verify the result JSON includes `weight_profile_version`.
- [ ] **Image content scoring:** Verify two campaigns — one with high-quality images, one with no images — produce different `thumb_stop` scores. The campaign with no images must not receive a `thumb_stop` score equal to the high-quality campaign.
- [ ] **Wording sensitivity regression:** Submit two semantically equivalent briefs with different wording in the same evaluation set. Verify their overall scores are within the `CONFIDENCE_THRESHOLD` margin.
- [ ] **Benchmark per-type metrics:** Verify benchmark report outputs `brand_accuracy`, `seeding_accuracy`, `conversion_accuracy` as separate metrics. Verify each type has at least 5 labeled examples before the first run.
- [ ] **Weight profile versioning:** Verify old evaluation results stored before v2.1 still load correctly in the UI without re-scoring. Verify they show a "v2.0 weights" indicator rather than showing stale scores as if computed with v2.1 weights.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Static path 404 | LOW | Add startup log, confirm path, redeploy. No data loss. |
| Railway data loss (no volume) | HIGH | Re-add volume mount, redeploy. All historical evaluations and uploaded images lost; users must re-submit. |
| Railway volume path mismatch | MEDIUM | Correct path in Railway dashboard, redeploy. Files written to ephemeral layer are lost; files already on volume are intact. |
| Flat weights biasing results | MEDIUM | Add `WeightProfile`, redeploy. Old results are not changed (immutable); users must re-run if they want brief-type-corrected scores. |
| Image quality not affecting scores | LOW | Add `visual_quality_score` extraction and pass to `DimensionEvaluator`, redeploy. Old results are unaffected. New evaluations pick up the signal automatically. |
| Wording sensitivity causing instability | MEDIUM | Add structured brief fields + `BriefParser` normalization. Users must re-submit campaigns with structured fields. Old free-text submissions remain in the system but are flagged as "legacy format." |
| Benchmark missing per-type labels | LOW | Add `brief_type` labels to existing benchmark examples before the first regression run. Benchmark data is JSON; label addition is a manual annotation task. |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Static path 404 (D1) | Phase D1 (Deployment Fix) | `curl http://localhost:5001/` returns 200; startup log shows resolved dist path |
| Serverless incompatibility (D2) | Phase D1 (Deployment Fix) | Restart container, poll existing task — result survives |
| Railway volume path mismatch (D3) | Phase D1 (Deployment Fix) | `/health` returns `uploads_writable: ok` after container restart |
| Flat weights bias conversion briefs (W1) | Phase W1 (Weight Profile) | Brand brief campaign does not win on `conversion_potential` dimension |
| Weight profile backward compatibility (W2) | Phase W1 (Weight Profile) | Old results load without re-scoring; `weight_profile_version` field present in new results |
| Image content not influencing scores (W3) | Phase W2 (Image Content Integration) | Campaign with high-quality images scores higher on `thumb_stop` than campaign with no images |
| Wording sensitivity (W4) | Phase W1 (Weight Profile) | Semantically equivalent briefs score within `CONFIDENCE_THRESHOLD` of each other |
| Benchmark without per-type labels (W5) | Phase W3 (Benchmark + Regression) | Benchmark runner outputs `brand_accuracy`, `seeding_accuracy`, `conversion_accuracy` separately |

## Sources

- Codebase analysis: `backend/app/__init__.py` (static path logic), `backend/app/services/probability_aggregator.py` (weight structure), `backend/app/services/submarket_evaluator.py` (dimension computation), `backend/app/services/pairwise_judge.py` (dimension list), `backend/app/services/evaluation_orchestrator.py` (visual_diagnostics pipeline), `docker-compose.yml` (volume config), `Dockerfile` (build paths)
- Known issues from milestone context: `/` returns 404 (server/index.ts line 48 in prior version, now `backend/app/__init__.py` line 117), Vercel `DEPLOYMENT_NOT_FOUND`, `conversionPotential`/`executionReadiness` over-weighting (lines 271-272 of prior evaluator), images as quantity bonus only (line 264), wording sensitivity
- [Railway persistent volumes documentation](https://docs.railway.com/reference/volumes)
- [Gunicorn deployment best practices](https://docs.gunicorn.org/en/stable/deploy.html) — `--chdir` interaction with `os.getcwd()`
- [Flask static file serving in production](https://flask.palletsprojects.com/en/stable/tutorial/deploy/) — `send_from_directory` path resolution
- [Judging the Judges: Position Bias in LLM-as-a-Judge (ACL 2025)](https://aclanthology.org/2025.ijcnlp-long.18/) — 10-30% verdict flip rate, systematic not random
- [Why Do Multi-Agent LLM Systems Fail? (arxiv 2503.13657)](https://arxiv.org/abs/2503.13657) — evaluation sensitivity and aggregation failure modes
- [Avoiding Common Pitfalls in LLM Evaluation](https://www.honeyhive.ai/post/avoiding-common-pitfalls-in-llm-evaluation) — structured input normalization to reduce wording sensitivity

---
*Pitfalls research for: Brand campaign simulation with LLM-based multimodal evaluation*
*Updated: 2026-03-18 (v2.1: deployment fix + evaluation bias correction)*
