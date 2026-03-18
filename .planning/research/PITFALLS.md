# Pitfalls Research

**Domain:** Brand campaign simulation with LLM-based multimodal evaluation
**Researched:** 2026-03-18 (updated for v2.0: frontend rewrite + multi-agent)
**Confidence:** HIGH (grounded in codebase analysis + domain research)

---

## v2.0 Milestone-Specific Pitfalls

The following pitfalls are specific to the two goals of this milestone:
(A) Frontend rewrite referencing MiroFish original while keeping Flask backend unchanged.
(B) Adding parallel multi-agent evaluation to the existing Qwen/Bailian pipeline.

---

### Pitfall F1: API Contract Drift During Frontend Rewrite

**What goes wrong:**
The rewrite starts with the MiroFish reference frontend and maps its data shapes to the existing Flask API. Midway through the rewrite, a developer changes a field name or nests a previously flat payload to match MiroFish conventions, without updating the Flask route. Both sides compile; the runtime error is silent: the field arrives as `undefined`, a default value kicks in, and the evaluation runs with the wrong parameter. In this codebase, the risk points are:
- `product_line` vs `productLine` (camelCase/snake_case mismatch between store.ts and Flask routes)
- `category` field used in Evaluate payload but not validated on the backend — can silently default
- Image path format: the store holds `File` objects; the API expects already-uploaded paths from `/api/campaign/upload`

**Why it happens:**
Frontend rewrites reference two sources simultaneously (MiroFish original + current Flask API), and the two have divergent naming conventions. Developers copy field names from the wrong source.

**How to avoid:**
- Before writing any new component, create a `contracts.ts` file that mirrors each Flask route's expected request/response shape exactly (copy from `api.ts`, expand where needed).
- Run `npm run build` after every component — TypeScript strict mode will catch most shape mismatches at compile time if API types are accurate.
- Never change a field name without checking the Flask route handler first. Changes to the API layer require a corresponding backend change.

**Warning signs:**
- A field is `undefined` in a network request body where a string is expected
- Evaluation runs without error but `category` defaults to `null`, causing the wrong persona set to load
- Backend logs show `KeyError` on fields that were renamed on the frontend side

**Phase to address:**
Phase F1 (Frontend Foundation) — lock down `contracts.ts` before writing page components.

---

### Pitfall F2: MiroFish Reference Logic Carries Assumptions That Don't Match This Backend

