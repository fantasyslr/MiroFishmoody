# Feature Research

**Domain:** Brand Campaign Pre-testing / 推演 (Internal Tool) — v2.0 Frontend Rewrite + Multi-Agent Backend
**Researched:** 2026-03-18
**Confidence:** HIGH — based on direct reading of existing codebase (all 10 frontend pages + 20 backend services), MiroFish upstream repo analysis, and peer-reviewed 2025 research on multi-agent LLM evaluation

---

## Context: What v1.1 Already Ships

Before mapping new features, the baseline matters. All items below are **already built and working**:

| Capability | Status |
|-----------|--------|
| Race path: baseline ranking + visual analysis + quick ranking | Done |
| Evaluate path: persona panel scoring + pairwise comparison + BT ranking | Done |
| Both mode (Race + Evaluate combined, async) | Done |
| Per-category personas (moodyPlus 6, colored_lenses 5) | Done |
| Image upload + multimodal analysis (parallel, Semaphore-controlled) | Done |
| PairwiseJudge with 3 judge perspectives (策略/用户/品牌) + position-swap debiasing | Done |
| PDF/image export (html2canvas + jsPDF) | Done |
| Version iteration + comparison | Done |
| Trends dashboard (recharts, by category) | Done |
| Auth (login/logout/role) | Done |

v2.0 is **not a greenfield build**. It is a targeted rewrite of the frontend interaction layer and a precision enhancement of the multi-agent evaluation engine.

---

## Feature Landscape

### Table Stakes (Must Have for v2.0)

Features where the current implementation has known bugs, interaction logic failures, or UX gaps that block real usage. These are the reasons v2.0 exists.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Form state persists through navigation** | Users fill in 5 plans with images, click submit, something fails, they navigate back — they expect the form to still be there | MEDIUM | Current: `useState` initializes fresh on every mount. Fix: sessionStorage or React context persistence across navigation |
| **Image upload status is honest** | Users need to know if images are "ready" before submitting. Current status indicators have race conditions with React StrictMode double-fire | MEDIUM | `startedRef` guard already in RunningPage for StrictMode — same pattern needed everywhere image state is mutated async |
| **Progress page does not poll blindly** | Evaluate path shows static step animation while polling every 3s. If network drops, user sees spinner forever | LOW | Add timeout + visible error recovery. RunningPage already shows error state for Race; EvaluatePage needs same treatment |
| **Both mode: evaluate link is clickable only when ready** | In Both mode, ResultPage shows "查看深度评审" button that appears when polling completes. If eval fails, this link should show failure — not just disappear | LOW | Current code already handles `evalStatus: 'failed'` but UI text and visibility need clarity |
| **Version iterate flow is complete end-to-end** | "基于上一版本迭代" banner appears on HomePage when iterateState exists. But Race→Evaluate cross-mode parentSetId is not passed (known debt: `parent_set_id` empty in Race-then-Evaluate flow) | MEDIUM | Fix: when Both mode completes, capture the eval setId and surface it for next iteration |
| **Result page does not require manual tab switching** | Current EvaluateResultPage has 3 tabs (排名/人格/对比). Users may miss the 人格 tab details. The most important finding (winner + reasons) must be visible without clicking | LOW | Restructure: show winner prominently, collapse others behind toggle |
| **Export works on all result types** | Export buttons exist on both ResultPage and EvaluateResultPage. html2canvas sometimes clips content or produces blank PDFs on large result sets | MEDIUM | Test with real 5-plan result sets. May need scroll-capture or page-break logic |
| **Category selector drives visible persona list** | Users select "彩片" but have no confirmation which personas will evaluate them. They should see the persona set before submitting | LOW | Add persona preview in the right-panel "评估矩阵" sidebar before submission |

### Differentiators (Multi-Agent Accuracy Enhancement)

Features that move the evaluation engine from "one LLM pretending to be 5 different people" to "genuinely independent signal sources that catch each other's errors."

