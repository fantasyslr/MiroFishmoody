# Changelog

All notable changes to this repository are documented here.

This repo starts its documented SemVer baseline at `v0.5.0`. Earlier rewrite work still exists in Git history, but is consolidated into the current release notes instead of being retro-tagged.

## [0.5.0] - 2026-03-13

First documented release baseline for the current `moody-main` branch.

### Added / 新增

- Session-based authentication with `/api/auth/login`, `/api/auth/logout`, and `/api/auth/me`.
- Role-aware UI flow with `admin` / `user` distinction and admin-facing dashboard routes.
- Brief-first campaign creation flow with `/api/campaign/parse-brief`.
- Campaign image upload, per-campaign image binding, and image rendering in result views.
- Async task metadata with readable submitter, campaign names, and submission time.
- Persistent evaluation result storage plus JSON export via `/api/campaign/export/<set_id>`.
- Post-launch resolution and calibration endpoints for judge/persona feedback loops.

### Changed / 调整

- Reframed the product around Moody campaign review instead of the original generic "predict anything" narrative.
- Extracted orchestration logic into a dedicated evaluation orchestrator.
- Tightened the evaluation stack around audience review, pairwise judging, probability aggregation, and dimension scoring.
- Redesigned the UI and admin workflow for everyday internal review operations.
- Cleaned up terminology so the product reads like a campaign review system instead of a prediction-market experiment.

### Fixed / 修复

- Prevent duplicate `set_id` overwrites when submitting evaluations.
- Prevent duplicate post-launch resolution for the same review set.
- Allow resolution fallback from persisted prediction files after service restart.
- Correct calibration readiness messaging so it depends on sets that actually contain prediction data.
- Align `judge_calibration` state labels with real coverage behavior (`complete` vs `partial`).
- Improve task list readability and review follow-through across dashboard, running, and result pages.

### Included rewrite milestones / 收录的重构阶段

- `P0`: required validation, brief mode entry, readable task list
- `P1`: login system, image upload, terminology cleanup
- `P2`: orchestrator extraction, market judge, probability fixes, dimension scoring
- `P3`: task persistence, image display, report export
- `Recent polish`: UI redesign, admin role, review fixes
