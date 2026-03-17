# Phase 1: Image Pipeline Fix - Context

**Gathered:** 2026-03-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the silent image dropout bug in Evaluate path and add automatic image resize before base64 encoding. This phase delivers correct image handling across all evaluation services — no new features, pure pipeline correctness.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — pure infrastructure phase.

Key technical context:
- `AudiencePanel` (audience_panel.py:181) and `PairwiseJudge` (pairwise_judge.py:129) use `os.path.exists()` on API URL strings — always returns False, silently skipping images
- `ImageAnalyzer` has `_resolve_image_url_to_path()` that correctly converts API URLs to disk paths — this logic should be centralized and reused
- Images are stored at `backend/uploads/images/<set_id>/` and served via `GET /api/campaign/image-file/<set_id>/<filename>`
- Pillow is already installed for image processing
- Max resize target: 1024px (already used in upload handler)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ImageAnalyzer._resolve_image_url_to_path()` in `backend/app/services/image_analyzer.py` — already handles URL-to-path conversion
- `Pillow` (already in dependencies) — image resize capability
- Upload handler in `backend/app/api/campaign.py` already resizes to max 1024px on upload

### Established Patterns
- Services import utilities from `backend/app/utils/`
- Image paths stored as API URLs in campaign objects (e.g., `/api/campaign/image-file/...`)
- LLM vision calls use base64 encoding via `LLMClient.chat_multimodal()`

### Integration Points
- `backend/app/services/audience_panel.py` — needs `resolve_image_path()` integration
- `backend/app/services/pairwise_judge.py` — needs `resolve_image_path()` integration
- `backend/app/services/image_analyzer.py` — source of existing resolution logic

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