**What goes wrong:**
MiroFish (https://github.com/666ghj/MiroFish) was built for a different backend with different data models. Developers copy interaction flows verbatim: routing logic, state management patterns, polling mechanisms. Some patterns are incompatible:
- MiroFish may use different polling patterns (WebSocket, SSE, or different HTTP polling intervals) vs. the current `GET /api/campaign/task/<task_id>` polling approach
- MiroFish campaign model differs from the `CampaignPlan` / `EvaluatePayload` types in this codebase
- File upload flow in MiroFish may differ from the current `/api/campaign/upload` + path reference pattern

**Why it happens:**
"Reference the original" is interpreted as "copy from the original." Logic that worked in MiroFish's context is assumed to work here without verifying the API contract.

**How to avoid:**
- Treat MiroFish as a UI/UX reference, not a code reference. Copy visual design and interaction flow, not data models or API calls.
- Before implementing any data-flow component, document which Flask API endpoint it calls and what shape it expects.
- The existing `lib/api.ts` is the authoritative source for API shape. New components must import from it — never replicate API call logic inline.

**Warning signs:**
- A component polls an endpoint that doesn't exist in Flask
- Image upload uses a different multipart field name than the Flask route expects
- A new store slice has fields not present in any Flask response

**Phase to address:**
Phase F1 (Frontend Foundation) — review MiroFish source before writing any page, extract only the UI patterns.

---

### Pitfall F3: Zustand Store State Surviving a Rewrite Creates Ghost State Bugs

**What goes wrong:**
The current `store.ts` uses in-memory Zustand state (no persistence). The rewrite adds new fields or restructures the store. If old store shape is still in memory (from a hot-reload or browser tab kept open), stale closures capture the old shape and the new component reads `undefined` where a value is expected. In the specific case of `iterateState.parentSetId` (which is set when iterating on a campaign version), stale state from the previous version chain could be silently injected into a new evaluation.

**Why it happens:**
In-memory state during development doesn't have schema migrations. Hot-reload keeps old state alive. Adding fields to a Zustand store while the app is running means the old state object doesn't have the new fields.

**How to avoid:**
- When restructuring the store, always hard-refresh (not hot-reload) before testing the new shape.
- Add a store version key and reset state when the version changes. For the `iterateState` in particular, assert that `parentSetId` is cleared before every new evaluation submission (this already exists in `clearIterateState()` — preserve it in the rewrite).
- For critical state transitions (submitting an evaluation, clearing iterate state), add explicit `console.log` entries during development to confirm the state is what's expected.

**Warning signs:**
- `parentSetId` appears in a new evaluation request that shouldn't have it
- A new evaluation inherits plan data from a previous session
- Form fields show stale values on first render after navigation

**Phase to address:**
Phase F1 (Frontend Foundation) — validate state shape reset behavior as part of the store rewrite.

---

### Pitfall F4: Both Mode Race Condition: Evaluate Task ID Lost Before Navigation

**What goes wrong:**
In `Both` mode, the current code fires `evaluateCampaigns()` asynchronously without waiting, then immediately navigates to `/running` for the Race result. If the evaluate API call completes after the navigation but before `saveEvaluateState` is called, the task ID is stored correctly. But if the evaluate call fails silently (network error, rate limit), `bothModeState.evaluateTaskId` is never set. When the user clicks "View Evaluate Results" from the Race result page, there is no task ID to poll. The UI shows an error with no explanation.

This is a known issue flagged in `PROJECT.md` as "Race→Evaluate 跨模式迭代 parentSetId 传空" — the rewrite must fix this explicitly, not carry it forward.

**Why it happens:**
The fire-and-forget pattern is convenient for UX (not blocking Race navigation) but creates a gap between "task submitted" and "task ID persisted."

**How to avoid:**
- Change the Both mode flow: fire both Race and Evaluate requests concurrently using `Promise.all`, navigate to `/running` only after both task IDs are confirmed. The latency difference is minimal (both are HTTP POST calls that return task IDs within 200ms).
- If one fails, show a specific error: "Evaluate submission failed — proceeding with Race only." Do not silently hide the failure.
- The Evaluate task ID must be stored before navigation in both the `evaluate` and `both` paths.

**Warning signs:**
- User completes Race, clicks "View Evaluate" on ResultPage, gets an empty or error state
- `bothModeState.evaluateTaskId` is null/undefined when ResultPage tries to link to Evaluate results
- Network tab shows evaluate POST completing after page navigation

**Phase to address:**
Phase F2 (Both Mode and Navigation) — fix the race condition explicitly when reimplementing `handleSubmit`.

---

### Pitfall M1: Agent Count Growth Without Concurrency Budget Control

**What goes wrong:**
Adding more evaluation agents (more personas, more pairwise judges, more image analyzers) increases parallelism. With 6 personas and 5 campaigns, the panel phase already fires 30 LLM calls. Adding 3 more agent types multiplies this. Without a concurrency limit, all calls fire simultaneously, hit Bailian's RPM/TPM quota, receive 429 errors, and the entire evaluation fails with a cryptic timeout. The current `Semaphore` in `ImageAnalyzer` controls image analysis concurrency but does not gate the combined load of panel + pairwise + new agents.

**Why it happens:**
Each agent type is developed independently and adds its own executor. There is no global concurrency budget across the whole pipeline. Local testing with 1-2 campaigns doesn't hit rate limits; production usage with 5 campaigns does.

**How to avoid:**
- Introduce a single global `LLMSemaphore` at the `LLMClient` level, not per-service. All LLM calls go through `LLMClient`; the semaphore there enforces a global concurrent call ceiling.
- Set the ceiling based on Bailian's actual RPM limit (check the Alibaba Cloud Model Studio rate limit docs). A safe default is 8-12 concurrent calls for free/trial tiers, 20-40 for paid tiers.
- Log the semaphore queue depth during evaluations. If it consistently exceeds 10, the pipeline is bottle-necked; this is a signal to implement request batching.
- Add retry with exponential backoff for 429 responses specifically (the current error handling logs and fails; it should retry up to 3 times with 2s, 4s, 8s delays).

**Warning signs:**
- Evaluate evaluations that pass for 2 campaigns but fail for 5
- HTTP 429 errors in LLM client logs during peak usage
- Evaluation wall-clock time growing super-linearly as campaign count increases

**Phase to address:**
Phase M1 (Multi-Agent Foundation) — implement global semaphore before adding any new agent types.

---

### Pitfall M2: Score Schema Inconsistency Between Old and New Agents

**What goes wrong:**
The existing `AudiencePanel` returns scores in a specific shape consumed by `CampaignScorer`. New agent types (e.g., a "strategic fit" agent, a "market positioning" agent) return scores in a different schema. `CampaignScorer` aggregates by iterating `panel_scores` and `pairwise_results`; if a new agent type returns a hybrid schema, the scorer silently ignores fields it doesn't recognize and produces rankings that exclude the new agent's signal entirely. The developer sees "it works" because no exception is raised.

**Why it happens:**
Adding an agent type feels like a feature addition, not a schema change. The scorer's aggregation logic is not tested for forward compatibility.

**How to avoid:**
- Define a `AgentScore` dataclass or TypedDict with required fields (`campaign_id`, `score: float`, `dimensions: dict[str, float]`, `agent_type: str`) before implementing any new agent. All agents must return this shape.
- Add a schema validation step in `EvaluationOrchestrator.run()` that raises immediately if any agent returns a result missing required fields. Fail loudly rather than silently skip.
- Add a unit test for `CampaignScorer` that exercises 3+ agent types simultaneously and asserts all are represented in the final ranking.

**Warning signs:**
- New agent type produces results in logs but the final ranking doesn't reflect the new signal
- `CampaignScorer` aggregation produces identical rankings before and after adding a new agent
- `scoreboard.to_dict()` output has no trace of the new agent's dimensions

**Phase to address:**
Phase M1 (Multi-Agent Foundation) — define `AgentScore` schema as the first step before implementing any new agent.

---

### Pitfall M3: Cascade Failure in Sequential Agent Pipeline Silently Degrades Results

**What goes wrong:**
The current pipeline is sequential: Panel → Image Analysis → Pairwise → Scoring → Summary. If the Image Analysis phase fails (e.g., one campaign's images are too large and hit a token limit), the exception is caught, logged, and skipped. The pipeline continues and produces a result. But the Scoring phase now has incomplete input: it aggregates a `visual_diagnostics` dict that's missing entries for some campaigns. A user looking at the result cannot tell which campaigns were analyzed with images and which were not. Rankings that depend on visual analysis are silently based on incomplete data.

This is compounded when adding more agent stages: each new "optional" stage that fails silently degrades the result quality without any indication.

**Why it happens:**
Silent failure is a common pattern for "nice to have" features — if it fails, continue without it. But when the feature is central to the product's value proposition (visual campaign evaluation), silent failure is a product bug, not graceful degradation.

**How to avoid:**
- Add a `result_metadata` field to `EvaluationResult` that records which agents ran, how many succeeded, and any failures. Example: `{"image_analysis": {"attempted": 5, "succeeded": 3, "failed_campaigns": ["campaign_b"]}}`.
- Surface this metadata in the frontend: show a warning banner when any agent partially failed. "Note: image analysis failed for 2 of 5 campaigns — their visual scores are excluded."
- For new agent types, classify them as either "required" (failure stops the pipeline) or "supplementary" (failure records in metadata, pipeline continues). Pairwise judgment is required; market trend analysis might be supplementary.

**Warning signs:**
- Evaluation results with unexpectedly low confidence scores for some campaigns
- Missing fields in `visual_diagnostics` without any error in the result
- Users reporting inconsistent rankings that change when they re-run the same campaigns

**Phase to address:**
Phase M1 (Multi-Agent Foundation) — add `result_metadata` to `EvaluationResult` before adding any new agent type.

---

### Pitfall M4: Position Bias Compounding in Pairwise Ensemble

**What goes wrong:**
The current `PairwiseJudge` already performs position swapping (A/B and B/A) as a debiasing mechanism. When adding more judges to the ensemble, a naive implementation calls all judges with the same ordering (A first, B second). Position bias — which causes 10-30% verdict flips when order is swapped — is then consistent across all judges. Majority voting across biased judges amplifies the bias rather than canceling it.

Research from ACL 2025 confirms that position bias in pairwise LLM evaluation is systematic, not random: the same model consistently favors the first or second position across runs. Multiple calls to the same model with the same order produce the same biased result, not a distribution.

**Why it happens:**
Adding more judges is understood as "reducing variance." It does reduce variance. But if all judges share the same systematic bias, it also reduces the signal that would reveal the bias.

**How to avoid:**
- When running N judges in parallel on the same pair, alternate presentation order: half receive (A, B), half receive (B, A). Majority vote only counts when there is genuine agreement across orderings.
- Track per-judge consistency: for each judge, measure what fraction of pairs produce the same verdict when order is swapped. A judge with <70% consistency is unreliable; flag its results.
- Use the existing `PairwiseJudge` position-swap mechanism as the template for any new judge type. Do not write new judge classes that skip this step.

**Warning signs:**
- Adding more judges increases confidence in a ranking that humans disagree with
- All 3 judges pick the same winner for all pairs, regardless of which campaign seems better
- Consistency metric (same verdict with swapped order) below 70% for any judge

**Phase to address:**
Phase M2 (Multi-Agent Evaluation Enhancement) — enforce position-alternation as a requirement in the judge interface before adding any new judge implementation.

---

### Pitfall M5: Calibration System Starvation on New Agent Types

**What goes wrong:**
`JudgeCalibration` computes per-persona and per-judge weights, but requires 5+ resolved evaluation sets before weights activate. New agent types added in v2.0 start with zero calibration data. The system applies equal weight to all agents (including new untested ones) until enough data accumulates. An unreliable new agent has full voting power in rankings until users manually resolve enough evaluations to teach the system its unreliability. In practice, the calibration data required may never accumulate if users don't systematically mark post-hoc results.

**Why it happens:**
Calibration systems work well when there is dense labeled data. For internal brand tools with infrequent usage (one campaign evaluation per week), calibration data accumulates slowly. New agent types effectively bypass calibration indefinitely.

**How to avoid:**
- Set new agent types to a lower default weight (e.g., 0.3x the weight of established agents) until they have 10+ resolved evaluations.
- Alternatively, exclude new agent types from ranking aggregation entirely for the first month, and use them only to surface supplementary signals (not to influence the final ranking).
- Document explicitly which agents are "calibrated" vs "provisional" in the UI. Show a badge: "Beta — does not affect ranking."

**Warning signs:**
- New agent producing wildly different rankings from established agents without explanation
- Calibration JSON files show 0 predictions for a new agent type after several weeks
- Users expressing confusion about why rankings changed after adding a new agent

**Phase to address:**
Phase M2 (Multi-Agent Enhancement) — define default weights for new agents before enabling them in the ranking pipeline.

---

## Original Pitfalls (v1.x, still apply in v2.0)

### Pitfall 1: Silent Image Dropout in LLM Evaluation

**What goes wrong:**
Images are silently ignored during evaluation. The Evaluate path receives `image_paths` as API URL strings (e.g. `/api/campaign/image-file/...`), but `AudiencePanel` (line 181) and `PairwiseJudge` (line 129) call `os.path.exists()` on these strings. This always returns `False`, so images are quietly skipped. The evaluation completes without error -- users see scores that appear valid but were computed without visual context. For a brand whose core differentiator is visual aesthetics, this makes the entire evaluation meaningless.

**Why it happens:**
The Race path was built first with `ImageAnalyzer._resolve_image_url_to_path()`. When the Evaluate path was added, it duplicated the image-handling pattern without importing the resolver. Two different image resolution strategies coexist with no shared abstraction.

**How to avoid:**
- Extract a single `resolve_image_path(path_or_url: str) -> Optional[Path]` utility used by all services
- Add a validation step in `EvaluationOrchestrator.run()` that logs a WARNING and includes it in the result metadata if zero images were successfully resolved
- Write an integration test that submits a campaign with API URL image_paths to `/api/campaign/evaluate` and asserts that LLM receives `image_url` content parts

**Warning signs:**
- Evaluate results show identical scores for campaigns with wildly different visuals
- No `image_url` content parts in LLM request logs during Evaluate runs
- `os.path.exists` calls on strings containing `/api/` or `http`

**Phase to address:**
Phase 1 (Bug Fix) -- this is the highest priority fix because it silently corrupts all Evaluate results.

---

### Pitfall 2: LLM Judge Bias Producing Confidently Wrong Rankings

**What goes wrong:**
The pairwise comparison pipeline uses a single LLM model (Qwen via Bailian) as the sole judge. Research shows single-model LLM judges exhibit systematic biases: position bias (favoring the first or second option presented), verbosity bias (favoring longer descriptions), and self-enhancement bias. The Bradley-Terry model then amplifies these biases into confident-looking rankings -- more data makes rankings "more confidently wrong" when judge reliability is not modeled.

**Why it happens:**
The BT model assumes all pairwise comparisons are independent and equally reliable. When a single biased judge produces all comparisons, systematic errors compound rather than cancel. The system has no mechanism to detect or correct for judge bias.

**How to avoid:**
- Randomize presentation order in pairwise comparisons (swap A/B positions across runs). Run each pair twice with swapped order; flag inconsistent judgments
- Add position-swap consistency check: if judge picks A when A is first but picks B when B is first, that pair's result should be marked as uncertain
- Track judge consistency metrics over time via `JudgeCalibration` -- the calibration system exists but needs 5+ resolved sets to activate, so bootstrap it with synthetic gold-standard pairs
- Consider ensemble judging (multiple LLM calls with different system prompts or temperatures) for high-stakes Evaluate runs

**Warning signs:**
- Rankings that change significantly when campaign descriptions are reordered
- One campaign consistently winning despite human reviewers disagreeing
- BT model confidence intervals that are suspiciously narrow with few data points
- Calibration system stuck at <5 resolved sets for extended periods

**Phase to address:**
Phase 2 (Evaluate UI + Persona Config) -- when building the Evaluate frontend, add position-swap as a default behavior in `PairwiseJudge.evaluate_all()`. Calibration bootstrapping can come in Phase 3.

---

### Pitfall 3: God Class Decomposition That Breaks Working Features

**What goes wrong:**
`BrandStateEngine` (1319 lines) handles state construction, replay, prediction, scenario simulation, diffusion, and backtesting. The natural instinct is to refactor it into separate classes. But aggressive decomposition without comprehensive tests first will break working Race path functionality. The class has implicit coupling between its methods -- state built by `construct()` is consumed by `predict()` in ways that aren't obvious from method signatures.

**Why it happens:**
Refactoring feels productive and looks clean in PRs. But forked codebases (MiroFish origin) have undocumented invariants. Breaking a God class is only safe when you have tests that verify the end-to-end behavior, not just unit tests on individual methods.

**How to avoid:**
- Write characterization tests BEFORE refactoring: capture current input/output pairs for `BrandStateEngine` as golden snapshots
- Refactor incrementally: extract one responsibility at a time (start with `BacktestEngine` which is least coupled), verify all characterization tests pass after each extraction
- Do NOT refactor in the same phase as feature additions -- refactoring is a separate phase with its own verification

**Warning signs:**
- Race path results change after refactoring (even slightly different scores indicate broken invariants)
- Tests that mock internal methods of `BrandStateEngine` -- these tests will pass even when the refactoring breaks real behavior
- PRs that extract 3+ classes at once

**Phase to address:**
Phase 3 or later (Tech Debt) -- only after Evaluate UI and image fix are stable. Must be preceded by characterization test creation.

---

### Pitfall 4: Concurrent Access Corruption on Shared Mutable State

**What goes wrong:**
`_evaluation_store` is a module-level `dict = {}` (campaign.py line 36) shared across all Flask request threads. When multiple users submit evaluations simultaneously, background threads write nested dicts while request threads read them. Python's GIL prevents segfaults but does NOT prevent inconsistent reads of composite structures. A user could see a partial result (panel scores present, pairwise scores missing) that looks like a completed evaluation.

Additionally, SQLite without WAL mode will throw `OperationalError: database is locked` under concurrent writes. `BrandictionStore` opens a new connection per operation with no pooling or retry logic.

**Why it happens:**
Single-user development environment hides concurrency bugs. Flask's threaded mode is the default but developers test with one browser tab.

**How to avoid:**
- Wrap `_evaluation_store` access with `threading.Lock()` immediately -- this is a 5-line fix
- Enable SQLite WAL mode (`PRAGMA journal_mode=WAL`) in `BrandictionStore.__init__()` -- another one-liner
- Add a retry loop with exponential backoff for `OperationalError: database is locked` in `_connect()`
- Use thread-local connections (`threading.local()`) instead of creating new connections per operation
- Test concurrent access: write a pytest that spawns 5 threads submitting evaluations simultaneously

**Warning signs:**
- Users report "evaluation completed" but results are missing fields
- `OperationalError: database is locked` in server logs
- Evaluation results that show different data on page refresh vs. initial load

**Phase to address:**
Phase 1 (Stability) -- must be fixed before enabling cross-team usage. The lock and WAL fixes are trivial; do them before the Evaluate UI launch.

---

### Pitfall 5: Persona Configuration Without Validation Creates Garbage Evaluations

**What goes wrong:**
The plan includes "configurable personas by category" (different reviewer personas for transparent vs. colored lenses). If persona prompts are user-editable without validation, users can create personas that produce incoherent or contradictory evaluations. A poorly written persona prompt ("be harsh and rate everything 1/10") will produce scores that the BT model treats as equally valid, dragging down all rankings.

**Why it happens:**
Configurability feels like a feature. But LLM prompt quality directly determines output quality. Treating persona prompts as free-text user input is like letting users write their own SQL queries -- technically powerful, practically dangerous.

**How to avoid:**
- Provide curated preset persona sets per category (e.g., "transparent lens buyer: female 25-35, comfort-focused, price-sensitive" for moodyPlus). Let users select from presets, not write free-form prompts
- If custom personas are needed, validate against a schema: require age range, gender, purchase motivation, product experience level
- Add a "persona dry run" that shows how a persona would evaluate a known-good campaign before using it in a real evaluation
- Store persona versions: when a persona is changed, old evaluations retain a reference to the persona version used

**Warning signs:**
- Evaluation scores that are all clustered at extremes (all 9-10 or all 1-2)
- Persona descriptions that don't mention any product-relevant attributes
- Different team members getting wildly different rankings for the same campaigns because they configured different personas

**Phase to address:**
Phase 2 (Persona Config) -- build presets first, custom later. The schema validation should gate any custom persona creation.

---

### Pitfall 6: Base64 Image Encoding Blowing Up LLM Token Budget

**What goes wrong:**
Each image is base64-encoded and sent inline in the LLM request. A single high-resolution campaign KV image (3-5MB) becomes ~4-7MB of base64 text. With 5 images per campaign and 5 personas in the panel, that's 25 image encodings per evaluation. Qwen's vision API has token limits; exceeding them causes silent truncation or API errors. The cost per evaluation also scales linearly with image size.

**Why it happens:**
Base64 inline is the simplest multimodal integration pattern. It works fine with 1-2 small images but breaks at scale. No image preprocessing exists in the current pipeline.

**How to avoid:**
- Resize images before encoding: cap at 1024x1024 or 768px longest edge. Campaign KV aesthetics are preserved at this resolution for LLM analysis
- Cache base64-encoded images per evaluation session (encode once, reuse across 5 persona calls)
- Add image size validation on upload: reject images >10MB, warn on >5MB
- Monitor LLM API costs per evaluation and set a budget ceiling with alerting
- If Qwen supports URL-based image input (some OpenAI-compatible APIs do), use that instead of base64 to reduce payload size

**Warning signs:**
- LLM API calls timing out or returning truncated responses
- Evaluation cost per run increasing over time as users upload higher-resolution images
- `413 Request Entity Too Large` or similar errors in API logs

**Phase to address:**
Phase 1 (Image Fix) -- when fixing the image path resolution, add resize preprocessing in the same change. Don't fix the path without fixing the payload size.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| In-memory `_evaluation_store` dict | No DB schema needed for results | Memory leak, no thread safety, lost on restart | Never -- disk persistence already exists via JSON files, the dict is redundant |
| New SQLite connection per operation | No connection management code | Connection overhead, no WAL mode, locked DB under load | MVP with single user only |
| Plaintext passwords in env var | Quick setup for internal tool | Credential exposure if env vars leak or logs are shared | Never -- bcrypt is a 3-line change |
| God class `BrandStateEngine` | All prediction logic in one place | Untestable, fragile, blocks parallel development | Only during initial port from MiroFish; must decompose before adding features |
| Calibration as flat JSON files | Quick to implement | Three persistence layers (SQLite + JSON results + JSON calibration), backup/restore is fragile | Acceptable for MVP if documented |
| MiroFish code copy-paste | Fast reference implementation | Naming convention drift, ghost assumptions, hidden coupling to different backend | Never for data-flow code; acceptable for pure UI components with no API calls |
| One global LLM client, no semaphore at call site | Simple | Rate limit breaches when multi-agent adds concurrent calls | Never with more than 2 agent types running in parallel |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Qwen Vision API (Bailian) | Sending base64 images without size limits, hitting token ceiling silently | Resize to max 1024px, validate total payload size before API call |
| Qwen Vision API (Bailian) | Assuming all OpenAI-compatible features work identically | Test `detail` parameter support, max images per request, and token counting behavior specifically with Bailian endpoint |
| Bailian rate limits (v2.0) | Each new agent type adds its own concurrent call burst; combined load exceeds RPM | Implement global semaphore in `LLMClient`; all agents share one concurrency ceiling |
| SQLite WAL mode | Enabling WAL but not setting `busy_timeout` | Always pair `PRAGMA journal_mode=WAL` with `PRAGMA busy_timeout=5000` for concurrent access |
| Flask background threads | Accessing Flask request context (`request`, `g`, `session`) from background thread | Pass all needed data as arguments to the background function; never reference Flask context objects |
| React rewrite + Flask backend | Renaming fields to match MiroFish naming conventions without updating Flask routes | Lock API contract in `contracts.ts`; `npm run build` catches mismatches with TypeScript strict mode |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Serial image analysis in Race path | Race evaluation takes 30-60s for 6 campaigns with images | Use `ThreadPoolExecutor` with max 3-4 workers for concurrent image analysis | >3 campaigns with images (noticeable at 6+) |
| `BaselineRanker` loading all interventions | API response time grows linearly with historical data | Push category/audience filters into SQL WHERE clause | >1000 historical interventions |
| No pagination on list endpoints | Browser hangs on Dashboard, API timeouts | Add `limit`/`offset` to store queries | >500 rows in any table |
| 30-75 LLM calls per Evaluate run | Single evaluation takes 90-150 seconds | Parallelize panel calls (already done), add caching for identical campaign-persona pairs | Always noticeable; acceptable with progress UI |
| Multi-agent burst without global semaphore | 429 errors and evaluation failures at 5 campaigns | Global semaphore at `LLMClient` level, not per-service | >2 agent types running in parallel (v2.0 threshold) |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Plaintext password comparison | Credential theft if env vars leak (logs, process list, container inspection) | Hash with bcrypt on storage, compare with `bcrypt.checkpw()` |
| `SECRET_KEY` fallback to hardcoded string | Session cookie forgery -- attacker can impersonate any user | Remove default value, crash on startup if `SECRET_KEY` not set |
| `FLASK_DEBUG=True` as default | Werkzeug debugger exposes arbitrary Python execution if server is network-accessible | Default to `False`, require explicit opt-in |
| No rate limiting on LLM endpoints | Single user can exhaust entire LLM API quota with one large evaluation batch | Add per-user rate limit (e.g., max 3 concurrent evaluations) and global queue depth limit |
| `set_id` not scoped to user | Users can read/overwrite each other's uploaded images by guessing `set_id` | Prefix upload directory with authenticated username |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Evaluate results shown without indicating image analysis status | Users trust scores that were computed without visual analysis (the current silent dropout bug) | Show explicit "images analyzed: 3/5" or "no images included" badge on each result |
| No progress indication during 90-150s evaluation | Users think the tool is broken, refresh the page, trigger duplicate evaluations | Show phase-by-phase progress bar (Panel 40%, Pairwise 80%, Scoring 90%) -- the `TaskManager` already supports this |
| Showing BT model scores as absolute numbers | Users compare scores across different evaluation sessions (scores are relative, not absolute) | Show rankings (1st, 2nd, 3rd) prominently; show scores only as secondary detail with "relative within this evaluation" label |
| Persona names shown in Chinese jargon | Non-marketing team members (e.g., media buyers) don't understand persona descriptions | Show persona as "25-35 female, comfort-priority" not internal persona IDs |
| Race and Evaluate results not cross-referenced | Users run both paths but can't see whether they agree or disagree | Add a comparison view: "Race ranked A>B>C, Evaluate ranked B>A>C -- investigate B vs A" |
| Both mode evaluate failure with no UI feedback | User completes Race, sees no Evaluate tab, doesn't know why | Show "Evaluate not available — submission failed" with retry option instead of silent omission |

## "Looks Done But Isn't" Checklist

- [ ] **Image path fix:** Often missing -- verify that BOTH `AudiencePanel` AND `PairwiseJudge` use the resolver. Fixing one but not the other will still produce partially blind evaluations
- [ ] **Evaluate UI:** Often missing image count display -- verify the UI shows how many images were actually analyzed (not just uploaded)
- [ ] **Persona configuration:** Often missing version tracking -- verify that changing a persona doesn't retroactively change how old evaluations display
- [ ] **Concurrent access fix:** Often missing the SQLite side -- verify both `_evaluation_store` locking AND SQLite WAL mode are enabled together
- [ ] **Password hashing:** Often missing migration -- verify existing stored passwords are re-hashed, not just new passwords
- [ ] **CORS fix:** Often missing production config -- verify the fix works in Docker deployment, not just `localhost:5173`
- [ ] **Rate limiting:** Often missing the background thread case -- verify that a queued evaluation counts against the limit even after the HTTP response returns
- [ ] **Frontend rewrite API contract:** Often missing -- verify every field name in new components matches the Flask route exactly (snake_case on backend, checked via `contracts.ts`)
- [ ] **Both mode race condition:** Often missing -- verify `evaluateTaskId` is stored before navigation in Both mode, not after
- [ ] **Global LLM semaphore:** Often missing -- verify the semaphore is applied at `LLMClient` level, not independently in each new agent's executor
- [ ] **New agent score schema:** Often missing -- verify new agents return `AgentScore`-compatible shape before integrating with `CampaignScorer`
- [ ] **Multi-agent result metadata:** Often missing -- verify `EvaluationResult` records which agents ran and which partially failed

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Silent image dropout | LOW | Fix resolver, re-run affected evaluations. No data loss since campaigns and images are persisted |
| Judge bias in rankings | MEDIUM | Add position-swap, re-run evaluations. Old rankings cannot be retroactively corrected but new ones will be more reliable |
| God class refactoring breaks Race | HIGH | Revert refactoring commit, add characterization tests first, try again. Risk of lost work if changes were interleaved with features |
| Concurrent state corruption | MEDIUM | Add lock, restart server. In-memory results may be lost but disk JSON files are intact. Re-serve from disk |
| Persona garbage evaluations | LOW | Delete bad evaluation results, fix persona presets, re-run. Users need to be told which results were affected |
| Base64 token overflow | LOW | Add resize step, re-run. No permanent damage since images are stored at original resolution |
| API contract drift in rewrite | MEDIUM | Audit each component's API call against Flask routes, fix mismatches, rebuild. TypeScript will surface most issues at compile time |
| Multi-agent rate limit failure | LOW | Add global semaphore, reduce default parallelism. No data loss; re-run evaluation. |
| Both mode evaluate task ID lost | LOW | Fix `Promise.all` ordering in `handleSubmit`, re-run. User must resubmit the evaluate run manually for affected campaigns |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Silent image dropout | Phase 1 (Bug Fix) | Integration test: submit campaign with API URL image_paths, assert LLM receives image content |
| Concurrent state corruption | Phase 1 (Stability) | Concurrent pytest: 5 threads submit evaluations simultaneously, all complete without error |
| Base64 token overflow | Phase 1 (Image Fix) | Unit test: 5MB image is resized to <500KB before encoding |
| Security basics (password, SECRET_KEY, DEBUG) | Phase 1 (Security) | Startup test: server crashes if SECRET_KEY not set; password comparison uses bcrypt |
| LLM judge bias | Phase 2 (Evaluate Enhancement) | Position-swap test: same pair evaluated A/B and B/A, consistency tracked |
| Persona configuration | Phase 2 (Persona Config) | Schema validation test: reject persona without age/gender/motivation fields |
| God class decomposition | Phase 3 (Tech Debt) | Characterization tests pass before AND after each extraction |
| Rate limiting | Phase 2 (Cross-team) | Load test: 4th concurrent evaluation is queued, not started |
| API contract drift (v2.0 frontend rewrite) | Phase F1 (Frontend Foundation) | `npm run build` passes; `contracts.ts` manually audited against Flask routes |
| MiroFish assumptions mismatch (v2.0) | Phase F1 (Frontend Foundation) | Each new component's API call traced to a specific Flask route handler |
| Zustand ghost state (v2.0) | Phase F1 (Frontend Foundation) | Hard-refresh test: store resets cleanly between sessions |
| Both mode race condition (v2.0) | Phase F2 (Both Mode) | Test: evaluate task ID is non-null in `bothModeState` immediately after navigate('/running') |
| Global LLM semaphore (v2.0 multi-agent) | Phase M1 (Multi-Agent Foundation) | Stress test: 5-campaign evaluation with 3 agent types completes without 429 errors |
| Agent score schema inconsistency (v2.0) | Phase M1 (Multi-Agent Foundation) | Unit test: `CampaignScorer` rejects agent result missing required fields |
| Cascade failure degradation (v2.0) | Phase M1 (Multi-Agent Foundation) | `result_metadata` present in all EvaluationResult outputs; frontend displays warning when agents partially failed |
| Position bias in ensemble (v2.0) | Phase M2 (Judge Ensemble) | Consistency test: judge verdict match rate >70% across order-swapped pairs |
| Calibration starvation (v2.0) | Phase M2 (Judge Ensemble) | New agent types start at 0.3x weight; documented in agent config |

## Sources

- Codebase analysis: `/Users/slr/MiroFishmoody/.planning/codebase/CONCERNS.md`
- [Why Do Multi-Agent LLM Systems Fail? (arxiv 2503.13657)](https://arxiv.org/abs/2503.13657) — 3-category, 14-failure-mode taxonomy; kappa=0.88 across 150 traces
- [Judging the Judges: Position Bias in LLM-as-a-Judge (ACL 2025)](https://aclanthology.org/2025.ijcnlp-long.18/) — 10-30% verdict flip rate from order swap; systematic not random
- [Justice or Prejudice? Quantifying Biases in LLM-as-a-Judge](https://llm-judge-bias.github.io/) — 12 bias types including position, verbosity, self-enhancement
- [Avoiding Common Pitfalls in LLM Evaluation](https://www.honeyhive.ai/post/avoiding-common-pitfalls-in-llm-evaluation) — rubric consistency, score schema standardization
- [Alibaba Cloud Model Studio Rate Limits](https://www.alibabacloud.com/help/en/model-studio/rate-limit) — Bailian API RPM/TPM limits
- [Multi-Agent Evaluation System (Cognizant)](https://www.cognizant.com/us/en/ai-lab/blog/ai-scoring-multi-agent-evaluation-system) — score aggregation and schema normalization patterns
- [Strangler Fig Pattern pitfalls (AWS)](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/strangler-fig.html) — API contract maintenance during incremental rewrites
- SQLite analysis: `/Users/slr/MiroFishmoody/backend/app/services/evaluation_orchestrator.py`, `store.ts`, `api.ts`

---
*Pitfalls research for: Brand campaign simulation with LLM-based multimodal evaluation*
*Updated: 2026-03-18 (v2.0: frontend rewrite + multi-agent enhancement)*
