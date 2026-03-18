# Feature Research

**Domain:** Brand Campaign Pre-testing Tool — v2.1 Brief-Type-Aware Evaluation + Benchmark Dataset
**Researched:** 2026-03-18
**Confidence:** MEDIUM — weight proportions from industry research (WebSearch verified against multiple sources); benchmark schema from LLM evaluation literature (HIGH confidence for structure, MEDIUM for domain-specific field selection)

---

## Context: v2.1 Delta from v2.0

v2.0 ships: 9/8 persona pool, MultiJudge ensemble, devil's advocate, ConsensusAgent, cross-path badge, visual diagnostics.

v2.1 adds three things:
1. **Deployment fix** — static asset 404 on `/`, Railway/Docker migration
2. **Brief-type-aware evaluation** — weights differ by campaign objective (品牌/种草/转化)
3. **Benchmark dataset** — labeled historical examples to regression-test scoring accuracy

This FEATURES.md covers (2) and (3) only. Deployment is an ops concern, not a feature concern.

---

## Feature Landscape

### Table Stakes (Must Have for v2.1)

These are features where their absence makes the current evaluation system demonstrably wrong — not just incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Brief type field in campaign form** | Without knowing campaign objective, the evaluator cannot apply correct weights. A seeding brief scored with conversion weights will always rank wrong. | LOW | Add `brief_type: enum["brand", "seeding", "conversion"]` to the campaign submission form. Already have `category` field pattern to follow. |
| **Per-brief-type weight profiles** | Industry consensus: conversion campaigns weight ROAS/CVR 50-60%; brand campaigns weight storytelling/emotional resonance 40-50%; seeding campaigns weight content generation rate and authentic alignment 40-50%. Using a single flat weight across all three gives systematically wrong rankings. | MEDIUM | Implement as a `BriefTypeWeightProfile` config class. Store as YAML/JSON alongside persona configs. Follow existing PersonaRegistry DI pattern. |
| **Brief-type weights applied in BaselineRanker** | The Race path currently scores against ROAS/CVR/purchase_rate baselines uniformly. A brand campaign should be penalized less for low purchase_rate and more for low brand_recall proxy signals. | MEDIUM | BaselineRanker already accepts dimension configs. Add brief_type param that selects weight overrides before scoring. No schema change needed. |
| **Brief-type weights applied in EvaluationOrchestrator** | The Evaluate path must pass brief context to each persona judge. A "conversion" brief changes how a persona interprets "success" — "竹竹" cares about aspiration regardless, but her weight in the final score should shift based on brief type. | MEDIUM | Inject brief_type into persona system prompts and into final score aggregation. Two touch points: persona instructions + CampaignScorer aggregation weights. |
| **Brief type visible in result pages** | Users need to verify the brief type used in evaluation. Evaluating a brand campaign with conversion weights by mistake has no visible trace today. | LOW | Add brief_type badge to ResultPage header and exported PDF. Read from stored result JSON — no backend change if brief_type is stored in the result. |
| **Benchmark dataset schema** | Without labeled examples, there is no way to know if weight changes improve or regress accuracy. Any weight tuning is blind. The benchmark is the minimum verification infrastructure for the weight feature. | MEDIUM | See Benchmark Dataset Schema section below. |
| **Benchmark regression test runner** | A script that loads the benchmark dataset and checks whether the current evaluator produces the expected winner for each labeled example. Reports hit rate (% correct). | LOW | Single Python script. No UI needed. Run in CI or manually before releases. |

### Differentiators (v2.1 Specific Value)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Weight transparency panel** | Show the brand team which dimensions drove the final ranking and what weight each carried. "Plan A won because visual-brand-fit (weight 0.35) was 8.2 vs Plan B's 6.1" is actionable. "Plan A scored 87" is not. | MEDIUM | Backend already has per-dimension scores. Add weight × score breakdown to result detail view. Collapsible panel, not front-and-center. |
| **Brief-type calibration history** | Over time, track whether brief-type-A evaluations that scored "Plan X winner" were validated by real performance. This closes the feedback loop. | HIGH | Requires real-outcome capture (post-campaign ROAS/CTR linkage). Long-term only. Include in benchmark schema but don't build UI yet. |
| **Benchmark hit rate in admin dashboard** | The admin user can see current model hit rate against benchmark — e.g., "brand brief: 78%, seeding brief: 65%, conversion brief: 82%". Reveals which brief type needs better calibration. | LOW | Read from benchmark runner output. Static JSON → dashboard chart. |

