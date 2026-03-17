# Coding Conventions

**Analysis Date:** 2026-03-17

## Naming Patterns

**Files:**
- Python backend: `snake_case.py` — e.g., `campaign_scorer.py`, `brand_state_engine.py`
- TypeScript frontend: `PascalCase.tsx` for components/pages, `camelCase.ts` for utilities/hooks/lib
- Test files: `test_<module>.py` matching service name — e.g., `test_scorer.py`, `test_brandiction.py`

**Python Functions and Methods:**
- `snake_case` throughout — e.g., `make_campaign()`, `_fresh_store()`, `get_logger()`
- Private helpers prefixed with `_` — e.g., `_login()`, `_save_result()`, `_load_users()`
- Factory/builder helpers: `make_<thing>()` pattern — e.g., `make_campaign()`, `make_panel()`

**Python Classes:**
- `PascalCase` — e.g., `CampaignScorer`, `BrandictionStore`, `TaskManager`
- Singleton classes expose `_reset_instance()` class method for test isolation

**TypeScript Functions:**
- Named exports using `PascalCase` for React components: `export function SectionCard()`
- `camelCase` for regular functions: `makePlan()`, `makeImageDraft()`, `uuid()`
- Custom hooks: `useAsync`, `useReviewStore` — `use` prefix strictly

**TypeScript Types/Interfaces:**
- `PascalCase` type aliases for props: `type SectionCardProps = {...}`
- Interfaces for store shape: `interface ReviewStore {...}`
- Types defined locally in the file that uses them — no shared `types.ts` barrel

**Variables:**
- Python: `snake_case` — `bt_scores`, `panel_scores`, `set_id`
- TypeScript: `camelCase` — `planImages`, `uploadError`, `draftSetId`
- Constants: Python `UPPER_SNAKE_CASE` — `PERSONAS`, `SHIP_WIN_RATE`, `KILL_PANEL_FLOOR`; TypeScript `UPPER_SNAKE` or `camelCase` depending on scope

## Code Style

**Formatting:**
- Python: No formatter config detected; PEP 8 style followed manually. 4-space indentation.
- TypeScript: No `.prettierrc` detected. Vite/TypeScript project uses 2-space indentation based on code samples.

**Linting:**
- TypeScript: ESLint via `frontend/eslint.config.js` with `typescript-eslint`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`. Only `.ts` and `.tsx` files linted.
- Python: No linter config file present. `noqa` comments used sparingly — `# noqa: E402, F401` in `backend/app/api/__init__.py`

**TypeScript Strictness:**
- `strict: true` in `frontend/tsconfig.app.json`
- `noUnusedLocals: true`, `noUnusedParameters: true`
- `noFallthroughCasesInSwitch: true`
- `erasableSyntaxOnly: true` (TypeScript 5.9 mode)
- `verbatimModuleSyntax: true` — `import type` required for type-only imports

## Import Organization

**Python (backend):**
1. Standard library (`os`, `sys`, `json`, `threading`, `datetime`)
2. Third-party (`flask`, `werkzeug`, `pydantic`)
3. Relative app imports (`from ..utils.logger import get_logger`, `from ..models.campaign import Campaign`)
- Relative imports only within `app/` package — no absolute `app.X` imports in production code
- Test files use `sys.path.insert(0, ...)` to bootstrap then absolute imports from `app`

**TypeScript (frontend):**
1. React/framework imports (`import { useState } from 'react'`)
2. Third-party libraries (`lucide-react`, `react-router-dom`)
3. Internal lib (`../lib/api`, `../utils`)
4. Local/sibling (`./SectionCard`)
- `import type` for type-only imports (enforced by `verbatimModuleSyntax`)

**Path Aliases:**
- None configured. All imports use relative paths (`../lib/api`, `../../utils`)

## Error Handling

**Python (backend):**
- Services raise `ValueError` with Chinese error messages for business rule violations: `raise ValueError("至少需要 2 个 campaign 方案")`
- API layer catches exceptions and returns `jsonify({"error": str(e)})` with appropriate HTTP status
- LLM calls use retry wrapper from `backend/app/utils/retry.py`
- `warnings.warn()` used for configuration issues (missing env vars) rather than hard failures

**TypeScript (frontend):**
- Custom `ApiError` class in `frontend/src/lib/api.ts` extends `Error` with `.status: number`
- `useAsync` hook in `frontend/src/lib/useAsync.ts` catches all errors and maps to `{ status: 'error', error: string }` discriminated union state
- Unmount safety via `mountedRef` pattern in async hooks — state not set after component unmounts

## Logging

**Framework:** Python `logging` module, configured in `backend/app/utils/logger.py`

**Patterns:**
- `get_logger('ranker.<module>')` called at module level: `logger = get_logger('ranker.audience_panel')`
- Logger names follow `ranker.<layer>.<module>` hierarchy — e.g., `ranker.api.campaign`, `ranker.campaign_scorer`
- File handler: detailed format `[timestamp] LEVEL [name.func:line] msg` at DEBUG level, rotating 10MB files in `backend/logs/`
- Console handler: simple format `[time] LEVEL: msg` at INFO level only
- `logger.propagate = False` prevents duplicate output

## Comments

**When to Comment:**
- Module-level docstrings in Chinese for purpose/overview: `"""Campaign API — 方案提交 + 评审 + 结算 + 校准"""`
- Section dividers using `# ──────────────────────────────────────────────` in test files
- Inline comments in Chinese for business logic rationale
- English comments for technical/algorithmic details
- `TODO`/`FIXME` usage is rare — only 2 instances found in codebase

**Docstrings:**
- Class and public method docstrings present on services: `"""综合评分，输出 (rankings, scoreboard)。"""`
- Args/Returns blocks omitted — inline type hints serve as documentation

## Function Design

**Size:** Service methods are moderate (20-60 lines); API handlers can grow to 100+ lines due to inline orchestration logic.

**Parameters:**
- Python: type hints preferred but not uniformly enforced. Complex input via dataclass/model objects not raw dicts.
- TypeScript: props via local `type XxxProps` before the function. Optional props use `?`, defaulted in destructuring.

**Return Values:**
- Python services return typed objects (`Tuple[List[CampaignRanking], ScoreBoard]`), not dicts
- API handlers always return `jsonify(...)` — no raw dict returns from route handlers
- TypeScript API functions return `Promise<T>` via generic `request<T>()` wrapper

## Module Design

**Python Exports:**
- Classes and public functions accessible from module directly — no `__all__` declarations found
- Module-level logger instances and config constants are top-level

**TypeScript Exports:**
- Named exports only — no default exports in components or lib files
- `export function`, `export type`, `export const` — no `export default`

**Backend Layer Contracts (from CLAUDE.md):**
- `api/` = HTTP routes only, no business logic
- `services/` = business logic, no Flask imports
- `models/` = data structures, no service calls

**Singleton Pattern:**
- `TaskManager`, `BrandictionStore` implemented as singletons with `_instance` class attribute
- Expose `_reset_instance()` class method exclusively for test isolation — never called in production

---

*Convention analysis: 2026-03-17*
