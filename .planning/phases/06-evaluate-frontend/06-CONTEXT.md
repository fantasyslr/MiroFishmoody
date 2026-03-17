# Phase 6: Evaluate Frontend - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the Evaluate frontend: EvaluatePage (submit + progress polling) and EvaluateResultPage (persona scores, pairwise matrix, BT ranking). Reuse existing design language from RunningPage/ResultPage.

</domain>

<decisions>
## Implementation Decisions

### Page Structure
- EvaluatePage with step indicator (Panel → Pairwise → Scoring → Summary) + percentage progress bar
- EvaluateResultPage with tab navigation: Overall Ranking / Persona Details / Pairwise Comparison
- 3-second interval polling on task status endpoint (GET /api/campaign/evaluate/status/<task_id>)
- Reuse existing Tailwind components, motion animations, and card patterns from RunningPage/ResultPage

### Data Display
- Persona score cards: avatar icon + name + score + short comment excerpt
- Pairwise comparison: win/loss matrix table showing head-to-head results
- BT ranking: ranked cards + bar chart showing BT scores
- Position swap inconsistency: ⚙️ icon + tooltip showing forward/reverse results

### Claude's Discretion
- Exact React component structure and file organization
- How to fetch and parse the evaluation result JSON
- Animation and loading state details
- Whether to use @tanstack/react-query or plain useState+useEffect for polling

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/pages/RunningPage.tsx` — progress display pattern (can adapt for Evaluate progress)
- `frontend/src/pages/ResultPage.tsx` — result display pattern (card-based, uses motion)
- `frontend/src/lib/api.ts` — API client, fetch helpers, saveRaceState/getRaceState
- `frontend/src/components/` — shared UI components (likely cards, buttons, etc.)
- `frontend/src/store.ts` — Zustand store (useReviewStore)

### Established Patterns
- Hash-based routing via createHashRouter in App.tsx
- Page-level state via useState, cross-page via localStorage
- API calls through lib/api.ts
- Tailwind CSS for all styling
- Chinese for user-facing text

### Integration Points
- `frontend/src/App.tsx` — add routes for /evaluate and /evaluate-result
- `frontend/src/lib/api.ts` — add evaluateCampaigns() and getEvaluationStatus() functions
- Backend: GET /api/campaign/evaluate/status/<task_id> (existing)
- Backend: POST /api/campaign/evaluate (existing)
- Backend: GET /api/campaign/evaluate/result/<set_id> (existing)

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond the decisions above.

</specifics>

<deferred>
## Deferred Ideas

- WebSocket for real-time progress (v2 — polling is sufficient for internal tool)
- Combined Race+Evaluate result view (Phase 8)

</deferred>