### Anti-Features (Do Not Build in v2.1)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Fully separate evaluation pipelines per brief type** | "Brand campaigns are so different they need a different model" | Creates 3x maintenance burden. The personas and judges are already differentiated enough; the only variable is the weight profile. Separate pipelines mean 3x bugs, 3x tests, 3x config drift. | Single pipeline, injected weight profile. The `BriefTypeWeightProfile` abstraction handles all variation without code duplication. |
| **LLM-inferred brief type** | "Let the AI figure out the brief type from the description" | LLM inference of intent is unreliable and adds latency + cost. A 2-second form field is more reliable than a prompt that may miscategorize. Wrong brief-type detection silently corrupts all evaluation scores. | Explicit user selection in form. Add validation: brief_type required before submit. |
| **Sub-brief-types (e.g., awareness vs recall within brand)** | "Brand campaigns have sub-goals too" | v2.1 has 3 categories; more granularity requires more labeled examples to validate. With no ground truth data yet, sub-types would be invented weights with no verification path. | Start with 3 types. After benchmark dataset is built and hit rates are measured, add sub-types only where hit rate is low and sub-type separation would logically help. |
| **Automatic weight optimization via ML** | "Train on benchmark data to find optimal weights" | 20-50 labeled examples (realistic benchmark size) is far too small for ML-derived weights to beat expert-designed weights. Risk: overfitting to benchmark, failing on real campaigns. | Expert-designed weights from industry research, validated against benchmark hit rate. Revisit when benchmark reaches 200+ examples. |

---

## Brief Type Weight Profiles

Research synthesis from multiple industry sources (MEDIUM confidence — cross-verified against Adstellar, SmartInsights, Motimatic KPI frameworks):

### Brand Campaign (品牌向)

Objective: Build brand equity, establish positioning, increase aided/unaided recall.

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| Visual brand consistency | 0.25 | Brand campaigns live or die on visual coherence with existing brand system |
| Emotional resonance | 0.25 | Brand recall is driven by emotional association, not rational argument |
| Storytelling quality | 0.20 | Narrative-structured messaging improves brand attitude 38% vs feature-based (ISO 20671 data) |
| Audience-brand fit | 0.15 | Target affinity with Moody's aesthetic/value positioning |
| Conversion signal | 0.05 | Deliberately low — brand campaigns are not optimized for immediate purchase |
| Competitive differentiation | 0.10 | Does this campaign make Moody visually distinct from ACUVUE/Bausch&Lomb? |

### Seeding Campaign (种草向)

Objective: Generate authentic content, seed consideration, build social proof.

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| Content authenticity | 0.30 | Seeding fails when it reads as advertising. Authenticity is the product. |
| Audience-creator fit | 0.25 | Will the target creator persona genuinely post this? Misfit = zero content generation rate. |
| Visual shareability | 0.20 | Content must work in feed context (not in-ad context). Thumb-stop, repost potential. |
| Emotional resonance | 0.15 | Engagement > reach in seeding; emotional hooks drive comments/saves |
| Brand consistency | 0.05 | Deliberately low — seeding allows more creative latitude than brand campaigns |
| Conversion signal | 0.05 | Seeding is top-of-funnel; conversion measurement is lagged and indirect |

### Conversion Campaign (转化向)

Objective: Drive purchase, maximize ROAS/CVR, capture bottom-of-funnel intent.

| Dimension | Weight | Rationale |
|-----------|--------|-----------|
| Purchase intent signal | 0.30 | Does the visual/copy create urgency and a clear reason to buy now? |
| Product clarity | 0.25 | Conversion ads must communicate product benefit unambiguously within 3 seconds |
| CTA effectiveness | 0.20 | Is there a clear, low-friction call to action? |
| Audience targeting fit | 0.15 | Conversion campaigns waste budget on mismatched audiences more than brand campaigns do |
| Brand consistency | 0.05 | Lower weight — conversion campaigns can deviate from brand aesthetic for performance |
| Storytelling quality | 0.05 | Lower weight — narrative structure matters less when the goal is immediate action |

**Implementation note:** These weights should be stored as YAML config, not hardcoded. The brand team must be able to adjust them after seeing benchmark hit rates.

---

## Benchmark Dataset Schema