Research basis: 2025 literature consistently shows multi-agent debate and panel approaches improve accuracy 8-20 percentage points over single-judge evaluation, with the largest gains in domains requiring nuanced judgment (exactly our case — brand aesthetics, audience resonance).

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Cross-persona disagreement surfacing** | When personas disagree strongly (e.g., moodyPlus "科学派" loves a rational claim, "美感派" rejects the same visual), this disagreement is more informative than the averaged score. Currently averaged away silently. | MEDIUM | Backend already has per-persona scores. Add disagreement_score = std dev of persona scores. Surface in UI as "争议方案" badge when std dev > threshold |
| **Devil's advocate judge in pairwise** | Current 3-judge pairwise (策略/用户/品牌) votes by majority. Add a 4th judge with explicit adversarial role: "你的工作是找到多数评委忽略的风险或被高估的优点" — prevents groupthink convergence | MEDIUM | Add `devil_advocate` perspective to JUDGE_PERSPECTIVES in pairwise_judge.py. Mark its dissenting votes separately so UI can show "少数意见" |
| **Inconsistency detection between Race and Evaluate** | When Both mode runs, Race ranks plan A first, Evaluate ranks plan B first. This contradiction is currently invisible. It is actually the most valuable signal ("your historical data says A, but independent judges say B — investigate why"). | MEDIUM | In ResultPage Both mode: add cross-path consistency badge. Show explicitly when Race winner != Evaluate winner and flag for review |
| **Persona confidence flagging** | LLM outputs a score of 7/10 but its reasoning text contradicts the score ("this would not resonate with me... 7/10"). Current code trusts the JSON number. Add a pass checking score vs reasoning semantic alignment. | HIGH | Use a second LLM call (cheaper/faster model) to verify score-reasoning alignment. Flag low-confidence evaluations in UI. This is the "meta-judge" pattern from 2025 literature |
| **Expanded pairwise judge perspectives** | Current 3 judges (strategist, consumer, brand guardian) all evaluate from Moody's existing brand frame. Add: "竞品视角" — assumes the evaluator is a Acuvue/Bausch&Lomb brand manager assessing threat level. This surfaces competitive differentiation gaps. | LOW | Add 1-2 more JUDGE_PERSPECTIVES entries. Minimal code change, high signal value for brand team |
| **Calibrated scoring against historical winners** | All persona scores are relative to each other, not anchored to real-world outcomes. If campaign X was a historical top performer (high ROAS), and current personas gave it 6/10, there's a calibration gap. Use JudgeCalibration service (already exists) to apply learned weights. | HIGH | JudgeCalibration.get_weights() already called in orchestrator but weights are likely not trained on real data yet. Needs historical outcome data pipeline |

### Anti-Features (Deliberately NOT Build in v2.0)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Full Vue.js → React rewrite mirroring MiroFish exactly** | "MiroFish frontend patterns" sounds like "copy their code" | MiroFish is a Vue.js simulation platform for thousands of agents. Its UI patterns (knowledge graph visualization, real-time agent chat, simulation state) are completely inapplicable to a 5-plan campaign evaluation tool. Taking UI patterns from MiroFish means misreading the task. | Rewrite React frontend to fix current bugs and improve interaction clarity. MiroFish's value is its multi-agent backend architecture concept, not its Vue components. |
| **Full LLM orchestration rewrite (LangChain/LangGraph)** | "Add more agents = need orchestration framework" | Current ThreadPoolExecutor + custom services works and is debuggable. LangChain adds abstraction overhead, version churn, and debugging difficulty for marginal gains. The team already knows Flask services. | Add agents by extending existing service classes. EvaluationOrchestrator already coordinates phases correctly — extend it, don't replace it. |
| **Thousands of agents (MiroFish simulation scale)** | "More agents = better accuracy" is a common extrapolation | 2025 research shows gains plateau after 3-5 diverse agents. Beyond that, cost and latency grow linearly while accuracy gains are marginal. MiroFish's "thousands of agents" is designed for macro social simulation, not per-campaign evaluation. | 5-7 well-differentiated agents (current 6 personas + 3 judges + 1 devil's advocate = already near optimal). Focus on quality of disagreement, not quantity. |
| **Real-time agent chat interface** | MiroFish has interactive "chat with agents" feature — seems valuable | Campaign evaluation is async batch, not interactive. Adding chat would require stateful agent sessions, session storage, and a fundamentally different UX model. The brand team wants a result PDF, not a conversation. | After evaluation completes, show "follow-up questions" as expandable pre-baked responses from each persona (e.g., "竹竹的具体担忧是什么?" → shows stored objections). Zero added complexity. |
| **GraphRAG knowledge graph visualization** | MiroFish shows entity relationship graphs — looks impressive | This is for exploring multi-agent simulation state. For campaign evaluation, the "knowledge graph" would be personas knowing each other... which adds nothing actionable. | Clean tabular persona scores + radar chart is clearer and faster to interpret than a graph visualization. |
| **Realtime collaboration / multi-user editing** | "Multiple team members should work on the same campaign" | Internal tool with sequential workflow. simultaneous editing creates race conditions in evaluation state (already managed with threading.Lock). | One user submits evaluation, shares exported PDF in meeting. If needed, add read-only result sharing link (trivial to implement) as v2.x. |

