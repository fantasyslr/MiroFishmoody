# Phase 13: Critical Bug Fixes + API Contract Lock - Research

**Researched:** 2026-03-18
**Domain:** Flask API contract repair, TypeScript API surface lock, React polling, Python image path resolution
**Confidence:** HIGH — all findings from direct codebase inspection, zero speculation

## Summary

Phase 13 addresses four concrete defects that are directly verifiable in the current codebase. All bugs are mechanically clear — no architectural decisions are required, only targeted surgical fixes and one new file (`contracts.ts`). The phase requires no new dependencies.

BUG-05 is more severe than the REQUIREMENTS.md description implies: it is not merely an `os.path.exists()` call issue in isolation. The `resolve_image_path()` utility already exists and is correctly implemented in `backend/app/utils/image_helpers.py`, and both `AudiencePanel` and `PairwiseJudge` already import and call it correctly. The actual root cause of "视觉评估为盲评" is an **EvaluatePayload field mismatch**: the frontend sends `campaign_id` (not `id`) and `description` (not `core_message`), but the backend's `_parse_campaigns()` requires `id` (fallback `campaign_{i+1}`) and `core_message` (required non-empty). This means the `/api/campaign/evaluate` endpoint currently returns `400 {"error": "方案 1: core_message 不能为空"}` for any evaluate submission from the current frontend — making Evaluate mode non-functional, not merely blind. This is the critical fix.

BUG-06 (Both mode race condition) is confirmed: `evaluateCampaigns()` is fired without `await` before `navigate('/running')`, so `evaluateTaskId` may not be persisted if the POST resolves after page navigation. BUG-07 (RunningPage fake animation) is confirmed: `RunningPage.tsx` uses a `setInterval` step ticker with no backend signal — meanwhile `EvaluatePage.tsx` already has correct real polling logic that can serve as a direct reference. FE-08 (`contracts.ts`) needs to be created from scratch, mirroring every Flask API endpoint's exact shape.

**Primary recommendation:** Fix BUG-05 first (field mapping in `_parse_campaigns` or a dedicated evaluate parser) before any other work — without it, Evaluate mode returns 400 and Phase 13 success criteria cannot be tested.

## Standard Stack

### Core (no new dependencies needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| TypeScript | 5.9 (current) | `contracts.ts` type definitions | Already installed; `npm run build` is the validation gate |
| React `useEffect` + `setInterval` | React 19 (current) | Real polling in RunningPage | `EvaluatePage.tsx` already has working polling pattern — reuse exactly |
| Python `os.path` | stdlib | Path resolution in image_helpers.py | Already implemented correctly |
| Flask `jsonify` | 3.0 (current) | API response shaping | No changes to Flask routing needed |

### No Additions Required

This phase adds zero new npm packages and zero new Python packages. All fixes are modifications to existing files.

**Verification commands:**
```bash
# Frontend build gate (run after every change)
npm run build

# Backend test suite
cd /Users/slr/MiroFishmoody && uv run --project backend pytest backend/ -q --no-header
# Baseline: 601 passed, 1 known-fail (pyarrow/parquet unrelated), 10 skipped
```

## Architecture Patterns

### Recommended File Structure Changes

```
backend/app/api/
  campaign.py              # Add _parse_evaluate_campaigns() alongside _parse_campaigns()

frontend/src/lib/
  api.ts                   # FROZEN - do not touch
  contracts.ts             # NEW: mirror all Flask endpoints' exact request/response types

frontend/src/pages/
  HomePage.tsx             # Fix: await Promise.all([raceCampaigns, evaluateCampaigns]) in Both mode
  RunningPage.tsx          # Fix: replace fake step ticker with real TaskManager polling (copy from EvaluatePage)
```

### Pattern 1: Separate evaluate parser (BUG-05 fix)

**What:** `_parse_campaigns()` is designed for the `/race` endpoint where campaigns have `core_message`, `target_audience`, etc. The `/evaluate` endpoint receives a different shape (`campaign_id`, `name`, `description`, `image_paths`). The fix is a dedicated `_parse_evaluate_campaigns()` that maps the evaluate shape to Campaign objects.

