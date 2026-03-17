# Project Research Summary

**Project:** MiroFishmoody -- Brand Campaign Simulation Engine Enhancement
**Domain:** Brand campaign pre-testing / AI synthetic audience evaluation (internal tool for beauty/contact lens brand)
**Researched:** 2026-03-17
**Confidence:** HIGH

## Executive Summary

MiroFishmoody is an internal brand campaign pre-testing tool for Moody Lenses that uses LLM-based synthetic audience panels to evaluate and rank campaign creatives. The product already has a working Race path (quick ranking) and a backend-only Evaluate path (deep AI jury analysis with Bradley-Terry scoring). The core architecture -- Flask monolith, React SPA, Qwen/Bailian LLM, SQLite persistence -- is sound and should be kept. The project is not greenfield; the primary work is completing the Evaluate path frontend, fixing critical bugs, and enhancing the evaluation pipeline's reliability.

The recommended approach is a 5-phase build: (1) fix the silent image dropout bug and concurrent access issues that would corrupt all downstream work, (2) build the PersonaRegistry and category-based persona configuration that Moody's dual-category business demands, (3) parallelize image analysis for performance, (4) build the Evaluate frontend and unified entry UI, (5) combine Race + Evaluate results into a single view. This order is driven by hard dependencies: the image bug silently invalidates all Evaluate results, persona config must exist before the frontend can offer category selection, and concurrent image analysis is an independent performance win.

The top risks are: silent image dropout producing confidently wrong scores (critical -- fix first), LLM judge position bias amplified by Bradley-Terry into misleadingly confident rankings (mitigate with position-swap in pairwise comparisons), and the temptation to refactor the 1319-line BrandStateEngine God class before stabilizing the Evaluate path (defer refactoring until characterization tests exist). The existing stack needs only 3 new backend dependencies (bcrypt, langfuse, structlog) and 2 frontend additions (react-query, recharts) -- no infrastructure changes required.

## Key Findings

### Recommended Stack

The existing stack (Python 3.11/Flask 3.0/SQLite/React 19/Vite/Zustand) is kept entirely. No migrations. New additions are minimal and low-risk.

**Core additions:**
- `AsyncOpenAI` / `ThreadPoolExecutor`: Concurrent LLM image analysis -- directly fixes the documented P0 performance bottleneck. Zero new dependencies (uses existing openai SDK + stdlib)
- `threading.Lock` for `_evaluation_store`: Fixes correctness bug in shared mutable state. Stdlib only
- `bcrypt`: Replace plaintext password storage. Security table stakes
- `@tanstack/react-query v5`: Async polling for Evaluate task completion, cache invalidation. Required for Evaluate frontend
- `recharts v2`: Multi-dimensional score visualization (radar charts, bar comparisons). Lightweight, SVG-based, React-native

**Explicitly rejected:** Celery/Redis (overkill), PostgreSQL (unnecessary migration), LangChain (abstraction without benefit), FastAPI (migration cost exceeds benefit), LiteLLM (single provider), DeepEval/RAGAS (wrong problem domain).

### Expected Features

**Must have (table stakes):**
- Side-by-side campaign comparison UI -- the entire purpose of the tool
- Multi-dimensional scoring with composite score -- already implemented, needs UI polish
- Visual creative analysis -- already implemented via ImageAnalyzer + LLM vision
- Category-specific evaluation personas -- transparent vs. colored lenses have completely different buyer profiles
- Results in under 5 minutes -- current serial pipeline is too slow
- Evaluate path frontend -- backend exists, no UI
- Historical baseline comparison -- BaselineRanker exists, needs prominent display

**Should have (differentiators):**
- AI synthetic audience panel (already built, deepen persona accuracy)
- Dual-path simulation (Race + Evaluate, already built as backends)
- Actionable visual diagnostics ("why it scored low, how to fix")
- Exportable results (PDF/image for meetings)
- Customizable audience personas (after preset system stabilizes)

**Defer (v2+):**
- Trend dashboard (needs data accumulation)
- BrandStateEngine refactoring (works today, risky to touch)
- Video/GIF analysis, AI creative generation, eye tracking -- anti-features

### Architecture Approach

The system is a Flask monolith with two coexisting execution models: Race (synchronous, 5-30s) and Evaluate (async daemon thread, 2-10min). The target architecture adds a unified entry point in the React SPA that lets users choose Race, Evaluate, or Both modes from a single plan builder. A new `PersonaRegistry` service decouples persona configuration from code. `ImageAnalyzer` switches from serial to concurrent execution via `ThreadPoolExecutor`. The `EvaluatePage` frontend component handles async task polling.