## Feature Dependencies

```
[Frontend interaction fixes] — no backend deps, can ship independently
    └──enables──> [Stable form state]
    └──enables──> [Honest async feedback]
    └──enables──> [Both-mode cross-path surfacing]

[Cross-persona disagreement surfacing]
    └──requires──> [per-persona scores in API response] (already in backend)
    └──enables──> [Calibrated scoring]

[Devil's advocate judge]
    └──requires──> [pairwise_judge.py JUDGE_PERSPECTIVES extension]
    └──independent──> (no frontend changes needed for backend addition)
    └──enables──> [UI: 少数意见 badge] (optional frontend)

[Race + Evaluate cross-path inconsistency detection]
    └──requires──> [Both mode result storage] (already exists)
    └──requires──> [Frontend ResultPage change only]

[Persona confidence flagging]
    └──requires──> [Secondary LLM verification call]
    └──requires──> [Score-reasoning extraction from panel output]
    └──HIGH COST — defer unless accuracy gap proven

[Calibrated scoring against historical winners]
    └──requires──> [JudgeCalibration training data pipeline]
    └──requires──> [Historical outcome → score mapping]
    └──HIGH COST — long-term only
```

### Dependency Notes

- **Frontend fixes are independent of backend**: All frontend table stakes can be shipped without touching any backend service. This is a clean separation.
- **Devil's advocate is backend-only first**: Add the judge perspective in pairwise_judge.py. The frontend can display it without code changes (votes already shown per-judge). Frontend badge is an enhancement, not a requirement.
- **Cross-path inconsistency requires zero backend changes**: Both-mode already stores Race result AND Evaluate result. This is purely a ResultPage UI computation.
- **Confidence flagging is the most expensive feature**: Requires a second LLM call per persona score. At 6 personas × N campaigns × secondary call, this doubles LLM cost. Only do this if users report trusting wrong scores.

## MVP Definition for v2.0

### Ship in v2.0 Phase 1: Frontend Rewrite

These are interaction fixes with no backend dependency. Can be developed, tested, and shipped independently.

- [ ] **Form state persistence across navigation** — sessionStorage save/restore of HomePage state
- [ ] **Timeout + recovery on Evaluate polling** — prevents infinite spinner
- [ ] **Both mode: cross-path consistency badge** — zero backend work, high signal value
- [ ] **Category selector shows persona preview** — add persona names/count to sidebar before submit
- [ ] **Result page: winner-first layout** — restructure EvaluateResultPage to show top campaign without requiring tab navigation
- [ ] **Export reliability** — test + fix html2canvas PDF generation on full result sets
- [ ] **Race→Evaluate parentSetId fix** — pass setId correctly in Both mode for version chain

### Ship in v2.0 Phase 2: Multi-Agent Enhancement

Backend extensions that increase evaluation signal quality.

- [ ] **Cross-persona disagreement score** — std dev of persona scores, surfaced as "争议" badge
- [ ] **Devil's advocate judge perspective** — add to JUDGE_PERSPECTIVES, mark dissenting votes
- [ ] **Expanded pairwise perspectives (+1 竞品视角)** — extend judge set for brand differentiation signal

### Defer to v2.x: High-Cost Features

Only build if specific need is validated.