**When to use:** `/api/campaign/evaluate` endpoint only.

**Current broken code:**
```python
# campaign.py line 301 — this causes 400 for all evaluate submissions
campaign_set = _parse_campaigns(data)  # expects core_message, gets description
```

**Fix pattern:**
```python
def _parse_evaluate_campaigns(data: dict) -> CampaignSet:
    """Parse EvaluatePayload shape: {campaign_id, name, description, image_paths}"""
    campaigns_raw = data.get("campaigns", [])
    if not campaigns_raw or len(campaigns_raw) < 2:
        raise ValueError("至少需要 2 个 campaign 方案")
    if len(campaigns_raw) > Config.MAX_CAMPAIGNS:
        raise ValueError(f"最多支持 {Config.MAX_CAMPAIGNS} 个方案")

    campaigns = []
    seen_ids = set()
    for i, c in enumerate(campaigns_raw):
        # Frontend sends campaign_id, not id
        campaign_id = c.get("campaign_id") or c.get("id") or f"campaign_{i+1}"
        if campaign_id in seen_ids:
            raise ValueError(f"方案 {i+1}: campaign_id '{campaign_id}' 重复")
        seen_ids.add(campaign_id)

        name = c.get("name", "").strip()
        if not name:
            raise ValueError(f"方案 {i+1}: name 不能为空")

        # description maps to core_message for LLM evaluation context
        core_message = c.get("description") or c.get("core_message") or name
        product_line_str = c.get("product_line", "colored_lenses")
        try:
            product_line = ProductLine(product_line_str)
        except ValueError:
            product_line = ProductLine.COLORED  # safe default for evaluate path

        campaigns.append(Campaign(
            id=campaign_id,
            name=name,
            product_line=product_line,
            target_audience=c.get("target_audience", ""),
            core_message=core_message,
            channels=c.get("channels", []),
            creative_direction=c.get("creative_direction", ""),
            image_paths=c.get("image_paths", []),  # CRITICAL: this is what enables visual eval
            extra=c.get("extra", {}),
        ))

    set_id = data.get("set_id", str(uuid.uuid4()))
    return CampaignSet(set_id=set_id, campaigns=campaigns)
```

Replace the call in `evaluate()`:
```python
# line 301: was campaign_set = _parse_campaigns(data)
campaign_set = _parse_evaluate_campaigns(data)
```

### Pattern 2: Both mode Promise.all fix (BUG-06)

**What:** Both Race and Evaluate POSTs must complete before navigating, so `evaluateTaskId` is always persisted.

**Current broken code:**
```typescript
// HomePage.tsx lines 302-311
evaluateCampaigns(evalPayload)           // NOT awaited — race condition
  .then((res) => {
    saveEvaluateState(...)
    saveBothModeState(...)               // may not run before navigate
  })
  .catch(() => {})

navigate('/running')                     // fires immediately
```

**Fix pattern:**
```typescript
setSubmitting(true)
try {
  const [_, evalRes] = await Promise.all([
    Promise.resolve(),                   // race payload already saved above
    evaluateCampaigns(evalPayload),
  ])
  saveEvaluateState({ taskId: evalRes.task_id, setId: evalSetId, payload: evalPayload })
  saveBothModeState({ evaluateTaskId: evalRes.task_id, evaluateSetId: evalSetId })
  navigate('/running')
} catch {
  // Evaluate POST failed — still navigate for Race, but don't save evaluate state
  navigate('/running')
} finally {
  setSubmitting(false)
}
```

Or simpler:
```typescript
setSubmitting(true)
let evalTaskId: string | null = null
try {
  const res = await evaluateCampaigns(evalPayload)
  evalTaskId = res.task_id
  saveEvaluateState({ taskId: res.task_id, setId: evalSetId, payload: evalPayload })
  saveBothModeState({ evaluateTaskId: res.task_id, evaluateSetId: evalSetId })
} catch {
  // silent — Race path still works
} finally {
  setSubmitting(false)
  navigate('/running')
}
```

