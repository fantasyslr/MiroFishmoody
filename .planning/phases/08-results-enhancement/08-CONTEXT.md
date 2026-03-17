# Phase 8: Results Enhancement - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Enhance the Race ResultPage and Evaluate EvaluateResultPage with: side-by-side campaign comparison, radar chart multi-dimensional scoring, historical baseline percentile display, and structured visual diagnostic recommendations from Phase 5.

</domain>

<decisions>
## Implementation Decisions

### Side-by-Side Comparison
- Card grid layout: each campaign as a card with thumbnail images + score summary
- Cards show: campaign name, primary KV thumbnail, overall score, top 3 dimension scores
- Responsive: 2 cards per row on desktop, 1 on mobile

### Multi-Dimensional Visualization
- Use recharts RadarChart for dimension comparison across campaigns
- Dimensions: visual appeal, brand fit, audience resonance, etc. (from existing scoring)
- Overlay multiple campaigns on same radar chart for direct comparison

### Historical Baseline
- Progress bar showing percentile position within historical data
- Text label: "超过 {N}% 的历史 campaign"
- Data source: BaselineRanker already computes percentile in race results

### Visual Diagnostics Display (QUAL-03)
- Collapsible cards per campaign showing structured diagnostics from Phase 5
- Each issue: severity badge (high/medium/low) + description
- Each recommendation: action text + priority indicator
- Collapsed by default, expand to see details

### Claude's Discretion
- Exact recharts configuration and styling
- How to install recharts (npm install)
- Card layout grid details
- Animation for expand/collapse

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/pages/ResultPage.tsx` — existing Race result page to enhance
- `frontend/src/pages/EvaluateResultPage.tsx` — from Phase 6, can also add comparison view
- `frontend/src/lib/api.ts` — result data access helpers
- Phase 5 structured diagnostics in ImageAnalyzer output

### Established Patterns
- Tailwind card components
- motion animations for transitions
- Tab navigation pattern from EvaluateResultPage

### Integration Points
- `frontend/src/pages/ResultPage.tsx` — add comparison grid, radar chart, baseline display
- `frontend/src/pages/EvaluateResultPage.tsx` — add diagnostics tab or section
- `package.json` — add recharts dependency

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond the decisions above.

</specifics>

<deferred>
## Deferred Ideas

- PDF export of enhanced results (v2 — EXP-01)
- Combined Race+Evaluate cross-reference view (v2 — ANAL-02)

</deferred>
