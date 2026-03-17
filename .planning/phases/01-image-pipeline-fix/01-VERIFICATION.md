---
phase: 01-image-pipeline-fix
verified: 2026-03-17T05:00:00Z
status: passed
score: 9/9 must-haves verified
gaps: []
---

# Phase 1: Image Pipeline Fix — Verification Report

**Phase Goal:** 所有推演路径的图片处理正确工作，不再静默丢弃图片
**Verified:** 2026-03-17T05:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Evaluate 推演使用上传图片 URL 时，图片被正确解析并送入 LLM，不再静默跳过 | VERIFIED | `resolve_image_path()` called in AudiencePanel (line 180), PairwiseJudge `_build_image_parts` (line 128), ImageAnalyzer `analyze_single_image` (line 88); integration test `test_audience_panel_resolves_api_url` PASSES |
| 2 | 高分辨率图片（>1024px）在 base64 编码前被自动缩放，不触发 LLM token 限制 | VERIFIED | `image_to_base64_part()` uses `img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)` when `max(width, height) > max_dimension`; `test_high_res_image_gets_resized` and `test_large_image_resized` both PASS, assert `max(resized.size) <= 1024` |
| 3 | 使用 `resolve_image_path()` 统一路径解析，AudiencePanel 和 PairwiseJudge 不再直接调用 `os.path.exists()` | VERIFIED | grep confirms zero `os.path.exists` calls in `audience_panel.py` and `pairwise_judge.py`; both import `resolve_image_path` from shared utility |

**Score:** 3/3 success criteria verified

---

### Plan 01 Must-Haves

#### Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `resolve_image_path()` converts API URL to disk path correctly | VERIFIED | Lines 36-64 in `image_helpers.py`; `test_valid_url_existing_file` PASSES |
| 2 | `resolve_image_path()` returns None for non-URL strings and invalid paths | VERIFIED | Empty string, non-prefix path, missing file all return None; 4 tests cover this |
| 3 | `image_to_base64_part()` resizes images exceeding 1024px before encoding | VERIFIED | `thumbnail()` call at line 104; `test_large_image_resized` verifies decoded dimensions == 1024 |
| 4 | `image_to_base64_part()` leaves images <= 1024px untouched | VERIFIED | Raw bytes path at lines 109-111; `test_small_image_not_resized` asserts `img.size == (800, 600)` |

#### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/utils/image_helpers.py` | resolve_image_path + image_to_base64_part | VERIFIED | 120 lines; exports both functions; imports PIL, werkzeug, Config |
| `backend/tests/test_image_helpers.py` | Unit tests, min 60 lines | VERIFIED | 164 lines, 12 test functions across 2 test classes |

#### Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/utils/image_helpers.py` | `backend/app/config.py` | `Config.UPLOAD_FOLDER` | VERIFIED | Line 22: `IMAGES_DIR = os.path.join(Config.UPLOAD_FOLDER, "images")` |

---

### Plan 02 Must-Haves

#### Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | AudiencePanel uses `resolve_image_path()` to convert API URLs before os.path.exists check | VERIFIED | Line 180 in `audience_panel.py`: `resolved = resolve_image_path(img_url)` |
| 2 | PairwiseJudge uses `resolve_image_path()` to convert API URLs before os.path.exists check | VERIFIED | Line 128 in `pairwise_judge.py`: `resolved = resolve_image_path(img_url)` in `_build_image_parts` |
| 3 | Both services use `image_to_base64_part()` from shared utility instead of inline base64 encoding | VERIFIED | Both files call `image_to_base64_part(resolved)`; no inline `base64.b64encode(f.read())` remains |
| 4 | ImageAnalyzer delegates to shared utility instead of private functions | VERIFIED | Private `_resolve_image_url_to_path` and `_image_to_base64_part` removed; `resolve_image_path` / `image_to_base64_part` called at lines 88, 93, 132 |
| 5 | Images with API URL paths are no longer silently skipped | VERIFIED | `test_pairwise_judge_build_image_parts_resolves_url` asserts `len(parts) == 1` for API URL input |

#### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/services/audience_panel.py` | imports from `..utils.image_helpers` | VERIFIED | Line 16: `from ..utils.image_helpers import resolve_image_path, image_to_base64_part` |
| `backend/app/services/pairwise_judge.py` | imports from `..utils.image_helpers` | VERIFIED | Line 17: `from ..utils.image_helpers import resolve_image_path, image_to_base64_part` |
| `backend/app/services/image_analyzer.py` | imports from `..utils.image_helpers` | VERIFIED | Line 18: `from ..utils.image_helpers import resolve_image_path, image_to_base64_part` |
| `backend/tests/test_image_pipeline_integration.py` | Integration tests, min 40 lines | VERIFIED | 91 lines, 5 test functions covering BUG-01 and BUG-02 regressions |

#### Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `audience_panel.py` | `image_helpers.py` | `from ..utils.image_helpers import` | VERIFIED | Line 16 confirmed present |
| `pairwise_judge.py` | `image_helpers.py` | `from ..utils.image_helpers import` | VERIFIED | Line 17 confirmed present |
| `image_analyzer.py` | `image_helpers.py` | `from ..utils.image_helpers import` | VERIFIED | Line 18 confirmed present |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| BUG-01 | 01-01, 01-02 | AudiencePanel 和 PairwiseJudge 使用 `resolve_image_path()` 而非 `os.path.exists()` 检查 URL 字符串 | SATISFIED | Both services import and call `resolve_image_path()`; no `os.path.exists` on image paths; 2 integration regression tests pass |
| BUG-02 | 01-01, 01-02 | 上传图片在 base64 编码前自动缩放至 max 1024px | SATISFIED | `image_to_base64_part()` with `thumbnail((1024,1024), LANCZOS)`; `test_high_res_image_gets_resized` verifies decoded size <= 1024px |

Both v1 requirements for Phase 1 are fully satisfied. No orphaned requirements.

---

## Test Results

| Test Suite | Result | Count |
|------------|--------|-------|
| `tests/test_image_helpers.py` | PASSED | 12/12 |
| `tests/test_image_pipeline_integration.py` | PASSED | 5/5 |
| Full `tests/` suite | PASSED | 557 passed, 10 skipped, 0 failed |

Note: `scripts/test_sync_etl_enrichment.py` fails due to missing `pyarrow` dependency — this is a pre-existing infrastructure issue unrelated to Phase 1 changes.

---

## Anti-Patterns Scan

| File | Pattern | Result |
|------|---------|--------|
| `image_helpers.py` | TODO/placeholder/stub | None found |
| `image_helpers.py` | `return null` / empty impl | Not present; both functions have real logic |
| `audience_panel.py` | Inline `os.path.exists` on image path | Not present |
| `audience_panel.py` | Inline `base64.b64encode(f.read())` | Not present |
| `pairwise_judge.py` | Inline `os.path.exists` on image path | Not present |
| `pairwise_judge.py` | Inline `base64.b64encode(f.read())` | Not present |
| `image_analyzer.py` | Private `_resolve_image_url_to_path` | Removed — confirmed absent |
| `image_analyzer.py` | Private `_image_to_base64_part` | Removed — confirmed absent |

No blockers, no warnings.

---

## Human Verification Required

None. All goal-critical behavior is verifiable programmatically via the test suite.

---

## Summary

Phase 1 goal is fully achieved. All must-haves pass all three verification levels (exists, substantive, wired):

- `backend/app/utils/image_helpers.py` — shared utility exists with real resize logic and security checks
- All three services (AudiencePanel, PairwiseJudge, ImageAnalyzer) import from the shared utility
- No service retains inline `os.path.exists` or `base64.b64encode` for image handling
- 17 unit + integration tests pass, covering URL resolution, path traversal blocking, resize boundary behavior, and end-to-end `_build_image_parts` with API URL input
- Full 557-test backend suite passes with zero regressions

Both BUG-01 (silent image dropout) and BUG-02 (high-res overflow) are fixed and regression-tested.

---

_Verified: 2026-03-17T05:00:00Z_
_Verifier: Claude (gsd-verifier)_
