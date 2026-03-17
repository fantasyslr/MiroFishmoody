# Architecture Patterns

**Domain:** Brand campaign simulation/evaluation platform (Moody Lenses)
**Researched:** 2026-03-17
**Confidence:** HIGH (based on direct codebase analysis)

## Current Architecture (As-Is)

```
                    React SPA (Vite + React 19)
                    ├── HomePage (Race form)
                    ├── RunningPage (Race execution)
                    ├── ResultPage (Race results)
                    └── [No Evaluate UI yet]
                              │
                              │ fetch via lib/api.ts
                              ▼
                    Flask Monolith (create_app factory)
                    ├── /api/auth      (session auth)
                    ├── /api/campaign   (evaluate pipeline)
                    └── /api/brandiction (race pipeline)
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
     EvaluationOrchestrator  BaselineRanker  BrandStateEngine
     (async daemon thread)   (sync)          (sync)
              │               │               │
              ▼               ▼               ▼
         LLMClient      BrandictionStore    BrandictionStore
         (Qwen/Bailian)  (SQLite)           (SQLite)
```

**Two distinct execution models coexist:**

| Path | Trigger | Execution | Duration | Frontend |
|------|---------|-----------|----------|----------|
| Race | `/api/brandiction/race` | Synchronous in request | 5-30s | Full UI flow |
| Evaluate | `/api/campaign/evaluate` | Async daemon thread | 2-10min | API only, no UI |

## Recommended Architecture (To-Be)

### Target: Unified Simulation Entry with Dual Paths

```
                    React SPA
                    ├── HomePage (unified entry)
                    │   ├── Mode selector: Race / Evaluate / Both
                    │   ├── Plan builder (shared)
                    │   ├── Category selector → persona config
                    │   └── Image uploader (shared)
                    ├── RunningPage (supports both paths)
                    ├── EvaluatePage (NEW: async progress + results)
                    └── ResultPage (enhanced: Race + Evaluate combined)
                              │
                              │ lib/api.ts (extended)
                              ▼
                    Flask Monolith
                    ├── /api/auth
                    ├── /api/campaign
                    │   └── /evaluate (fix image handling)
                    ├── /api/brandiction
                    │   └── /race (add concurrent image analysis)
                    └── /api/persona (NEW: category-based persona config)
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
     EvaluationOrchestrator  BaselineRanker  PersonaRegistry
     (async, fixed images)   (concurrent IA) (NEW)
              │               │
              ▼               ▼
         LLMClient      ImageAnalyzer
         (shared)        (concurrent via ThreadPool)
```

## Component Boundaries

### Existing Components (Modify)

| Component | Responsibility | Changes Needed | Communicates With |
|-----------|---------------|----------------|-------------------|
| `HomePage` | Plan input + race config | Add mode selector (Race/Evaluate/Both), category-based persona preview | `lib/api.ts`, `RunningPage` |
| `RunningPage` | Race execution display | Support Evaluate async polling alongside Race sync | `lib/api.ts`, `ResultPage`/`EvaluatePage` |
| `ResultPage` | Race results display | Add Evaluate results tab when both modes run | `localStorage` + API |
| `AudiencePanel` | 5-persona LLM jury | Accept persona list as parameter (not hardcoded), fix `image_paths` bug | `EvaluationOrchestrator`, `LLMClient` |
| `ImageAnalyzer` | Per-image LLM vision | Change from serial to `ThreadPoolExecutor` | `BaselineRanker`, `LLMClient` |
| `EvaluationOrchestrator` | 4-phase async pipeline | Pass persona config through, fix image URL resolution | `AudiencePanel`, `PairwiseJudge`, `CampaignScorer`, `SummaryGenerator` |
| `_evaluation_store` | In-memory result cache | Add `threading.Lock`, add LRU eviction (max 100 entries) | `campaign.py` API handlers |

### New Components (Build)

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `PersonaRegistry` (backend service) | Maps category -> persona list; admin CRUD | `AudiencePanel`, `EvaluationOrchestrator`, API layer |
| `EvaluatePage` (frontend page) | Evaluate mode UI: submit, poll progress, display jury results | `lib/api.ts`, `useReviewStore` |
| Unified entry UI (within `HomePage`) | Mode selector + shared plan builder that feeds both paths | `RunningPage`, `EvaluatePage` |