Research basis: LLM evaluation literature (Kili Technology, Maxim AI, LitBench methodology, evidentlyai). MEDIUM-HIGH confidence — these patterns are well-established for domain-specific LLM evaluation.

### What a Good Benchmark Dataset Contains

A benchmark for campaign evaluation needs:
1. **Inputs** — the same data the evaluator receives (brief, visual descriptions, campaign metadata)
2. **Expected output** — human-expert-labeled winner + ranking
3. **Outcome linkage** — actual post-campaign performance (where available), for long-term calibration
4. **Metadata** — enough to slice results by brief type, category, recency

### Minimum Required Fields per Example

```json
{
  "example_id": "bm_2025_q4_001",
  "brief_type": "brand | seeding | conversion",
  "category": "moodyPlus | colored_lenses",
  "campaign_name": "string (may be anonymized)",
  "evaluation_date": "ISO 8601",

  "plans": [
    {
      "plan_id": "A",
      "plan_name": "string",
      "visual_description": "string — what the image shows (for text-only benchmark runs)",
      "image_path": "optional — relative path to image file",
      "brief_description": "string — plan's approach to the brief"
    }
  ],

  "ground_truth": {
    "winner": "A | B | C ...",
    "ranking": ["A", "C", "B"],
    "labeled_by": "string — role of labeler (e.g., brand_director)",
    "label_confidence": "high | medium | low",
    "label_rationale": "string — why this plan won (required for high-confidence labels)"
  },

  "outcome": {
    "available": true,
    "winner_actual": "A | B | null",
    "roas_delta": "float | null — relative ROAS of labeled winner vs alternatives",
    "cvr_delta": "float | null",
    "outcome_source": "string — where this data came from"
  },

  "tags": ["string"],
  "notes": "string"
}
```

### Minimum Dataset Size for Useful Hit Rate Measurement

| Size | What You Can Do | Confidence Level |
|------|-----------------|-----------------|
| 10-20 examples | Sanity check only. Can detect catastrophic failures. | LOW |
| 20-50 examples | Per-brief-type breakdown starts to be meaningful. Spot-check calibration. | MEDIUM |
| 50-100 examples | Weight tuning is defensible. Can run A/B test of weight profiles. | MEDIUM-HIGH |
| 100+ examples | ML-based weight optimization becomes viable. Cross-validation possible. | HIGH |

**Recommendation for v2.1:** Target 30 labeled examples minimum before shipping brief-type weights to production. Even 30 examples — roughly 10 per brief type — gives the brand team a falsifiable hit rate number rather than "we think this is better."

### Annotation Guidelines (Required for Label Consistency)

Labels are only useful if consistently applied. Minimum annotation guidelines:

1. **Winner = the plan you would recommend to leadership** given the stated brief. Not "which image is prettier" — which plan best serves the objective.
2. **Brief type determines the evaluation lens.** Label a seeding plan by seeding criteria, not by whether you personally like the product.
3. **Label confidence = high** only when the winner is clear to any senior marketer. If two plans are tied, label confidence = low and note it.
4. **Image availability.** If images are available, the labeler must view them before labeling. Text-only labels are acceptable only as a fallback, and must be tagged `text_only: true`.
5. **Outcome data.** Attach actual performance data whenever it exists. This is the only ground truth that beats expert opinion.

---

## Feature Dependencies

```
[Brief type field in form]
    └──required by──> [Per-brief-type weight profiles]
    └──required by──> [BaselineRanker weight injection]
    └──required by──> [EvaluationOrchestrator weight injection]
    └──required by──> [Brief type in result/export]

[Benchmark dataset (manually labeled)]
    └──required by──> [Benchmark regression test runner]
    └──required by──> [Hit rate in admin dashboard]
    └──enables──> [Weight profile validation]
    └──enables (long-term)──> [Brief-type calibration history]

[BaselineRanker weight injection]
    └──independent from──> [EvaluationOrchestrator weight injection]
    (Race and Evaluate paths can be migrated independently)

[Weight transparency panel]
    └──requires──> [per-dimension scores with weights stored in result JSON]
    (backend already has scores; needs weight metadata added to output)
```

### Dependency Notes

- **Brief type field is the v2.1 gate.** Every other feature in this milestone depends on it. Ship it first, wire backend after.
- **Benchmark and weight injection are independent.** You can build the benchmark dataset in parallel while developing the weight profiles. The benchmark validates the weights, but building the benchmark does not block building the weights.
- **BaselineRanker and EvaluationOrchestrator are decoupled.** Race path and Evaluate path weighting can be migrated one at a time. Start with EvaluationOrchestrator (Evaluate path) because it has more dimensions to weight.

