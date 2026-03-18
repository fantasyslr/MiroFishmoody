---
phase: 14-frontend-rewrite-core-pages
plan: "01"
subsystem: frontend
tags: [sessionStorage, persistence, persona-preview, HomePage]
dependency_graph:
  requires: []
  provides: [homeFormStorage-module, homepage-form-persistence, persona-preview-sidebar]
  affects: [frontend/src/pages/HomePage.tsx, frontend/src/lib/homeFormStorage.ts]
tech_stack:
  added: []
  patterns: [sessionStorage-persistence, functional-useState-initializer, override-spread-pattern]
key_files:
  created:
    - frontend/src/lib/homeFormStorage.ts
  modified:
    - frontend/src/pages/HomePage.tsx
decisions:
  - "loadHomeForm() called once in component body (not useEffect) so useState initializer has the value synchronously — no flash of default state"
  - "persistForm() uses spread overrides pattern so callers pass only the changed field without needing to read all other state"
  - "clearHomeForm() called before navigate() in all three submit paths (race/evaluate/both) to guarantee cleanup even if navigate throws"
metrics:
  duration: "3min"
  completed_date: "2026-03-18"
  tasks_completed: 2
  files_changed: 2
---

# Phase 14 Plan 01: HomePage sessionStorage Persistence + Persona Preview Summary

**One-liner:** sessionStorage form persistence via homeFormStorage.ts + persona preview sidebar showing product-line-specific jury (6 moodyplus / 5 colored_lenses personas).

## What Was Built

### homeFormStorage.ts (new)

Utility module at `frontend/src/lib/homeFormStorage.ts` with four exports:

- `HOME_FORM_KEY` — storage key constant `'miro_home_form_v1'`
- `HomeFormSnapshot` — type covering mode/market/productLine/sortBy/seasonTag/plans
- `saveHomeForm(snapshot)` — writes to sessionStorage, silently swallows quota/unavailable errors
- `loadHomeForm()` — reads + parses, returns null if missing or plans array is empty
- `clearHomeForm()` — removes the key

### HomePage.tsx changes

1. **Import** — added `saveHomeForm, loadHomeForm, clearHomeForm` from `../lib/homeFormStorage`
2. **PERSONA_PREVIEW constant** — defined at module level outside component, maps product line to persona name arrays (moodyplus: 6, colored_lenses: 5)
3. **State restoration** — `const savedForm = loadHomeForm()` called at top of component; all six useState calls use `savedForm?.field ?? default` pattern; plans uses a function initializer
4. **persistForm() helper** — collects all current state + caller overrides, calls saveHomeForm; placed before buildRacePayload
5. **onChange wiring** — all field onChange handlers now call persistForm with the new value as override; updatePlan computes nextPlans first, then setPlans(nextPlans) + persistForm({ plans: nextPlans })
6. **clearHomeForm on submit** — called in race path before navigate('/running'), in evaluate try block before navigate('/evaluate'), and in both-mode finally block before navigate('/running')
7. **Persona preview sidebar card** — inserted above the existing "评估矩阵" card in the sticky right sidebar; title shows product line display name + count; list shows numbered persona names with circular index badges

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- FOUND: frontend/src/lib/homeFormStorage.ts
- FOUND: frontend/src/pages/HomePage.tsx
- FOUND commit 0d8c8fc: feat(14-01): create homeFormStorage.ts sessionStorage persistence module
- FOUND commit 9d34849: feat(14-01): integrate sessionStorage persistence and persona preview in HomePage