### Component Dependency Graph

```
PersonaRegistry ← (no deps, leaf service)
     ↑
AudiencePanel ← LLMClient, PersonaRegistry
     ↑
EvaluationOrchestrator ← AudiencePanel, PairwiseJudge, CampaignScorer, SummaryGenerator
     ↑
campaign.py (API) ← EvaluationOrchestrator, TaskManager

ImageAnalyzer ← LLMClient (concurrent)
     ↑
BaselineRanker ← BrandictionStore, ImageAnalyzer
     ↑
brandiction.py (API) ← BaselineRanker, BrandStateEngine
```

## Data Flow

### Flow 1: Unified Entry -> Race Path (Enhanced)

```
1. User fills plans in HomePage (shared plan builder)
2. Selects mode = "Race" (or "Both")
3. Selects category (moodyPlus / colored_lenses)
4. Uploads images per plan (existing flow, max 5 per plan)
5. Submit → saveRaceState() to localStorage
6. Navigate to /running
7. RunningPage calls POST /api/brandiction/race
8. Backend:
   a. BaselineRanker.rank_campaigns() — historical baseline
   b. ImageAnalyzer.analyze_plan_images() — NOW CONCURRENT via ThreadPoolExecutor
   c. apply_visual_adjustment() — merge visual scores
   d. BrandStateEngine.predict_impact() — optional cognitive model
9. Return RaceResult JSON → localStorage → /result
```

**Change from current:** Step 8b switches from serial to concurrent image analysis.

### Flow 2: Unified Entry -> Evaluate Path (New Frontend)

```
1. User fills plans in HomePage (shared plan builder)
2. Selects mode = "Evaluate" (or "Both")
3. Selects category → PersonaRegistry returns matching persona set
4. User reviews persona panel (can see who will judge)
5. Submit → POST /api/campaign/evaluate
6. Backend spawns daemon thread:
   a. EvaluationOrchestrator.run()
   b. AudiencePanel uses category-specific personas (not hardcoded)
   c. image_paths resolved via _resolve_image_url_to_path() (BUG FIX)
   d. Images sent as base64 to LLM
   e. PairwiseJudge → CampaignScorer → SummaryGenerator
7. Navigate to /evaluate/:taskId (NEW page)
8. EvaluatePage polls GET /api/campaign/evaluate/status/:taskId
9. On completion, displays jury results inline
```

**Critical changes:**
- Personas loaded from `PersonaRegistry` by category, not hardcoded in `audience_panel.py`
- `image_paths` bug fixed: URL strings resolved to local file paths before `os.path.exists()`
- Frontend page added to visualize the async evaluation

### Flow 3: "Both" Mode

```
1. User selects "Both" → system runs Race sync + Evaluate async in parallel
2. Race result available in seconds → show immediately on /result
3. Evaluate result arrives minutes later → notification or tab update on /result
4. Combined view: Race ranking (evidence-based) + Evaluate jury (perception-based)
```

**Implementation approach:** Fire Race synchronously first (fast), then fire Evaluate async. ResultPage shows Race immediately with an "Evaluate pending" indicator that updates via polling.

### State Management Strategy

| Data | Current | Proposed | Rationale |
|------|---------|----------|-----------|
| Plan form state | `useState` in HomePage | Keep as-is | No cross-page sharing needed during input |
| Race payload/result | `localStorage` | Keep as-is | Works for single-user flow |
| Evaluate task tracking | None (API only) | `localStorage` (taskId) + API polling | Consistent with Race pattern |
| Persona config | Hardcoded in `audience_panel.py` | `PersonaRegistry` service + JSON config file | Decouples personas from code |
| Mode selection | N/A | `localStorage` via `saveRaceState()` extended | Survives navigation |

## Patterns to Follow

### Pattern 1: Image Path Resolution (Bug Fix Pattern)

**What:** Centralize all image path resolution through a single helper that handles both local paths and API URLs.

**When:** Any service that reads `campaign.image_paths` for LLM vision calls.