---

## MVP Definition for v2.1

### Ship in v2.1 (Brief-Type Evaluation)

- [ ] **Brief type field** — add `brief_type` to campaign form, required field, enum validation
- [ ] **BriefTypeWeightProfile config** — YAML-based weight profiles for 3 brief types, loaded via registry pattern
- [ ] **EvaluationOrchestrator weight injection** — brief_type param passed through to score aggregation
- [ ] **BaselineRanker weight injection** — brief_type selects dimension weight override in Race path
- [ ] **Brief type visible in result** — badge on ResultPage and in PDF export
- [ ] **Benchmark dataset seed** — 10-30 labeled examples in `/backend/benchmark/` as JSON, created by brand team
- [ ] **Benchmark runner script** — `python benchmark/run.py` outputs hit rate by brief type

### Defer to v2.2

- [ ] **Weight transparency panel** — UI breakdown of weight × score. Useful but not blocking.
- [ ] **Benchmark hit rate in admin dashboard** — nice-to-have; runner script is sufficient for v2.1
- [ ] **Brief-type calibration history** — requires post-campaign outcome collection pipeline. Long-term.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Brief type form field | HIGH (gates entire feature) | LOW | **P1** |
| BriefTypeWeightProfile config | HIGH | LOW-MEDIUM | **P1** |
| EvaluationOrchestrator weight injection | HIGH | MEDIUM | **P1** |
| BaselineRanker weight injection | MEDIUM | MEDIUM | **P1** |
| Brief type in result/export | MEDIUM | LOW | **P1** |
| Benchmark dataset (manual labeling) | HIGH (verification) | MEDIUM (human time) | **P1** |
| Benchmark runner script | HIGH (regression safety) | LOW | **P1** |
| Weight transparency panel | MEDIUM | MEDIUM | **P2** |
| Benchmark hit rate dashboard | LOW | LOW | **P2** |
| Brief-type calibration history | HIGH (long-term) | HIGH | **P3** |

---

## Sources

- [Adstellar: Meta Campaign Performance Scoring — weighted KPI framework](https://www.adstellar.ai/blog/meta-campaign-performance-scoring)
- [SmartInsights: Brand Evaluation and Marketing KPIs Beyond a Single Campaign Metric](https://www.smartinsights.com/goal-setting-evaluation/goals-kpis/kpis-measuring-brand-marketing/)
- [Motimatic: KPIs in Digital Marketing — Brand Awareness vs Lead Generation](https://motimatic.com/industry/other/kpis-in-digital-marketing/)
- [Nepa: Campaign Evaluation — Measuring True Impact](https://nepa.com/blog/campaign-evaluation-measuring-true-impact-and-maximizing-marketing-roi/)
- [MightyScout: Ultimate Guide to Influencer Marketing KPIs 2025](https://mightyscout.com/blog/the-ultimate-guide-to-influencer-marketing-kpis)
- [Sprout Social: Influencer Marketing KPIs](https://sproutsocial.com/insights/influencer-marketing-kpis/)
- [Maxim AI: Building a Golden Dataset for AI Evaluation](https://www.getmaxim.ai/articles/building-a-golden-dataset-for-ai-evaluation-a-step-by-step-guide/)
- [Kili Technology: How to Build LLM Evaluation Datasets for Domain-Specific Use Cases](https://kili-technology.com/large-language-models-llms/how-to-build-llm-evaluation-datasets-for-your-domain-specific-use-cases/)
- [LitBench: A Benchmark and Dataset for Reliable Evaluation of Creative Writing (arXiv 2507.00769)](https://arxiv.org/abs/2507.00769) — benchmark methodology for subjective creative evaluation
- [evidentlyai: LLM-as-a-Judge Complete Guide](https://www.evidentlyai.com/llm-guide/llm-as-a-judge)
- [Keylabs AI: Creating Reliable Benchmark Datasets — Gold Standard](https://keylabs.ai/blog/creating-reliable-benchmark-datasets-gold-standard-data-for-model-evaluation/)
- ISO 20671 brand evaluation framework — storytelling dimension weighting basis (referenced via SmartInsights)

---

*Feature research for: MiroFishmoody v2.1 — Brief-Type-Aware Evaluation + Benchmark Dataset*
*Researched: 2026-03-18*