### Pattern 3: RunningPage real polling (BUG-07)

**What:** Replace the fake step-ticker in `RunningPage.tsx` with real `TaskManager` polling. `EvaluatePage.tsx` has the exact working pattern.

**Current broken code in RunningPage.tsx:**
```typescript
// lines 33-46: fake ticker, no backend signal
const interval = setInterval(() => {
  setCurrentStep(s => (s < STEPS.length - 1 ? s + 1 : s))
}, 2500)
raceCampaigns(state.payload).then(result => { ... })
```

**Important distinction:** RunningPage handles the `/race` endpoint, which is **synchronous** (returns full result directly, not task_id). The Race path does not use TaskManager — `raceCampaigns()` returns the full `RaceResult` when done. There is no `task_id` to poll for Race.

**Correct fix for BUG-07:** RunningPage's issue is the fake progress animation, not the absence of polling. Since Race is synchronous, the fix is:
- Show a spinner/progress indicator that reflects the actual wait (no fake steps)
- Keep the real `raceCampaigns()` call
- On resolve: save result and navigate
- On reject: show error

The fake STEPS ticker is misleading (shows fake milestones) but the underlying API call is correct. The fix is UI-only: replace the step list with an honest loading indicator.

**Success criteria verification for BUG-07:** "RunningPage 显示的进度百分比与后端 TaskManager 实际返回的 progress 字段一致" — this applies to the Evaluate path (`EvaluatePage.tsx`), which already does real polling. The Race path (`RunningPage.tsx`) has no progress field because it's synchronous. The fix for RunningPage is to remove the misleading fake steps.

### Pattern 4: contracts.ts structure (FE-08)

**What:** A TypeScript file that re-exports or re-declares every Flask endpoint's exact request/response shape. This acts as a compile-time safety net during Phase 14 rewrite.

**Location:** `frontend/src/lib/contracts.ts`

**Current endpoint inventory (from codebase inspection):**

| Endpoint | Method | Request Body | Response |
|----------|--------|--------------|----------|
| `/api/auth/login` | POST | `{username, password}` | `AuthUser` |
| `/api/auth/logout` | POST | — | `{status: string}` |
| `/api/auth/me` | GET | — | `AuthUser` |
| `/api/brandiction/race` | POST | `RacePayload` | `RaceResult` |
| `/api/brandiction/stats` | GET | — | `Record<string, unknown>` |
| `/api/brandiction/race-history` | GET | — | `{runs: RaceHistoryRun[]}` |
| `/api/campaign/upload-image` | POST | FormData | `UploadImageResponse` |
| `/api/campaign/image-file/<set_id>/<filename>` | GET | — | binary |
| `/api/campaign/images/<set_id>` | GET | — | `{images: ImageEntry[]}` |
| `/api/campaign/evaluate` | POST | `EvaluatePayload` | `{task_id, set_id, campaign_count, message}` |
| `/api/campaign/evaluate/status/<task_id>` | GET | — | `TaskStatusResponse` |
| `/api/campaign/result/<set_id>` | GET | — | `EvaluateResult` |
| `/api/campaign/version-history/<set_id>` | GET | — | `{versions: VersionInfo[]}` |
| `/api/campaign/compare` | GET | `?v1=&v2=` | `VersionCompareResult` |
| `/api/campaign/trends` | GET | `?category=` | `TrendsResponse` |
| `/api/campaign/resolve` | POST | resolution payload | resolution response |
| `/api/campaign/parse-brief` | POST | `{brief_text, product_line}` | parsed Campaign fields |

**contracts.ts pattern:**
```typescript
// frontend/src/lib/contracts.ts
// API Contract Lock — frozen 2026-03-18
// DO NOT change these types without updating the corresponding Flask endpoint.
// Source of truth: backend/app/api/

import type {
  AuthUser,
  RacePayload, RaceResult,
  EvaluatePayload, TaskStatusResponse, EvaluateResult,
  UploadImageResponse, VersionInfo, VersionCompareResult,
  TrendsResponse,
} from './api'

// Re-export from api.ts to create a stable named surface
// All page components import from contracts.ts, not api.ts directly
export type {
  AuthUser,
  RacePayload, RaceResult,
  EvaluatePayload, TaskStatusResponse, EvaluateResult,
  UploadImageResponse, VersionInfo, VersionCompareResult,
  TrendsResponse,
}

// Endpoint-literal types not yet in api.ts
export type EvaluateSubmitResponse = {
  task_id: string
  set_id: string
  campaign_count: number
  message: string
}

export type ImageFileEntry = {
  filename: string
  url: string
}

export type ListImagesResponse = {
  images: ImageFileEntry[]
}
```

