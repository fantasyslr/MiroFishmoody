# Phase 2: PersonaRegistry Service - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Extract the hardcoded PERSONAS list from audience_panel.py into an independent PersonaRegistry service. The registry loads persona presets from JSON config files with schema validation. AudiencePanel consumes personas from the registry instead of the module-level constant.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase.

Key technical context:
- Current personas are hardcoded as `PERSONAS: List[Dict[str, Any]]` at module level in `backend/app/services/audience_panel.py` (lines 23-78)
- 5 personas exist: daily_wearer, acuvue_switcher, beauty_first, price_conscious, eye_health
- Each persona has: id, name, description, evaluation_focus
- `AudiencePanel.__init__` sets `self.personas = PERSONAS`
- `evaluate_all` iterates `self.personas` for all campaigns
- Phase 3 will add category-based persona loading — registry must be designed to support per-category presets
- Persona JSON files should live in `backend/app/config/personas/` or similar
- Schema validation should enforce required fields: id, name, description, evaluation_focus

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/audience_panel.py` — current persona consumer, PERSONAS constant
- `backend/app/config.py` — Config class pattern for loading settings

### Established Patterns
- Services are in `backend/app/services/`
- Singletons used for stores (BrandictionStore, TaskManager) — but consider whether registry needs singleton
- Config loaded from env vars via `backend/app/config.py`
- JSON data files exist in `backend/uploads/` but config files would be better in `backend/app/config/`

### Integration Points
- `backend/app/services/audience_panel.py` — primary consumer, needs to accept personas from registry
- Phase 3 will extend registry to support category-based lookup

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase.

</specifics>

<deferred>
## Deferred Ideas

- Category-based persona loading (Phase 3)
- Custom persona creation UI (v2)

</deferred>