- [ ] **Persona confidence flagging** — defer until users report score-reasoning contradictions
- [ ] **Calibrated scoring against historical winners** — defer until historical outcome data is systematically captured and linked to evaluation results

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Form state persistence | HIGH (prevents lost work) | LOW | **P1** |
| Evaluate polling timeout/recovery | HIGH (prevents stuck UI) | LOW | **P1** |
| Both mode cross-path inconsistency badge | HIGH (new insight) | LOW (frontend only) | **P1** |
| Winner-first result layout | MEDIUM | LOW | **P1** |
| Export reliability fix | MEDIUM | MEDIUM | **P1** |
| Category → persona preview | MEDIUM | LOW | **P2** |
| Race→Evaluate parentSetId fix | MEDIUM | LOW | **P2** |
| Cross-persona disagreement score | HIGH (new signal) | MEDIUM | **P2** |
| Devil's advocate judge | HIGH (reduces groupthink) | LOW (backend only) | **P2** |
| Expanded pairwise perspectives | MEDIUM | LOW | **P2** |
| Persona confidence flagging | MEDIUM | HIGH (2x LLM cost) | **P3** |
| Calibrated scoring (historical) | HIGH (long-term) | HIGH | **P3** |

**Priority key:**
- P1: Ship in v2.0 Phase 1 (frontend rewrite)
- P2: Ship in v2.0 Phase 2 (multi-agent enhancement)
- P3: Validated need required before building

## What "MiroFish Frontend Patterns" Actually Means for This Project

The MiroFish upstream repo (https://github.com/666ghj/MiroFish) is a **Vue.js multi-agent simulation platform** for macro social simulation (policy testing, financial forecasting, public opinion modeling via thousands of agents with emergent behavior). Its frontend interaction patterns are:

1. Upload seed materials (documents, narratives)
2. Query in natural language
3. Watch real-time simulation unfold (knowledge graph, agent interactions)
4. Chat with individual simulated agents
5. Read ReportAgent synthesis

**None of these patterns map directly to campaign evaluation.** The "MiroFish frontend rewrite" in PROJECT.md means: use MiroFish's multi-agent evaluation *philosophy* (diverse agent perspectives, emergent disagreement as signal, structured consensus) to redesign the frontend to correctly surface what the backend already produces.

The valuable translation is:

| MiroFish concept | MiroFishmoody v2.0 equivalent |
|------------------|-------------------------------|
| Thousands of agents with distinct personalities | 6 personas (moodyPlus) / 5 personas (colored_lenses) with brand-specific evaluation focus |
| Emergent disagreement as signal | Cross-persona std dev surfaced as "争议" badge |
| ReportAgent synthesis | SummaryGenerator structured output |
| Agent chat for verification | Pre-baked persona objections expandable in result view |
| Real-time simulation progress | Async task polling with honest stage display |

## Sources

- Direct codebase analysis: `/Users/slr/MiroFishmoody/frontend/src/pages/` (all 10 pages)
- Direct codebase analysis: `/Users/slr/MiroFishmoody/backend/app/services/` (all 20 services)
- [MiroFish upstream README-EN](https://github.com/666ghj/MiroFish/blob/main/README-EN.md) — multi-agent architecture description
- [Multi-LLM-Agents Debate — Performance, Efficiency, and Scaling Challenges (ICLR 2025)](https://d2jud02ci9yv69.cloudfront.net/2025-04-28-mad-159/blog/mad/) — debate scaling results
- [Judging the Judges: A Systematic Study of Position Bias in LLM-as-a-Judge (ACL 2025)](https://aclanthology.org/2025.ijcnlp-long.18/) — position bias mechanics and majority vote mitigation
- [ChatEval: Towards Better LLM-based Evaluators through Multi-Agent Debate (Semantic Scholar)](https://www.semanticscholar.org/paper/ChatEval:-Towards-Better-LLM-based-Evaluators-Chan-Chen/ec58a564fdda29e6a9a0a7bab5eeb4c290f716d7) — multi-agent debate evaluation framework
- [Adversarial Multi-Agent Evaluation of LLMs through Iterative Debates (arXiv 2410.04663)](https://arxiv.org/html/2410.04663v1) — devil's advocate patterns
- [Orq.ai: Comprehensive Guide to Evaluating Multi-Agent LLM Systems](https://orq.ai/blog/multi-agent-llm-eval-system) — ensemble patterns
- [Beyond Consensus: Mitigating Agreeableness Bias in LLM Judge Evaluations (NUS 2025)](https://aicet.comp.nus.edu.sg/wp-content/uploads/2025/10/Beyond-Consensus-Mitigating-the-agreeableness-bias-in-LLM-judge-evaluations.pdf) — agreeableness bias mitigation

---
*Feature research for: MiroFishmoody v2.0 — Frontend Rewrite + Multi-Agent Enhancement*
*Researched: 2026-03-18*