### Anti-Patterns to Avoid

- **Touching `lib/api.ts`:** `api.ts` is frozen per v2.0 roadmap decision. `contracts.ts` re-exports from `api.ts` — it does not replace it.
- **Adding polling to RunningPage for Race:** Race is synchronous — there is no `task_id` to poll. Only the Evaluate path uses TaskManager.
- **Changing `_parse_campaigns()`:** The existing function is used by other internal paths. Add a new `_parse_evaluate_campaigns()` instead.
- **Adding new Flask routes:** No new endpoints are needed in Phase 13.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TypeScript API type validation at runtime | Custom validation middleware | Compile-time types in `contracts.ts` + `npm run build` | Runtime validation adds complexity; TypeScript compile-time check is sufficient for this internal tool |
| Progress animation while Race runs | Custom websocket / SSE | Simple spinner + honest "this takes ~15s" copy | Race is synchronous, no streaming protocol needed |
| Retry logic for Both mode evaluate POST | Custom retry wrapper | `Promise.all` with single attempt | Both mode navigate should be fast; retry adds complexity without value |

**Key insight:** All four bugs are fixable with < 50 lines of code each. No architectural changes needed.

## Common Pitfalls

### Pitfall 1: Confusing RunningPage (Race) with EvaluatePage (Evaluate)

**What goes wrong:** Developer reads "RunningPage 显示的进度百分比与后端 TaskManager 实际返回的 progress 字段一致" and adds polling to `RunningPage.tsx` that calls `getEvaluateStatus()`.
**Why it happens:** BUG-07 description sounds like it needs backend polling. But Race is synchronous — there is no `task_id` for RunningPage to poll.
**How to avoid:** RunningPage handles `/race` (synchronous). EvaluatePage handles `/evaluate` (async, has task_id). They are different pages for different paths. EvaluatePage already has correct real polling. The fix for RunningPage is UI-only: remove fake steps.
**Warning signs:** If you find yourself importing `getEvaluateStatus` into RunningPage, stop — that's EvaluatePage's job.

### Pitfall 2: Modifying `lib/api.ts` while creating `contracts.ts`

**What goes wrong:** Developer adds new types to `api.ts` instead of `contracts.ts`.
**Why it happens:** `api.ts` is the natural place for API types.
**How to avoid:** `api.ts` is frozen by roadmap decision (see STATE.md: "lib/api.ts MUST NOT change during frontend rewrite — contracts.ts is the safety layer"). All new types go in `contracts.ts`.
**Warning signs:** Any edit to `frontend/src/lib/api.ts` in Phase 13.

### Pitfall 3: EvaluatePayload `campaign_id` field ignored silently

**What goes wrong:** Developer fixes `_parse_evaluate_campaigns()` to use `core_message` fallback but forgets that `campaign_id` vs `id` mismatch means image URLs stored with campaign UUID prefix won't match the Campaign ID used by AudiencePanel/PairwiseJudge.
**Why it happens:** `_build_campaign_image_map()` in `campaign.py` parses filenames by splitting on `__` to get `campaign_id` prefix — the prefix is the UUID from frontend. But if the Campaign object is created with `id = "campaign_1"`, the `image_paths` in the Campaign object will still have the correct `/api/campaign/image-file/{set_id}/{campaign_uuid}__{uid}__{name}` URLs because they were passed in `image_paths` from the frontend payload directly.
**How to avoid:** In `_parse_evaluate_campaigns()`, use `c.get("campaign_id")` as the Campaign `id` — this must match the UUID prefix used when uploading images. Do not fall back to `campaign_{i+1}` for evaluate path.
**Warning signs:** Image URLs in `campaign.image_paths` don't match the `campaign_id` prefix in filenames.

