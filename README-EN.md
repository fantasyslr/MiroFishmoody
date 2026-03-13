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

## Intended workflow

The long-term workflow is straightforward:

1. submit multiple campaign concepts
2. choose product line and target audience
3. run audience panel reviews
4. run pairwise judge comparisons
5. generate probability board, sub-markets, ranking, objections, and action recommendation
6. settle against real campaign results later for calibration

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