**Example:**
```python
# backend/app/utils/image_resolver.py
def resolve_to_local_path(image_ref: str) -> Optional[str]:
    """Resolve image reference to local filesystem path.

    Handles:
    - Local path: /uploads/images/set_id/file.jpg → return as-is
    - API URL: /api/campaign/image-file/set_id/file.jpg → map to local path
    - Full URL: http://host/api/campaign/image-file/... → extract and map
    """
    if os.path.exists(image_ref):
        return image_ref
    # Extract from URL pattern
    match = re.search(r'/api/campaign/image-file/([^/]+)/(.+)$', image_ref)
    if match:
        local = os.path.join(UPLOAD_FOLDER, 'images', match.group(1), match.group(2))
        return local if os.path.exists(local) else None
    return None
```

**Apply to:** `AudiencePanel._evaluate_single()`, `PairwiseJudge` (same bug), `ImageAnalyzer`

### Pattern 2: Concurrent Image Analysis

**What:** Use `ThreadPoolExecutor` for parallel LLM vision calls on multiple images.

**When:** `ImageAnalyzer.analyze_plan_images()` processes 2+ images per plan.

**Example:**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def analyze_plan_images(self, plans: list) -> dict:
    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(self._analyze_single_image, img): (plan_id, img)
            for plan_id, images in plan_images.items()
            for img in images
        }
        for future in as_completed(futures):
            plan_id, img = futures[future]
            try:
                results.setdefault(plan_id, []).append(future.result())
            except Exception as e:
                logger.warning(f"Image analysis failed for {img}: {e}")
    return results
```

**Max workers = 3:** Bailian API has rate limits; 3 concurrent vision calls is safe.

### Pattern 3: Category-Based Persona Registry

**What:** Decouple persona definitions from code. Load from a JSON config file, keyed by category.

**When:** `AudiencePanel` needs personas for evaluation.

**Example:**
```python
# backend/app/services/persona_registry.py
class PersonaRegistry:
    DEFAULT_CONFIG = "backend/persona_config.json"

    def get_personas(self, category: str) -> list[dict]:
        """Return persona list for given category.
        Falls back to 'default' if category not found."""
        config = self._load_config()
        return config.get(category, config.get('default', []))
```

**Config structure:**
```json
{
  "moodyplus": [
    {"id": "daily_wearer", "name": "...", "description": "...", "evaluation_focus": "..."},
    {"id": "acuvue_switcher", ...},
    {"id": "eye_health", ...}
  ],
  "colored_lenses": [
    {"id": "beauty_first", ...},
    {"id": "trend_follower", ...},
    {"id": "kol_influenced", ...}
  ],
  "default": [/* current 5 personas as fallback */]
}
```

### Pattern 4: Async Task Polling on Frontend

**What:** Standard polling pattern for long-running Evaluate tasks.

**When:** EvaluatePage waits for jury results.

**Example:**
```typescript
// EvaluatePage.tsx
useEffect(() => {
  if (!taskId || status === 'completed') return
  const interval = setInterval(async () => {
    const res = await getEvaluateStatus(taskId)
    setProgress(res.progress)
    setMessage(res.message)
    if (res.status === 'completed' || res.status === 'failed') {
      clearInterval(interval)
      setStatus(res.status)
      if (res.status === 'completed') setResult(res.result)
    }
  }, 3000) // Poll every 3s
  return () => clearInterval(interval)
}, [taskId, status])
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Dual Plan Builders

**What:** Building a separate plan input form for Evaluate mode (like `useReviewStore` already does separately from `HomePage`).

**Why bad:** Two diverging plan schemas, duplicated validation, confused users. `useReviewStore` already exists as an alternative builder -- having three would be worse.

**Instead:** Unify into one plan builder in `HomePage`. The existing `useReviewStore` can be retired or repurposed as the backing store for the unified builder. Mode selection (Race/Evaluate/Both) should be a toggle, not a different page.

### Anti-Pattern 2: Hardcoded Persona Arrays in Service Code

**What:** The current `PERSONAS` list is defined as a module-level constant in `audience_panel.py`.

**Why bad:** Adding personas for `colored_lenses` means editing Python code, redeploying, and risking merge conflicts. Business users cannot configure this.

**Instead:** `PersonaRegistry` loads from JSON config. `AudiencePanel.__init__()` receives persona list as a parameter.

### Anti-Pattern 3: In-Memory Dict Without Bounds

**What:** `_evaluation_store: dict = {}` in `campaign.py` grows without limit, no thread safety.

