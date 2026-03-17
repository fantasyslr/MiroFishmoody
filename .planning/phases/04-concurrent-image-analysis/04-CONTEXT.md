# Phase 4: Concurrent Image Analysis - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Convert serial image analysis in ImageAnalyzer and race_campaigns to concurrent execution using ThreadPoolExecutor. Add semaphore-based rate limiting to prevent overwhelming the Bailian LLM API. Target: 5 images analyzed in ≤ 5 minutes (vs 15-25 minutes serial).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase.

Key technical context:
- `ImageAnalyzer.analyze_plan_images()` in `backend/app/services/image_analyzer.py` processes images serially in a for-loop
- `race_campaigns()` in `backend/app/api/brandiction.py` (lines 627-643) calls image analysis sequentially per plan
- `AudiencePanel.evaluate_all()` already uses ThreadPoolExecutor for parallelism — can follow same pattern
- LLM calls go through `backend/app/utils/llm_client.py` using OpenAI SDK
- Bailian API rate limits unknown — default to max_workers=3 with semaphore
- Phase 1 already fixed image path resolution — images now correctly flow through the pipeline

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/audience_panel.py` — ThreadPoolExecutor pattern already in use (evaluate_all method)
- `backend/app/utils/image_helpers.py` — shared image utility from Phase 1
- `backend/app/utils/llm_client.py` — LLM client wrapper

### Established Patterns
- ThreadPoolExecutor with `max_workers` in audience_panel.py
- concurrent.futures for parallel LLM calls
- Logger hierarchy: `ranker.services.*`

### Integration Points
- `backend/app/services/image_analyzer.py` — primary target for parallelization
- `backend/app/api/brandiction.py` — race_campaigns handler calls image analysis

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
