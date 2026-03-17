# Phase 3: Category Persona Config - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Add category-based persona presets to PersonaRegistry. Create separate JSON files for moodyPlus (transparent lenses) and colored_lenses (colored contact lenses). PersonaRegistry supports loading by category. API layer accepts category parameter to return appropriate personas.

</domain>

<decisions>
## Implementation Decisions

### Persona Distribution
- **moodyPlus (透明片)**: daily_wearer, acuvue_switcher, eye_health (existing) + 2-3 new transparent-lens-specific personas
- **colored_lenses (彩片)**: beauty_first, price_conscious (existing) + 2-3 new colored-lens-specific personas
- Rationale: daily_wearer/acuvue_switcher/eye_health focus on function and health (transparent lens buyer profile); beauty_first focuses on aesthetics (colored lens buyer profile); price_conscious is common in colored lens segment

### New Personas to Create
- moodyPlus new personas should focus on: office worker daily comfort, sports/active lifestyle, sensitive eyes/dry eyes
- colored_lenses new personas should focus on: makeup/beauty influencer, cosplay/special occasion, natural look enhancer

### File Structure
- `backend/app/config/personas/moodyplus.json` — transparent lens personas
- `backend/app/config/personas/colored_lenses.json` — colored lens personas
- `backend/app/config/personas/default.json` — kept as fallback (existing 5 personas)

### API Integration
- Evaluate and Race API endpoints should accept `category` parameter
- If category provided → load category-specific personas
- If no category → fall back to default.json (backward compatible)

### Claude's Discretion
- Exact new persona descriptions and evaluation_focus content
- PersonaRegistry API design for category-based lookup
- How category parameter flows through API → service layer

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/persona_registry.py` — PersonaRegistry created in Phase 2, loads from JSON
- `backend/app/config/personas/default.json` — existing 5 personas
- `backend/app/services/audience_panel.py` — consumes PersonaRegistry via DI

### Established Patterns
- PersonaRegistry loads JSON from `backend/app/config/personas/`
- Schema validation enforces required fields: id, name, description, evaluation_focus
- AudiencePanel accepts PersonaRegistry in constructor

### Integration Points
- `backend/app/services/persona_registry.py` — needs `get_personas(category=None)` method
- `backend/app/api/brandiction.py` — race endpoint, needs category parameter
- `backend/app/api/campaign.py` — evaluate endpoint, needs category parameter
- `backend/app/services/evaluation_orchestrator.py` — may need to pass category through

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond the distribution decision above.

</specifics>

<deferred>
## Deferred Ideas

- Custom persona creation by users (v2 — ITER-02)
- Cross-category personas for comparison campaigns

</deferred>