### Pitfall 4: Both mode navigation before Promise resolves

**What goes wrong:** Fix uses `Promise.all` but still has `navigate()` outside the `.then()` chain.
**Why it happens:** Copy-paste from existing code that navigates unconditionally.
**How to avoid:** `navigate('/running')` must be inside the `try` block after `await Promise.all(...)`, or in a `finally` block that only runs after the promise settles.
**Warning signs:** `evaluateTaskId` missing from store on first page load of ResultPage after Both mode submission.

### Pitfall 5: `contracts.ts` diverges from `api.ts` types immediately

**What goes wrong:** Developer re-declares types in `contracts.ts` instead of re-exporting from `api.ts`, then the two diverge.
**Why it happens:** Seems cleaner to have standalone types.
**How to avoid:** `contracts.ts` should `import type { ... } from './api'` and `export type { ... }` the same identifiers. Only add types for things not yet in `api.ts`. This way `api.ts` remains the single source of truth.

## Code Examples

### Confirmed working polling pattern (from EvaluatePage.tsx)

```typescript
// Source: frontend/src/pages/EvaluatePage.tsx lines 42-68
const interval = setInterval(async () => {
  try {
    const res = await getEvaluateStatus(taskId)
    setProgress(res.progress)
    setMessage(res.message)
    setStatus(res.status)

    if (res.status === 'completed') {
      clearInterval(interval)
      try {
        const result = await getEvaluateResult(setId)
        saveEvaluateState({ ...state, result })
        navigate('/evaluate-result')
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取评审结果失败')
      }
    } else if (res.status === 'failed') {
      clearInterval(interval)
      setError(res.error || '评审任务失败')
    }
  } catch (err) {
    clearInterval(interval)
    setError(err instanceof Error ? err.message : '轮询状态失败，请检查网络连接')
  }
}, 3000)
```

### Current image_helpers.py (already correct, no changes needed)

```python
# Source: backend/app/utils/image_helpers.py lines 25-64
def resolve_image_path(image_url: str) -> Optional[str]:
    prefix = "/api/campaign/image-file/"
    if not image_url.startswith(prefix):
        return None
    # ... sanitize set_id and filename, realpath containment check ...
    if os.path.isfile(real_path):
        return real_path
    return None
```

### TaskStatusResponse shape (what RunningPage should display honestly)

```typescript
// Source: frontend/src/lib/api.ts lines 266-284
export type TaskStatusResponse = {
  task_id: string
  task_type: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number         // 0-100 integer from TaskManager
  message: string          // human-readable stage name
  progress_detail: Record<string, unknown>
  result: { ... } | null
  error: string | null
  metadata: Record<string, unknown>
}
```

### EvaluationOrchestrator progress milestones (source for honest RunningPage for evaluate path)