**Major components:**
1. `PersonaRegistry` (NEW) -- Maps category to persona list; replaces hardcoded persona arrays
2. `EvaluatePage` (NEW) -- Frontend for async Evaluate path with progress polling and jury result display
3. `ImageAnalyzer` (MODIFIED) -- Concurrent image analysis via ThreadPoolExecutor, max 3 workers
4. `EvaluationOrchestrator` (MODIFIED) -- Fixed image path resolution, accepts injected persona config
5. `_evaluation_store` (MODIFIED) -- Thread-safe with Lock + LRU eviction (max 100 entries)

### Critical Pitfalls

1. **Silent image dropout** -- `AudiencePanel` and `PairwiseJudge` call `os.path.exists()` on API URL strings, silently skipping all images. Every Evaluate result is computed without visual context. Fix: centralized `resolve_image_path()` utility used by all services
2. **LLM judge position bias** -- Single-model judge + Bradley-Terry amplifies systematic bias into confident-looking rankings. Fix: randomize A/B presentation order, run each pair twice with swapped positions, flag inconsistent judgments
3. **Concurrent state corruption** -- `_evaluation_store` dict has no thread safety, SQLite has no WAL mode. Multi-user access will produce partial results and database locks. Fix: `threading.Lock` + `PRAGMA journal_mode=WAL` + `busy_timeout`
4. **Base64 image token overflow** -- High-res images (3-5MB) become 4-7MB base64, hitting LLM token limits silently. Fix: resize to max 1024px before encoding, validate payload size
5. **Persona config without validation** -- Free-text persona prompts can produce garbage evaluations that BT treats as valid. Fix: curated presets first, schema validation for any custom personas

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation Fixes (Bug Fix + Stability + Security)
**Rationale:** Every downstream feature depends on correct image handling and safe concurrent access. Building UI on a broken image pipeline means users see confidently wrong scores. This phase has zero feature value but prevents all subsequent work from being wasted.
**Delivers:** Working image path resolution across all services, thread-safe evaluation store, SQLite WAL mode, bcrypt password hashing, image resize preprocessing, SECRET_KEY enforcement
**Addresses:** Fix Evaluate image bug (P1), concurrent access safety, security basics
**Avoids:** Silent image dropout (Pitfall 1), concurrent state corruption (Pitfall 4), base64 token overflow (Pitfall 6)
**Stack:** `threading.Lock` (stdlib), `bcrypt`, SQLite WAL pragma, image resize via Pillow (already installed)
**Effort:** 2-3 days

### Phase 2: Persona Configuration + Evaluate Pipeline Enhancement
**Rationale:** Category-based personas must exist before the Evaluate frontend can offer category selection. Position-swap debiasing should ship with the first usable Evaluate experience.
**Delivers:** `PersonaRegistry` service, JSON persona config for moodyPlus and colored_lenses categories, `AudiencePanel` refactored to accept injected personas, position-swap in `PairwiseJudge`
**Addresses:** Category-specific evaluation (P1 feature), LLM judge bias mitigation
**Avoids:** Persona config without validation (Pitfall 5), judge bias (Pitfall 2)
**Stack:** No new dependencies. JSON config file + service class
**Effort:** 2-3 days

### Phase 3: Concurrent Image Analysis
**Rationale:** Independent of UI work, can be built and tested in isolation. Directly fixes the documented performance bottleneck. Should land before the Evaluate frontend so users experience fast evaluations from day one.
**Delivers:** `ThreadPoolExecutor` in `ImageAnalyzer` (max 3 workers), rate-limit-aware semaphore for LLM calls, per-user evaluation concurrency limit
**Addresses:** Evaluation speed < 5 minutes (P1 feature)
**Avoids:** Serial image analysis performance trap
**Stack:** `AsyncOpenAI` or `ThreadPoolExecutor` (stdlib), semaphore for rate limiting
**Effort:** 1-2 days

### Phase 4: Evaluate Frontend + Unified Entry
**Rationale:** Largest surface area change. Depends on Phases 1-2 being stable (working images + persona config). The unified entry design prevents the anti-pattern of dual plan builders.
**Delivers:** `EvaluatePage` component with progress polling, mode selector in `HomePage` (Race/Evaluate/Both), unified plan builder, category-based persona preview, `@tanstack/react-query` for async state
**Addresses:** Evaluate frontend (P1), unified entry (P1), side-by-side comparison UI (P1)
**Avoids:** Dual plan builder anti-pattern, missing progress indication UX pitfall
**Stack:** `@tanstack/react-query v5`, `recharts v2`
**Effort:** 4-5 days

### Phase 5: Combined Results + Export
**Rationale:** Only possible after both paths work end-to-end. Cross-references Race (evidence-based) and Evaluate (perception-based) rankings for richer insight.
**Delivers:** Enhanced `ResultPage` showing Race + Evaluate results together, comparison view ("Race ranked A>B, Evaluate ranked B>A -- investigate"), PDF/image export
**Addresses:** Result export (P2), Race+Evaluate cross-reference
**Stack:** `recharts` (already added in Phase 4), PDF generation (html-to-image or similar)
**Effort:** 2-3 days

