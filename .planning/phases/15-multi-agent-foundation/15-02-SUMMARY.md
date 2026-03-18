---
phase: 15-multi-agent-foundation
plan: "02"
subsystem: api
tags: [python, dataclass, scoring, agent, campaign-scorer]

requires:
  - phase: 15-multi-agent-foundation
    provides: Phase 15 foundation context; LLMSemaphore and agent infrastructure groundwork

provides:
  - AgentScore dataclass (agent_type, campaign_id, score, weight, metadata)
  - CampaignScorer.score() optional agent_scores parameter with weighted mix-in logic
  - AGENT_SCORE_WEIGHT env-configurable constant (default 0.1)

affects:
  - 16-multi-agent-expansion (Phase 16 new agents output AgentScore to integrate with CampaignScorer)

tech-stack:
  added: []
  patterns:
    - "AgentScore protocol: all new agents output List[AgentScore] with score normalized to 0-1"
    - "AGENT_SCORE_WEIGHT blend: final_score = base * (1 - w) + agent_contrib * w, only affects campaigns with agent data"

key-files:
  created:
    - backend/app/models/agent_score.py
    - backend/tests/test_agent_score.py
    - backend/tests/test_campaign_scorer_agent_scores.py
  modified:
    - backend/app/services/campaign_scorer.py

key-decisions:
  - "AgentScore.score is normalized to 0-1 by the agent itself — CampaignScorer does not normalize"
  - "AGENT_SCORE_WEIGHT=0.1 keeps agent influence modest by default; configurable via env var for production tuning"
  - "Campaigns without agent_scores entries are untouched — mix-in is opt-in per campaign"
  - "from collections import defaultdict already present in campaign_scorer, so no inline import needed"

patterns-established:
  - "Protocol pattern: new agents implement output as List[AgentScore], not wired directly into scorer logic"
  - "Backward-compat optional param: agent_scores=None means zero code change for existing callers"

requirements-completed:
  - MA-02

duration: 3min
completed: "2026-03-18"
---

# Phase 15 Plan 02: AgentScore Dataclass + CampaignScorer Mix-In Summary

**Unified AgentScore dataclass and optional weighted mix-in in CampaignScorer.score() enabling Phase 16 agents to integrate without modifying scorer internals.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-18T12:31:06Z
- **Completed:** 2026-03-18T12:34:06Z
- **Tasks:** 2
- **Files modified:** 4 (1 new model, 1 modified service, 2 new test files)

## Accomplishments

- Created `AgentScore` dataclass with 5 fields (agent_type, campaign_id, score, weight, metadata), default weight=1.0, metadata isolated per instance
- Added `agent_scores: Optional[List[AgentScore]] = None` to `CampaignScorer.score()` with full backward compatibility
- Implemented weighted average mix-in: `final = base * (1 - w) + contrib * w` at 10% weight by default, env-configurable via `AGENT_SCORE_WEIGHT`
- 21 new unit tests (9 for AgentScore, 12 for scorer integration), all green

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: AgentScore tests** - `4c2e39c` (test)
2. **Task 1 GREEN: AgentScore dataclass** - `95e904c` (feat)
3. **Task 2 RED: CampaignScorer agent_scores tests** - `909496f` (test)
4. **Task 2 GREEN: CampaignScorer agent_scores implementation** - `fa21a98` (feat)

_Note: TDD tasks have separate RED/GREEN commits per convention._

## Files Created/Modified

- `backend/app/models/agent_score.py` - New AgentScore dataclass with 5 fields
- `backend/app/services/campaign_scorer.py` - Added AgentScore import, AGENT_SCORE_WEIGHT constant, agent_scores param and mix-in block
- `backend/tests/test_agent_score.py` - 9 unit tests for AgentScore dataclass
- `backend/tests/test_campaign_scorer_agent_scores.py` - 12 integration tests for scorer mix-in

## Decisions Made

- `AgentScore.score` normalized to 0-1 by the agent itself — CampaignScorer does not re-normalize incoming values
- `AGENT_SCORE_WEIGHT=0.1` keeps agent influence modest (10%) so panel/pairwise signals still dominate; tunable via env var
- Campaigns missing from agent_scores are completely unaffected — mix-in is per-campaign opt-in
- Used existing `defaultdict` from `collections` already imported in campaign_scorer; no new top-level imports beyond AgentScore

## Phase 16 Usage Guide

New agents in Phase 16 only need to:

```python
from app.models.agent_score import AgentScore

# Inside agent: normalize score to 0-1
agent_out = [
    AgentScore(agent_type="devil_advocate", campaign_id=cid, score=0.4, metadata={"dissent": ...})
    for cid in campaigns
]

# Pass to scorer — no other changes needed
rankings, board = scorer.score(campaigns, panel_scores, pairwise_results, bt_scores, agent_scores=agent_out)
```

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Pre-existing failures in `scripts/test_sync_etl_enrichment.py` (missing pyarrow) and `tests/test_smoke.py` (missing LLM_API_KEY) are unrelated to this plan and pre-date these changes.

## User Setup Required

None - no external service configuration required. AGENT_SCORE_WEIGHT defaults to 0.1; set env var to tune.

## Next Phase Readiness

- Phase 16 agents (MultiJudge, DevilsAdvocate, ConsensusAgent) can immediately produce `List[AgentScore]` and pass to `scorer.score(..., agent_scores=...)`
- No CampaignScorer modifications needed when adding new agent types
- Weight tuning: set `AGENT_SCORE_WEIGHT` env var (default 0.1) to increase/decrease agent influence relative to panel/pairwise signals

---
*Phase: 15-multi-agent-foundation*
*Completed: 2026-03-18*
