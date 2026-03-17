---
phase: 07-unified-entry
verified: 2026-03-17T07:10:00Z
status: passed
score: 6/6 must-haves verified
re_verification: false
---

# Phase 7: Unified Entry Verification Report

**Phase Goal:** 用户从统一入口选择推演模式并提交方案，无需理解后端 API 差异
**Verified:** 2026-03-17T07:10:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User sees three mode cards (Race/Evaluate/Both) above the form on HomePage | VERIFIED | `MODE_OPTIONS` array + grid section at line 321; three `button` elements with `SimulationMode` values |
| 2 | User can select a mode and the card visually highlights as selected | VERIFIED | `border-primary bg-primary/5` class applied when `mode === opt.value` (line 330-333) |
| 3 | Default mode is Race, preserving backward compatibility | VERIFIED | `useState<SimulationMode>('race')` at line 53 |
| 4 | Clicking submit with Race mode works exactly as before (navigate to /running) | VERIFIED | `handleSubmit` lines 269-274: builds RacePayload, calls `saveRaceState`, navigates to `/running` |
| 5 | Clicking submit with Evaluate mode submits to evaluate API and navigates to /evaluate | VERIFIED | `handleSubmit` lines 276-287: calls `evaluateCampaigns`, `saveEvaluateState`, navigates to `/evaluate` |
| 6 | Clicking submit with Both mode fires both APIs and navigates to /running with a pending evaluate link | VERIFIED | lines 290-306: `saveRaceState` + navigate `/running` immediately; `evaluateCampaigns` fired in background with `.then` saving `saveBothModeState` |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/pages/HomePage.tsx` | Mode selector cards + unified submit handler | VERIFIED | 650 lines; contains `SimulationMode`, `MODE_OPTIONS`, `handleSubmit`, `buildRacePayload`, `buildEvaluatePayload` |
| `frontend/src/lib/api.ts` | submitBothMode helper or equivalent; `evaluateCampaigns` | VERIFIED | Contains `saveBothModeState`, `getBothModeState`, `clearBothModeState` at lines 369-382; `evaluateCampaigns` at line 340 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `HomePage.tsx` | `frontend/src/lib/api.ts` | `evaluateCampaigns`, `saveEvaluateState`, `saveBothModeState` | WIRED | All three imported on line 4; `evaluateCampaigns` called at lines 280 and 297; `saveEvaluateState` called at lines 281 and 299; `saveBothModeState` called at line 300 |
| `HomePage.tsx` | `/running` or `/evaluate` | `navigate` based on selected mode | WIRED | Race -> `/running` (line 272); Evaluate -> `/evaluate` (line 282); Both -> `/running` (line 306) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| UNIF-01 | 07-01-PLAN.md | 统一推演入口 — 在 HomePage 添加模式选择器（Race / Evaluate / Both） | SATISFIED | `SimulationMode` type + `MODE_OPTIONS` + mode selector grid (lines 7-13, 321-345); `useState<SimulationMode>('race')` default |
| UNIF-02 | 07-01-PLAN.md | 统一方案录入表单 — 一套表单支持两种推演路径，用户无需知道后端 API 差异 | SATISFIED | Single form (lines 347-585) shared across all modes; `handleSubmit` branches internally on mode; no mode-specific form fields exposed to user |

**Orphaned requirements check:** REQUIREMENTS.md Traceability table maps only UNIF-01 and UNIF-02 to Phase 7. UNIF-03 is mapped to Phase 3 (Category Persona Config) and was verified there. No orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `HomePage.tsx` | 433 | `placeholder="例：春季科学种草"` | Info | HTML input placeholder attribute — not a code anti-pattern |

No blockers or warnings found.

### Human Verification Required

#### 1. Mode Card Visual Highlight

**Test:** Load HomePage, click "深度评审" card
**Expected:** Card border changes to primary color and background tints; other two cards lose highlight
**Why human:** CSS class toggling verified in code, but rendering depends on Tailwind CSS build and browser

#### 2. Both Mode — Evaluate Link Accessibility After Race Result

**Test:** Submit with Both mode; wait for Race result page to load; check if a "查看深度评审结果" link or indicator appears
**Expected:** RunningPage or ResultPage reads `getBothModeState()` from localStorage and displays a link to the evaluate result
**Why human:** `saveBothModeState` is written correctly, but whether RunningPage/ResultPage *consumes* it is outside Phase 7 scope — Phase 7 only writes the state; Phase 8 polish is expected to surface it

#### 3. Evaluate Mode Spinner

**Test:** Select Evaluate mode, click submit
**Expected:** Button shows `Loader2` spinner while awaiting `evaluateCampaigns` response
**Why human:** `submitting` state + `Loader2` conditional render verified in code (lines 629-630); actual visual feedback requires runtime

### Gaps Summary

No gaps. All six must-have truths are verified at all three levels (exists, substantive, wired). Build passes with zero TypeScript errors (`npm run build` — 2150 modules, 260ms). Both requirement IDs (UNIF-01, UNIF-02) are fully satisfied with implementation evidence.

---

_Verified: 2026-03-17T07:10:00Z_
_Verifier: Claude (gsd-verifier)_