```python
# Source: backend/app/services/evaluation_orchestrator.py
# progress=5   — init
# progress=10  — Panel starting
# progress=40  — Panel complete
# progress=42  — Image analysis starting
# progress=80  — Pairwise complete
# progress=90  — Scoring complete
# progress=95  — Summary generating
# progress=100 — Complete (via complete_task)
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Evaluate used `_parse_campaigns()` shared with Race | Needs `_parse_evaluate_campaigns()` that accepts `{campaign_id, name, description, image_paths}` | Evaluate currently returns 400 for all submissions |
| RunningPage shows fake step ticker | Should show honest spinner + actual wait time copy | Misleads users about pipeline state |
| Both mode fires evaluate POST without await | `Promise.all` before navigate | evaluateTaskId lost on fast server responses |
| No `contracts.ts` | `contracts.ts` re-exporting from `api.ts` | TypeScript build catches any phase-14 drift |

**Confirmed working (no changes needed):**
- `backend/app/utils/image_helpers.py` — `resolve_image_path()` is correct
- `backend/app/services/audience_panel.py` — already calls `resolve_image_path()`
- `backend/app/services/pairwise_judge.py` — already calls `resolve_image_path()`
- `frontend/src/pages/EvaluatePage.tsx` — already has correct real polling
- `backend/app/models/task.py` — TaskManager with SQLite WAL, correct progress fields

## Open Questions

1. **Does `EvaluatePage.tsx` need RunningPage behavior or vice versa?**
   - What we know: RunningPage (`/running`) is the Race path (synchronous). EvaluatePage (`/evaluate`) is the Evaluate path (async polling). They are separate routes.
   - What's unclear: BUG-07 says "RunningPage 显示的进度百分比与后端 TaskManager 实际返回的 progress 字段一致". If Race has no progress field, the success criterion needs interpretation.
   - Recommendation: Interpret BUG-07 as "replace fake step animation with honest loading indicator" for RunningPage (Race path). The "progress 与 TaskManager 一致" criterion applies to the Evaluate path, which EvaluatePage already satisfies.

2. **Should Both mode show a combined progress UI?**
   - What we know: Currently Both mode navigates to `/running` (Race path). The Evaluate task runs in background and redirects to `/evaluate-result` separately (not currently wired).
   - What's unclear: Whether BUG-06 success criterion requires a UI showing both tasks, or just that both taskIds are persisted.
   - Recommendation: Scope to "both taskIds in store before navigate" — no new combined UI needed in Phase 13 (that's Phase 14 FE work).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (Python) + TypeScript compiler |
| Config file | `backend/pytest.ini` or `pyproject.toml` |
| Quick run command | `uv run --project backend pytest backend/ -q --no-header -k "not parquet"` |
| Full suite command | `uv run --project backend pytest backend/ -q --no-header` |
| Frontend validation | `npm run build` (TypeScript strict compile) |

Baseline: 601 passed, 1 known-fail (parquet/pyarrow dependency unrelated to Phase 13), 10 skipped.

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BUG-05 | `_parse_evaluate_campaigns()` preserves `image_paths` from `campaign_id` field | unit | `uv run --project backend pytest backend/tests/ -k "evaluate_campaigns" -x` | ❌ Wave 0 |
| BUG-05 | Evaluate endpoint returns 200 with valid `{campaign_id, name, description, image_paths}` payload | integration | `uv run --project backend pytest backend/tests/ -k "test_evaluate_endpoint" -x` | ❌ Wave 0 |
| BUG-06 | Both mode saves evaluateTaskId to localStorage before navigate (manual check via dev tools) | manual | N/A | N/A |
| BUG-07 | RunningPage renders without fake step text (no STEPS array) | manual-visual | N/A | N/A |
| FE-08 | `contracts.ts` exists and `npm run build` passes | compile | `npm run build` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `npm run build` (< 5s) + `uv run --project backend pytest backend/tests/ -k "evaluate" -x` (< 10s)
- **Per wave merge:** `uv run --project backend pytest backend/ -q --no-header`
- **Phase gate:** `npm run build` green + full pytest suite green (excluding known parquet failure)

### Wave 0 Gaps

- [ ] `backend/tests/test_phase13_evaluate_parser.py` — covers BUG-05: test `_parse_evaluate_campaigns()` with `{campaign_id, name, description, image_paths}` input; assert id mapping, core_message fallback, image_paths preserved
- [ ] `backend/tests/test_phase13_evaluate_endpoint.py` — covers BUG-05: integration test `/api/campaign/evaluate` with valid EvaluatePayload shape
- [ ] `frontend/src/lib/contracts.ts` — covers FE-08: file must exist before `npm run build` passes Phase 13 success criteria

## Sources

### Primary (HIGH confidence)

- `/Users/slr/MiroFishmoody/backend/app/api/campaign.py` — direct inspection: `_parse_campaigns()` field requirements, `evaluate()` endpoint wiring, `_build_campaign_image_map()` filename format
- `/Users/slr/MiroFishmoody/backend/app/utils/image_helpers.py` — direct inspection: `resolve_image_path()` already correct, no changes needed
- `/Users/slr/MiroFishmoody/backend/app/services/audience_panel.py` — direct inspection: already imports and calls `resolve_image_path()`
- `/Users/slr/MiroFishmoody/backend/app/services/pairwise_judge.py` — direct inspection: already imports and calls `resolve_image_path()`
- `/Users/slr/MiroFishmoody/frontend/src/pages/HomePage.tsx` lines 293-312 — direct inspection: Both mode race condition confirmed
- `/Users/slr/MiroFishmoody/frontend/src/pages/RunningPage.tsx` — direct inspection: fake STEPS ticker confirmed
- `/Users/slr/MiroFishmoody/frontend/src/pages/EvaluatePage.tsx` — direct inspection: correct real polling confirmed
- `/Users/slr/MiroFishmoody/frontend/src/lib/api.ts` — direct inspection: full endpoint surface mapped
- `/Users/slr/MiroFishmoody/backend/app/models/task.py` — direct inspection: TaskManager progress fields confirmed
- `/Users/slr/MiroFishmoody/backend/app/services/evaluation_orchestrator.py` — direct inspection: progress milestones (5, 10, 40, 42, 80, 90, 95, 100)
- `npm run build` output — build currently passes clean (no TypeScript errors)
- `uv run --project backend pytest backend/ -q --no-header` — 601 passed, 1 known-fail (parquet), 10 skipped

### Secondary (MEDIUM confidence)

- `.planning/research/SUMMARY.md` — project-level research summary (2026-03-18), confirmed Phase 13 assessment

### Tertiary (LOW confidence)

- None — all findings verified by direct code inspection.

## Phase Requirements

<phase_requirements>

| ID | Description | Research Support |
|----|-------------|-----------------|
| BUG-05 | 图片路径解析修复 — AudiencePanel/PairwiseJudge 对 API URL 调用 `os.path.exists()` 恒返回 False | Root cause is actually `_parse_evaluate_campaigns()` missing: frontend sends `campaign_id`/`description` but backend `_parse_campaigns()` requires `id`/`core_message`, causing 400 errors. `resolve_image_path()` in `image_helpers.py` already works; `AudiencePanel` and `PairwiseJudge` already import it. Fix: add `_parse_evaluate_campaigns()` to `campaign.py` and wire it into `evaluate()` endpoint. |
| BUG-06 | Both 模式 race condition 修复 — `Promise.all` 确保 Race + Evaluate POST 均完成后再导航 | Confirmed in `HomePage.tsx` lines 302-311: `evaluateCampaigns()` fires without `await` before `navigate('/running')`. Fix: `await evaluateCampaigns()` before navigate, with try/finally to ensure navigation always happens. |
| BUG-07 | RunningPage 假动画替换为真实后端轮询 | Confirmed in `RunningPage.tsx`: fake `STEPS` ticker with 2500ms interval. Race path is synchronous (no `task_id`), so fix is UI-only: replace fake steps with honest spinner. `EvaluatePage.tsx` already has real polling for Evaluate path — it does not need changes. |
| FE-08 | API 契约锁定 — `contracts.ts` 冻结 API 类型定义 | `frontend/src/lib/contracts.ts` does not exist. Full endpoint inventory documented above. Pattern: re-export existing types from `api.ts`, add only new types not yet in `api.ts`. Must not modify `api.ts` itself. |

</phase_requirements>

## Metadata

**Confidence breakdown:**

- BUG-05 root cause: HIGH — verified by reading `_parse_campaigns()`, `EvaluatePayload`, and `evaluate()` endpoint; the 400 error is deterministic
- BUG-06 location: HIGH — exact lines in `HomePage.tsx` identified
- BUG-07 behavior: HIGH — fake STEPS array confirmed in `RunningPage.tsx`; Race synchronous nature confirmed via `raceCampaigns()` in `api.ts`
- FE-08 scope: HIGH — full endpoint inventory from direct file inspection; `contracts.ts` absence confirmed
- image_helpers.py already correct: HIGH — file read directly, imports confirmed in both services

**Research date:** 2026-03-18
**Valid until:** 2026-04-18 (stable codebase, no external dependencies being researched)