### Phase Ordering Rationale

- **Phase 1 before everything:** The image dropout bug silently invalidates all Evaluate results. Building UI on broken data is worse than having no UI
- **Phase 2 before Phase 4:** The Evaluate frontend needs persona config to offer category selection. Without it, the UI has nothing to configure
- **Phase 3 parallel with Phase 2:** Concurrent image analysis is an independent backend change with no UI dependency. Can be developed alongside persona work
- **Phase 4 after 1-3:** All backend prerequisites must be stable before investing in frontend. Otherwise the UI ships over broken foundations
- **Phase 5 last:** Combined view requires both paths working, which is only guaranteed after Phase 4

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** LLM judge debiasing strategies need experimentation -- position-swap is well-documented but optimal temperature/prompt variations for ensemble judging are not. Run controlled experiments with known-good campaign pairs
- **Phase 4:** Unified plan builder UX needs design research -- how to present Race vs. Evaluate vs. Both modes without confusing non-technical brand team users. Consider user interview or prototype testing

Phases with standard patterns (skip research-phase):
- **Phase 1:** Bug fixes and thread safety are straightforward engineering with clear solutions documented in PITFALLS.md
- **Phase 3:** ThreadPoolExecutor for concurrent I/O is a well-documented Python pattern. Bailian rate limits need empirical testing but the pattern itself is standard
- **Phase 5:** Result visualization and PDF export are standard frontend patterns

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Existing stack is proven. Additions are conservative (3 backend, 2 frontend packages). All verified against current codebase compatibility |
| Features | MEDIUM | Competitive landscape well-researched (Kantar, Zappi, System1, Behavio). Internal user needs inferred from PROJECT.md and codebase analysis -- no direct user interview data |
| Architecture | HIGH | Based on direct codebase analysis. Component boundaries, data flows, and dependency graphs verified against actual code |
| Pitfalls | HIGH | Critical pitfalls verified with line-number-level codebase evidence. LLM judge bias supported by NAACL 2025 research. Concurrent access issues confirmed by code inspection |

**Overall confidence:** HIGH

### Gaps to Address

- **User validation of feature priorities:** Feature research used competitive analysis and codebase inference, not direct user feedback. Validate with brand/creative team that the priority order matches their actual workflow pain points
- **Bailian API rate limits:** Exact per-minute token/request limits not documented. Need empirical testing to determine safe `max_workers` for concurrent image analysis (assumed 3, may be higher or lower)
- **Evaluate path end-to-end timing:** The 2-10 minute estimate for Evaluate path is from code analysis. Actual timing with concurrent image analysis and 5+ campaigns needs measurement to validate the "<5 minutes" target
- **BrandStateEngine usage in Evaluate path:** It's unclear how much the Evaluate path depends on BrandStateEngine vs. using it only in Race. This affects whether Phase 2-4 changes could accidentally break BrandStateEngine's behavior
- **Persona effectiveness:** No data on whether the current 5 hardcoded personas produce evaluations that correlate with actual campaign performance. Calibration system exists but needs 5+ resolved sets. Bootstrap with historical campaign data if available

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis of `/Users/slr/MiroFishmoody/` -- architecture, bugs, component boundaries
- `.planning/PROJECT.md` -- requirements, constraints, active backlog
- `.planning/codebase/ARCHITECTURE.md` -- current architecture documentation
- `.planning/codebase/CONCERNS.md` -- known issues and tech debt

### Secondary (MEDIUM confidence)
- [Re-evaluating Automatic LLM System Ranking (NAACL 2025)](https://aclanthology.org/2025.findings-naacl.260.pdf) -- BT model bias amplification
- [Justice or Prejudice? Quantifying Biases in LLM-as-a-Judge](https://arxiv.org/html/2410.02736v1) -- judge bias taxonomy
- [Behavio: Ad Testing Software Guide 2026](https://www.behaviolabs.com/blog/ad-testing-software-what-it-is-how-it-works-the-best-platforms-in-2026) -- competitive landscape
- [Langfuse Python SDK v3](https://langfuse.com/docs/observability/get-started) -- LLM observability integration
- [TanStack React Query v5](https://tanstack.com/query/latest) -- async state management

### Tertiary (LOW confidence)
- [Altair Media: Synthetic Audiences 2026](https://altair-media.com/posts/synthetic-audiences-in-market-research-hype-reality-and-outlook-for-2026) -- market direction for AI synthetic audiences (single source)
- Bailian API rate limits -- inferred from general OpenAI-compatible API behavior, not verified against Bailian docs

---
*Research completed: 2026-03-17*
*Ready for roadmap: yes*
