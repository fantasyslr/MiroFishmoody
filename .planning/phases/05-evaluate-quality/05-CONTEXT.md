# Phase 5: Evaluate Quality - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Two backend quality improvements: (1) PairwiseJudge position-swap debiasing — each campaign pair evaluated twice with A/B order swapped, flagging inconsistent judgments; (2) ImageAnalyzer structured diagnostics — output changed from free-text paragraphs to structured JSON "issue → recommendation" format.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase.

Key technical context:
- `PairwiseJudge` in `backend/app/services/pairwise_judge.py` does 3-judge majority vote for each pair
- Each pair is evaluated once with fixed A/B order — position bias documented in research
- Fix: evaluate each pair twice (A vs B, then B vs A), flag if results disagree
- `ImageAnalyzer` in `backend/app/services/image_analyzer.py` returns free-text analysis
- Fix: change LLM prompt to request structured JSON with issues[] and recommendations[]
- VisualProfile model in `backend/app/models/` may need new fields for structured diagnostics

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/pairwise_judge.py` — 3-judge concurrent pattern with ThreadPoolExecutor
- `backend/app/services/image_analyzer.py` — LLM vision analysis, already uses json response_format
- `backend/app/utils/llm_client.py` — `chat_multimodal_json` method for structured output

### Established Patterns
- Pairwise combinations generated with `itertools.combinations`
- ThreadPoolExecutor for parallel judge calls
- LLM structured output via `response_format: {"type": "json_object"}`

### Integration Points
- `backend/app/services/pairwise_judge.py` — position swap logic
- `backend/app/services/image_analyzer.py` — structured output format
- `backend/app/models/` — VisualProfile or new diagnostic model
- Phase 8 will display diagnostics in frontend — output format must be frontend-friendly

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase.

</specifics>

<deferred>
## Deferred Ideas

- Judge ensemble temperature experimentation (research suggested but not required for v1)

</deferred>
