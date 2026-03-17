# Pitfalls Research

**Domain:** Brand campaign simulation with LLM-based multimodal evaluation
**Researched:** 2026-03-17
**Confidence:** HIGH (grounded in codebase analysis + domain research)

## Critical Pitfalls

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
The pairwise comparison pipeline uses a single LLM model (Qwen via Bailian) as the sole judge. Research shows single-model LLM judges exhibit systematic biases: position bias (favoring the first or second option presented), verbosity bias (favoring longer descriptions), and self-enhancement bias. The Bradley-Terry model then amplifies these biases into confident-looking rankings -- more data makes rankings "more confidently wrong" when judge reliability is not modeled ([NAACL 2025 findings](https://aclanthology.org/2025.findings-naacl.260.pdf)).

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
`_evaluation_store` is a module-level `dict = {}` (campaign.py line 36) shared across all Flask request threads. When multiple users submit evaluations simultaneously -- which is an explicit goal ("cross-team usage support") -- background threads write nested dicts while request threads read them. Python's GIL prevents segfaults but does NOT prevent inconsistent reads of composite structures. A user could see a partial result (panel scores present, pairwise scores missing) that looks like a completed evaluation.

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
| Plaintext passwords in env var | Quick setup for internal tool | Credential exposure if env var leaks or logs are shared | Never -- bcrypt is a 3-line change |
| God class `BrandStateEngine` | All prediction logic in one place | Untestable, fragile, blocks parallel development | Only during initial port from MiroFish; must decompose before adding features |
| Calibration as flat JSON files | Quick to implement | Three persistence layers (SQLite + JSON results + JSON calibration), backup/restore is fragile | Acceptable for MVP if documented |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Qwen Vision API (Bailian) | Sending base64 images without size limits, hitting token ceiling silently | Resize to max 1024px, validate total payload size before API call |
| Qwen Vision API (Bailian) | Assuming all OpenAI-compatible features work identically | Test `detail` parameter support, max images per request, and token counting behavior specifically with Bailian endpoint |
| SQLite WAL mode | Enabling WAL but not setting `busy_timeout` | Always pair `PRAGMA journal_mode=WAL` with `PRAGMA busy_timeout=5000` for concurrent access |
| Flask background threads | Accessing Flask request context (`request`, `g`, `session`) from background thread | Pass all needed data as arguments to the background function; never reference Flask context objects |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Serial image analysis in Race path | Race evaluation takes 30-60s for 6 campaigns with images | Use `ThreadPoolExecutor` with max 3-4 workers for concurrent image analysis | >3 campaigns with images (noticeable at 6+) |
| `BaselineRanker` loading all interventions | API response time grows linearly with historical data | Push category/audience filters into SQL WHERE clause | >1000 historical interventions |
| No pagination on list endpoints | Browser hangs on Dashboard, API timeouts | Add `limit`/`offset` to store queries | >500 rows in any table |
| 30-75 LLM calls per Evaluate run | Single evaluation takes 90-150 seconds | Parallelize panel calls (already done), add caching for identical campaign-persona pairs | Always noticeable; acceptable with progress UI |

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

## "Looks Done But Isn't" Checklist

- [ ] **Image path fix:** Often missing -- verify that BOTH `AudiencePanel` AND `PairwiseJudge` use the resolver. Fixing one but not the other will still produce partially blind evaluations
- [ ] **Evaluate UI:** Often missing image count display -- verify the UI shows how many images were actually analyzed (not just uploaded)
- [ ] **Persona configuration:** Often missing version tracking -- verify that changing a persona doesn't retroactively change how old evaluations display
- [ ] **Concurrent access fix:** Often missing the SQLite side -- verify both `_evaluation_store` locking AND SQLite WAL mode are enabled together
- [ ] **Password hashing:** Often missing migration -- verify existing stored passwords are re-hashed, not just new passwords
- [ ] **CORS fix:** Often missing production config -- verify the fix works in Docker deployment, not just `localhost:5173`
- [ ] **Rate limiting:** Often missing the background thread case -- verify that a queued evaluation counts against the limit even after the HTTP response returns

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Silent image dropout | LOW | Fix resolver, re-run affected evaluations. No data loss since campaigns and images are persisted |
| Judge bias in rankings | MEDIUM | Add position-swap, re-run evaluations. Old rankings cannot be retroactively corrected but new ones will be more reliable |
| God class refactoring breaks Race | HIGH | Revert refactoring commit, add characterization tests first, try again. Risk of lost work if changes were interleaved with features |
| Concurrent state corruption | MEDIUM | Add lock, restart server. In-memory results may be lost but disk JSON files are intact. Re-serve from disk |
| Persona garbage evaluations | LOW | Delete bad evaluation results, fix persona presets, re-run. Users need to be told which results were affected |
| Base64 token overflow | LOW | Add resize step, re-run. No permanent damage since images are stored at original resolution |

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

## Sources

- Codebase analysis: `/Users/slr/MiroFishmoody/.planning/codebase/CONCERNS.md`
- [Avoiding Common Pitfalls in LLM Evaluation](https://www.honeyhive.ai/post/avoiding-common-pitfalls-in-llm-evaluation)
- [Justice or Prejudice? Quantifying Biases in LLM-as-a-Judge](https://arxiv.org/html/2410.02736v1)
- [Re-evaluating Automatic LLM System Ranking (NAACL 2025)](https://aclanthology.org/2025.findings-naacl.260.pdf) -- BT model amplifies biased judges
- [Judge-Aware Ranking Framework](https://arxiv.org/html/2601.21817v1) -- judge reliability modeling
- [LLM-as-a-jury for Comparative Assessment](https://arxiv.org/html/2602.16610) -- multi-judge ensembling
- [The 5 Biases in LLM Evaluations](https://www.sebastiansigl.com/blog/llm-judge-biases-and-how-to-fix-them) -- position, verbosity, self-enhancement bias mitigation
- [SQLite Threading](https://sqlite.org/threadsafe.html) -- official thread safety documentation
- [Python SQLite Thread Safety](https://ricardoanderegg.com/posts/python-sqlite-thread-safety/) -- practical Python guidance

---
*Pitfalls research for: Brand campaign simulation with LLM-based multimodal evaluation*
*Researched: 2026-03-17*
