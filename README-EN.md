<div align="center">

<img src="./static/image/MiroFishmoody_logo.png" alt="MiroFishmoody Logo" width="60%"/>

# MiroFishmoody

**An internal decision market being rebuilt for Moody Lenses**

Shifting from "predict anything" social simulation to an internal market-style system for pricing campaign choices before launch.

[English](./README-EN.md) | [中文](./README.md)

</div>

## Positioning

**MiroFishmoody** is a product fork of [MiroFish](https://github.com/666ghj/MiroFish), rebuilt around a narrower and more practical goal:

- compare multiple campaign concepts before launch
- identify which angle is more likely to win
- turn intuition-heavy creative debates into a structured internal decision market

This project is not trying to answer "what will the future be?"

It is trying to answer:

- which concept is stronger among `A / B / C`
- which option is more eye-catching, credible, and audience-fit
- which objections or claim risks are likely to hurt conversion
- whether a concept should be `ship / revise / kill`
- which options do not have enough edge to deserve internal conviction

## Why this fork exists

Most early e-commerce campaign decisions still rely on taste, confidence, and internal persuasion:

- "this one looks better"
- "I think users will like this"
- "this angle feels stronger"

That is not reliable enough.

For Moody, the real need is an **internal decision market**:

- not a fake ROAS / GMV oracle
- not a single operator's judgment disguised as strategy
- not a giant simulation world for its own sake
- but a system that increases the odds of choosing the better concept before money is spent
- with probability outputs, sub-markets, and post-launch calibration

## Lineage

This project's next move did not come from AI alone. It also came directly out of **crypto, prediction market, and event-pricing culture**.

Without that background, this probably would have stayed a multi-agent evaluator instead of becoming an **internal decision market**.

What is being borrowed here is not token mechanics. It is a way of thinking:

- price disagreement instead of just arguing about it
- force "I think" into "what probability would you actually assign?"
- keep both the bull case and bear case alive at the same time
- tie opinions to later resolution so the system can be settled, proven wrong, and recalibrated

This repo therefore intentionally pays respect to that lineage:

- early prediction market builders
- crypto-native event market players
- communities that made `odds`, `edge`, and `implied probability` part of everyday decision language
- and also the trading-desk habit represented by figures like **SBF**: asking how the market prices disagreement before asking who sounds most convincing in the room

That acknowledgment is about the **epistemic machinery** only. It is not an endorsement of every later actor, project, or outcome.

## Moody business context

This fork is being shaped around **Moody Lenses**:

- two product lines: `colored lenses` and `moodyPlus`
- the brand competes on `function + aesthetics`, not discount-led messaging
- `moodyPlus` is aimed at existing contact lens wearers who care about natural effect, comfort, and eye-health confidence
- the system is intended to help pre-screen concepts before real Meta, Google, landing page, and creator testing

## What the engine is meant to evaluate

The decision logic should prioritize **relative ranking + probability pricing**, not absolute forecasting.

Core evaluation dimensions:

- Hook strength
- Visual / aesthetic pull
- Message clarity
- Trust and claim believability
- Audience fit
- Objection pressure
- Brand risk

Expected outputs:

- ranking
- probability board
- sub-markets
- pairwise comparison
- spread / uncertainty
- audience-specific feedback
- objections and revision directions
- resolution-ready fields
- `ship / revise / kill`

## Rewrite direction

The rewrite is intentionally opinionated.

**Keep**

- multi-agent / multi-perspective review
- pairwise concept comparisons
- structured decision summaries

**Remove**

- Zep graph dependencies
- GraphRAG
- Twitter / Reddit world simulation
- long-running social environment modeling
- the broad "predict anything" framing

**Rebuild**

- audience panel
- pairwise judge engine
- campaign scoring
- probability aggregation
- sub-market evaluation
- resolution tracking
- judge calibration
- summary generation
- deeper calibration layers over time

## Current status

This repository is an **active public rewrite**.

The direction is clear, but the fork is still being tightened into a focused internal decision market. The current public branch should be read as:

> a Moody-facing internal decision market in transition, not a simple reskin of the original MiroFish.

The immediate priorities are:

1. align the public narrative with the real product direction
2. continue syncing code cleanup and evaluator-focused refactors
3. converge on a pre-launch campaign review workflow that is actually usable

## How to Try It

### Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend build (skip if using Docker) |
| Docker | Latest | Recommended deployment method |

### Option 1: Docker (Recommended)

```bash
# 1. Clone
git clone https://github.com/fantasyslr/MiroFishmoody.git
cd MiroFishmoody

# 2. Configure
cp .env.example .env
# Edit .env, set LLM_API_KEY (any OpenAI-compatible API)

# 3. Build and start
docker compose up -d --build

# 4. Open
# http://localhost:5001
```

### Option 2: Run from Source

```bash
# 1. Install backend dependencies
cd backend && pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env, set LLM_API_KEY

# 3. Start
python run.py
# http://localhost:5001
```

### Option 3: API Only

```bash
# Health check
curl http://localhost:5001/health
# {"service":"Campaign Ranker Engine","status":"ok"}

# Submit evaluation (async)
curl -X POST http://localhost:5001/api/campaign/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "campaigns": [
      {"name": "Plan A", "core_message": "Natural daily disposable color lenses", "product_line": "colored_lenses"},
      {"name": "Plan B", "core_message": "Silicone hydrogel high-oxygen tech", "product_line": "moodyplus"}
    ]
  }'
# Returns task_id and set_id

# Check progress
curl http://localhost:5001/api/campaign/evaluate/status/<task_id>

# Get results
curl http://localhost:5001/api/campaign/result/<set_id>

# Post-launch resolution (optional)
curl -X POST http://localhost:5001/api/campaign/resolve \
  -H "Content-Type: application/json" \
  -d '{"set_id": "<set_id>", "winner_campaign_id": "campaign_1", "actual_metrics": {"ctr": 0.03}}'

# View calibration status
curl http://localhost:5001/api/campaign/calibration
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_API_KEY` | Yes | LLM API key |
| `LLM_BASE_URL` | No | OpenAI-compatible endpoint (defaults to OpenAI) |
| `LLM_MODEL_NAME` | No | Model name (defaults to gpt-4o-mini) |
| `SECRET_KEY` | Recommended | Flask session secret |

See [DEPLOY.md](./DEPLOY.md) for full deployment guide, and [backend/QUICKSTART.md](./backend/QUICKSTART.md) for backend dev quickstart.

## Tech Stack

- **Backend**: Python 3.11+ / Flask / Gunicorn
- **Frontend**: React + Vite + TypeScript
- **Deployment**: Docker multi-stage build, single port 5001
- **LLM**: OpenAI-compatible API (Alibaba Bailian / Qwen / OpenAI)

## At A Glance

```mermaid
flowchart LR
  A["Campaign Concepts"] --> B["Audience Panel"]
  B --> C["Pairwise Judges"]
  C --> D["Probability Board"]
  D --> E["Sub-markets"]
  E --> F["Ship / Revise / Kill"]
  F --> G["Post-launch Resolution"]
  G --> H["Judge Calibration"]
```

This is not a one-shot scoring tool. It is an internal decision loop that turns opinions into probabilities, then later settles those probabilities against reality.

## Intended workflow

The long-term workflow is straightforward:

1. submit multiple campaign concepts
2. choose product line and target audience
3. run audience panel reviews
4. run pairwise judge comparisons
5. generate probability board, sub-markets, ranking, objections, and action recommendation
6. settle against real campaign results later for calibration

## Why crypto people will recognize this instantly

If you come from prediction markets, event pricing, trading, or odds culture, this project should feel familiar.

Because underneath, it is doing the same thing:

- stop asking "do you like this concept?"
- start asking "what probability would you actually assign to it?"
- stop producing opinions alone
- start producing `price`, `spread`, `edge`, and `resolution`

The only difference is that the thing being priced here is not an election, macro event, or token narrative. It is a **Moody campaign concept**.

## Why an e-commerce team can actually use it

For an e-commerce team, this is not just a more articulate creative-review bot. It is a way to structure early-stage decision-making before spend goes live.

It is useful for:

- filtering out obviously weak concepts before budget is spent
- identifying which angle deserves to be tested first
- decomposing "I think this will win" into smaller decision markets
- putting creative, media, brand, and landing-page judgment into the same decision surface

It does not replace real testing, but it should reduce the number of low-quality tests that ever reach paid media.

## Intended use cases

- Meta campaign angle pre-screening
- creative direction comparison
- landing page angle comparison
- influencer script review
- product-line-specific evaluation for `colored lenses` and `moodyPlus`

## What this is not

This should not be treated as:

- a profit prediction engine
- an attribution system replacement
- a media buying system
- a magical certainty machine

It is first and foremost a **better campaign selection tool / internal decision market**.

## Credits

- Original project: [MiroFish](https://github.com/666ghj/MiroFish)
- The original multi-agent simulation direction provided the starting point for this fork
- This new direction also draws direct inspiration from **crypto-native prediction markets, event contracts, and forecasting communities**
- Without the crypto habit of `pricing disagreement`, `finding edge`, and `settling against reality`, this direction would not exist
- This is also a direct acknowledgment of the broader players and communities that made market-style aggregation legible, including early prediction-market builders, crypto event-market participants, and the specific style of trading influence associated with figures like **SBF**
- What we borrow: `implied probability`, `sub-markets`, `resolution`, and `calibration`
- What we explicitly do **not** borrow: tokens, onchain trading, or public speculation markets

Future code and documentation updates will continue to narrow the repo around the **Moody Lenses internal decision market** direction.
