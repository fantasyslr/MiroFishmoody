# MiroFishmoody — Project Contract

## Build & Run

- Install all: `npm run setup:all`
- Dev (backend + frontend): `npm run dev`
- Backend only: `npm run backend` (Flask, uv)
- Frontend only: `npm run frontend` (Vite + React + TypeScript)
- Build frontend: `npm run build`
- Backend tests: `cd backend && uv run pytest`

## Architecture Boundaries

- Backend: Flask + SQLite, code in `backend/app/`
  - `api/` = HTTP routes only, no business logic
  - `services/` = business logic
  - `models/` = data models
- Frontend: React + TypeScript + Tailwind, code in `frontend/src/`
  - `pages/` = page-level components
  - `components/` = reusable UI components
  - `lib/` = API client and utilities
- LLM: Qwen via OpenAI SDK (Bailian endpoint)
- Do NOT put business logic in route handlers
- Do NOT put API calls directly in components — use `lib/`

## Business Domain (IMPORTANT)

- moodyPlus = 透明片 (transparent lenses), colored_lenses = 彩片 (colored contact lenses)
- These are 品类 (business categories), NOT 产线 (product lines)
- UI text must say "品类", never "产品线"
- Brand competes on function + aesthetics, NEVER lead with discounts or price

## Coding Conventions

- Backend: Python, type hints preferred
- Frontend: TypeScript strict, Tailwind for styling
- Chinese for user-facing text, English for code/comments

## NEVER

- Delete existing content when editing a file (e.g. don't drop README logos, don't remove existing sections when adding new ones)
- Modify `.env`, secrets, or API keys without explicit approval
- Commit without showing me the diff first
- Make UI interactions that violate common sense (e.g. clicking category A should show A's products, not hide A and show B)
- Use "产品线" in any user-facing text — use "品类"
- Fabricate data, metrics, or analysis results

## ALWAYS

- Read the file before editing it
- Preserve all existing content when making edits unless I explicitly say to remove something
- Test UI interactions make logical sense before considering a task done
- Show me what changed after edits

## Verification

- Backend changes: `cd backend && uv run pytest`
- Frontend changes: `npm run build` must pass
- UI changes: describe the interaction flow so I can verify
- API changes: test with actual request/response

## Compact Instructions

When compressing context, preserve in priority order:

1. Architecture decisions and why they were made (NEVER summarize away)
2. Which files were modified and what changed
3. Current task status — what's done, what's left
4. Errors encountered and how they were fixed
5. Tool outputs can be deleted, keep only pass/fail
