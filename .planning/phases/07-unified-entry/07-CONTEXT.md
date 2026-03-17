# Phase 7: Unified Entry - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Add mode selector to HomePage (Race/Evaluate/Both) and unify the campaign submission form. Both mode launches both pipelines simultaneously. Existing HomePage form fields preserved; mode selector added at top.

</domain>

<decisions>
## Implementation Decisions

### Mode Selector
- Three cards at top of HomePage form: 快速推演 (Race), 深度评审 (Evaluate), 联合推演 (Both)
- Cards show mode name, brief description, estimated time
- Default selection: Race (backward compatible)

### Unified Form
- Single form serves all modes — existing fields preserved
- Category selector (品类) already exists in form — it drives persona loading (Phase 3)
- No mode-specific extra fields needed for v1

### Both Mode Behavior
- Submits to both /api/brandiction/race AND /api/campaign/evaluate simultaneously
- Race navigates to existing RunningPage → ResultPage
- Evaluate navigates to EvaluatePage → EvaluateResultPage
- Both mode: navigate to Race result first (faster), show link to "查看深度评审结果" when Evaluate completes
- Race and Evaluate results are independent — no combined view in this phase (Phase 8)

### Claude's Discretion
- Exact card styling and animation
- How to handle Both mode navigation (split screen vs sequential)
- Form submission logic for dual-submit

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/pages/HomePage.tsx` — existing campaign form with product_line selector
- `frontend/src/lib/api.ts` — raceCampaigns(), evaluateCampaigns() both exist
- `frontend/src/pages/EvaluatePage.tsx` — from Phase 6
- `frontend/src/pages/RunningPage.tsx` — existing Race progress page

### Established Patterns
- Form state via useState in HomePage
- Submission navigates to RunningPage with localStorage state transfer
- Tailwind cards with motion animations

### Integration Points
- `frontend/src/pages/HomePage.tsx` — add mode selector, modify submit handler
- `frontend/src/lib/api.ts` — may need helper for dual submission

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond the decisions above.

</specifics>

<deferred>
## Deferred Ideas

- Combined Race+Evaluate result view (Phase 8)

</deferred>