**Why bad:** Memory leak over time. Race condition when two evaluations write simultaneously.

**Instead:** Add `threading.Lock` for all reads/writes. Add LRU eviction (keep last 100 results). Results already persist to disk via `_save_result()`, so eviction is safe.

### Anti-Pattern 4: God Class BrandStateEngine

**What:** 1319-line class doing perception modeling, replay, backtest, and simulation.

**Why bad:** Hard to test, hard to modify, merge conflict magnet.

**Instead:** Not in scope for this milestone, but flag for future refactoring. Do not add more methods to it.

## Scalability Considerations

| Concern | Current (5 users) | Target (15 users) | Notes |
|---------|-------------------|--------------------|-------|
| Concurrent evaluations | 1 at a time (daemon thread, no queue) | 3-5 concurrent (ThreadPool) | SQLite WAL handles concurrent reads; writes serialized |
| Image analysis speed | Serial (N images = N * 5s) | Concurrent (N images in ~5s) | ThreadPoolExecutor, max_workers=3 |
| LLM rate limits | Not enforced | Should add semaphore | Bailian has per-minute token limits |
| Memory (_evaluation_store) | Unbounded dict | LRU cache, max 100 | Disk persistence already exists as backup |
| SQLite contention | No WAL mode | Enable WAL mode | `PRAGMA journal_mode=WAL` on both databases |

## Suggested Build Order

Based on dependency analysis, the components should be built in this order:

### Phase 1: Fix Foundation (No New Features)

**Build:** Image path resolution utility, `_evaluation_store` thread safety, SQLite WAL mode

**Rationale:** These are bugs/risks that must be fixed before building new features on top. The image path bug would silently break any new Evaluate UI. The thread safety issue would cause data corruption under concurrent use.

**Dependencies:** None -- these are leaf-level fixes.

### Phase 2: PersonaRegistry + AudiencePanel Refactor

**Build:** `PersonaRegistry` service, persona JSON config for both categories, modify `AudiencePanel` to accept injected personas.

**Rationale:** This decouples persona config from code and is required before the Evaluate frontend can offer category-based persona selection.

**Dependencies:** Phase 1 (image resolution fix feeds into AudiencePanel).

### Phase 3: Concurrent Image Analysis

**Build:** `ThreadPoolExecutor` in `ImageAnalyzer`, rate-limit-aware semaphore for LLM calls.

**Rationale:** Performance improvement that's independent of UI work. Can be built and tested in isolation.

**Dependencies:** Phase 1 (image resolution utility).

### Phase 4: Evaluate Frontend + Unified Entry

**Build:** `EvaluatePage` component, mode selector in `HomePage`, unified plan builder, API client extensions in `lib/api.ts`.

**Rationale:** This is the largest surface area change. Depends on backend fixes (Phase 1-2) being stable. The unified entry design prevents the anti-pattern of dual plan builders.

**Dependencies:** Phase 1 (working image pipeline), Phase 2 (persona config for category selector).

### Phase 5: Combined Results View

**Build:** Enhanced `ResultPage` showing Race + Evaluate results together when "Both" mode is used.

**Dependencies:** Phase 4 (both paths must work end-to-end).

### Dependency Graph

```
Phase 1 (Foundation Fixes)
   ├──→ Phase 2 (PersonaRegistry)
   │        └──→ Phase 4 (Evaluate UI + Unified Entry)
   │                  └──→ Phase 5 (Combined Results)
   └──→ Phase 3 (Concurrent Image Analysis)
```

Phases 2 and 3 can be built in parallel after Phase 1.

## Sources

- Direct codebase analysis of `/Users/slr/MiroFishmoody/` (PRIMARY)
- `backend/app/services/audience_panel.py` — hardcoded personas, image bug at line 181
- `backend/app/services/evaluation_orchestrator.py` — 4-phase pipeline structure
- `backend/app/api/campaign.py` — `_evaluation_store` dict, daemon thread pattern
- `backend/app/services/image_analyzer.py` — serial image analysis
- `frontend/src/App.tsx` — route structure, no evaluate route
- `frontend/src/store.ts` — `useReviewStore` (separate from HomePage state)
- `.planning/PROJECT.md` — requirements and constraints
- `.planning/codebase/ARCHITECTURE.md` — current architecture documentation

---

*Architecture research: 2026-03-17*
