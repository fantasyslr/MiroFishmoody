# Feature Research

**Domain:** Brand Campaign Pre-testing / 推演 (Internal Tool for Beauty/Contact Lens Brand)
**Researched:** 2026-03-17
**Confidence:** MEDIUM — based on competitive landscape analysis of Kantar, Zappi, System1, Behavio, and emerging AI synthetic audience tools; contextualized for internal brand tool (not SaaS product)

## Feature Landscape

### Table Stakes (Users Expect These)

Features that brand/creative/media teams assume a campaign pre-testing tool has. Missing any of these makes the tool feel broken or useless.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **多方案并排对比** (Side-by-side comparison) | 推演的核心目的就是对比方案优劣，没有对比等于没有推演 | MEDIUM | Race 路径已有排名输出，但缺少直观的视觉并排对比 UI。Evaluate 路径无前端。这是最高优先级 gap |
| **多维度评分 + 总分** (Multi-dimensional scoring with composite) | 品牌/创意/媒介各关注不同维度（视觉吸引力、品牌契合度、受众共鸣），只给一个总分不够 | LOW | 已有视觉分析多维度评分 + Bradley-Terry 总分。需要让维度在 UI 上清晰可读、可展开 |
| **视觉素材分析** (Visual creative analysis) | 隐形眼镜 campaign 以 KV/模特图/产品图为核心，不分析视觉就等于没分析 | LOW | 已实现（ImageAnalyzer + LLM vision）。属于已有能力，继续打磨 |
| **历史基线对比** (Historical benchmark) | "这个方案比以前的好还是差？" 是最自然的问题 | LOW | BaselineRanker 已有。需要在结果页面清晰展示 percentile 和历史分位 |
| **结果可导出** (Exportable results) | 推演结果需要带进会议、汇报给老板。PDF/截图/PPT 是刚需 | MEDIUM | 当前无导出功能。至少需要 PDF 或可截图的结果卡片式布局 |
| **推演速度 < 5 分钟** (Results in under 5 minutes) | Kantar LINK AI 15 分钟出结果已成行业标杆。内部工具必须更快 | MEDIUM | 当前串行分析慢。并行图片分析 + 缓存已在 Active backlog |
| **按品类区分推演逻辑** (Category-specific evaluation) | 透明片和彩片的用户画像、审美偏好、购买动机完全不同 | MEDIUM | 已在 Active backlog（按品类配置评审人格）。这是 Moody 场景下的 table stakes |

### Differentiators (Competitive Advantage)

Features that让 MiroFishmoody 超越 "把结果贴进 PPT" 的手动流程，且是 Kantar/Zappi 这类 SaaS 不会为单个品牌定制的能力。

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **AI 合成受众评审团** (Synthetic audience panel) | 业界 2025-2026 热点方向。用 LLM 模拟目标消费者人格做推演，无需招募真人 panel，成本从万元级降到接近零 | MEDIUM | 已有 5-persona AudiencePanel + PairwiseJudge。这是核心差异化能力，继续深化人格精准度和品类适配 |
| **双路径推演** (Dual-path: Race + Evaluate) | 快速筛选 vs 深度分析两种模式，匹配不同决策场景。竞品通常只提供单一流程 | LOW | 已有双路径后端。需要统一入口 UI 让用户自然选择 |
| **品牌认知状态模型** (Brand state cognitive model) | 将品牌当前认知状态（awareness/consideration/purchase stage）纳入推演，不只看素材好不好，还看是否匹配品牌当前阶段需求 | HIGH | BrandStateEngine 已有但是 God class。这个能力在竞品中极少见，是真正的壁垒 |
| **推演结果趋势追踪** (Campaign simulation history & trends) | 跨 campaign 追踪推演分数变化，让团队看到创意水平是否在提升 | MEDIUM | 当前每次推演独立，无跨 campaign 趋势视图。需要 dashboard |
| **视觉诊断建议** (Actionable visual diagnostics) | 不只是打分，还要给出"为什么扣分、怎么改"的建议。Kantar 和 System1 都强调 actionable recommendations | MEDIUM | ImageAnalyzer 已输出文本分析，但需要结构化诊断建议（如"模特表情不够自然，建议..."） |
| **受众人格自定义** (Customizable audience personas) | 让品牌团队根据具体 campaign 目标自定义评审人格（如"Z 世代彩妆重度用户" vs "30+ 职场女性"） | HIGH | 当前人格写死在代码里。开放配置 = 更多场景适用性 |
| **方案迭代推演** (Iterative refinement tracking) | 同一 campaign 多次推演（修改素材后重新推演），自动对比版本间改善 | MEDIUM | 当前无版本概念。需要 campaign revision tracking |

### Anti-Features (Deliberately NOT Build)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **真人消费者 panel 调研** | "AI 打分不够真实，要真人投票" | 成本高、速度慢、招募难。内部工具不是调研平台。Moody 已有独立调研流程 | 持续优化 AI 合成人格的精准度，用历史 campaign 数据校准 |
| **实时 A/B 投放测试** | "直接连广告平台跑 A/B test" | 超出推演工具范畴，涉及广告账户、预算、投放优化等完全不同的领域 | 推演结果导出为决策报告，投放由媒介团队在广告平台执行 |
| **视频/GIF 素材分析** | "我们也有视频素材要测" | 视频分析成本高（LLM vision 按帧计费）、技术复杂度指数级增长 | 先用静态帧截图做推演，未来 v2+ 再考虑视频 |
| **AI 自动生成创意素材** | "既然有 AI 评分，不如让 AI 直接生成更好的" | 与推演工具定位不同（评估 vs 生成）。生成质量不可控，品牌调性难保证 | 聚焦推演 + 诊断建议，让设计师基于反馈人工迭代 |
| **眼动追踪/注意力热力图** | "Brainsight 和 Neurons 都有热力图" | 需要专门的注意力预测模型（非通用 LLM 能力），训练成本和数据依赖极高 | 用 LLM vision 的视觉分析（构图、色彩、焦点）作为近似替代 |
| **跨渠道投放效果预测** | "预测在小红书 vs 抖音 vs 微博的效果差异" | 需要各平台历史投放数据和算法模型，远超当前数据基础 | 推演聚焦素材本身的品牌力/吸引力，平台效果差异由媒介团队基于经验判断 |

## Feature Dependencies

```
[按品类配置评审人格]
    └──requires──> [品类选择 UI]（已有）
                       └──enables──> [受众人格自定义]

[Evaluate 路径前端]
    └──requires──> [修复图片静默失效 bug]
    └──enables──> [多方案并排对比 UI]

[多方案并排对比 UI]
    └──requires──> [Race 结果展示]（已有）
    └──requires──> [Evaluate 前端]
    └──enables──> [方案迭代推演]

[结果可导出]
    └──requires──> [多方案并排对比 UI]（需要有东西可导）

[推演结果趋势追踪]
    └──requires──> [方案迭代推演]
    └──requires──> [历史数据持久化]（部分已有）

[统一推演入口]
    └──requires──> [Race 路径]（已有）
    └──requires──> [Evaluate 路径前端]

[并行图片分析]
    └──enhances──> [推演速度]
    └──independent──（无前置依赖）

[视觉诊断建议]
    └──enhances──> [多方案并排对比 UI]
    └──requires──> [ImageAnalyzer 结构化输出改造]
```

### Dependency Notes

- **Evaluate 前端 requires 图片 bug 修复**: 不修 bug 就做前端，用户会看到"图片分析成功"但实际没分析，体验灾难性
- **并排对比 requires 两条路径都有 UI**: Race 已有，Evaluate 前端是 blocker
- **导出 requires 并排对比**: 导出的前提是有结构化的结果展示，否则导出的是什么？
- **趋势追踪 requires 迭代推演**: 没有版本概念就无法追踪趋势

## MVP Definition

### Launch With (v1) — 当前 Active Backlog

已有后端能力的前端补全 + 关键 bug 修复。

- [x] Race 推演路径（已有）
- [x] 视觉分析引擎（已有）
- [x] 历史基线匹配（已有）
- [ ] **修复 Evaluate 图片 bug** — 不修复则 Evaluate 路径不可信
- [ ] **Evaluate 路径前端** — 让非技术用户也能发起深度推演
- [ ] **按品类配置评审人格** — 透明片/彩片不同评审团是 Moody 场景刚需
- [ ] **统一推演入口** — 用户不该需要知道该调哪个 API
- [ ] **并行图片分析** — 3+ 张图串行太慢，影响使用意愿
- [ ] **多方案并排对比 UI** — 推演结果的核心展示形式

### Add After Validation (v1.x)

核心路径跑通后，增强结果的可用性和团队协作体验。

- [ ] **结果导出 PDF/Image** — 第一次有人要把结果带进会议时加
- [ ] **视觉诊断建议结构化** — 从"一段话分析"升级为"问题 → 建议"结构
- [ ] **方案迭代推演（版本对比）** — 当团队开始迭代素材并想看改善时加
- [ ] **受众人格自定义** — 当固定人格不能覆盖新品类或特殊 campaign 时加
- [ ] **密码哈希 + 线程安全** — 多用户同时使用前必须做

### Future Consideration (v2+)

产品验证后的深化方向。

- [ ] **推演趋势 Dashboard** — 需要积累足够多次推演数据后才有意义
- [ ] **品牌认知状态模型重构** — BrandStateEngine 需要从 God class 拆分，但当前能用
- [ ] **跨品类基线对比** — 透明片 campaign 和彩片 campaign 的横向比较
- [ ] **推演模板** — 常用 campaign 类型（新品上市、节日促销、日常种草）的预设配置

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| 修复 Evaluate 图片 bug | HIGH | LOW | **P1** |
| Evaluate 路径前端 | HIGH | MEDIUM | **P1** |
| 按品类配置评审人格 | HIGH | MEDIUM | **P1** |
| 统一推演入口 | HIGH | LOW | **P1** |
| 并行图片分析 | MEDIUM | LOW | **P1** |
| 多方案并排对比 UI | HIGH | MEDIUM | **P1** |
| 结果导出 PDF/Image | MEDIUM | MEDIUM | **P2** |
| 视觉诊断建议结构化 | MEDIUM | MEDIUM | **P2** |
| 方案迭代推演 | MEDIUM | HIGH | **P2** |
| 受众人格自定义 | MEDIUM | HIGH | **P2** |
| 密码哈希 + 线程安全 | LOW (内部工具) | LOW | **P2** |
| 推演趋势 Dashboard | MEDIUM | HIGH | **P3** |
| 品牌状态模型重构 | LOW (当前能用) | HIGH | **P3** |

**Priority key:**
- P1: Must have — 不做则推演工具不完整，用户无法完成核心流程
- P2: Should have — 提升体验和协作效率，在核心流程稳定后加
- P3: Nice to have — 长期价值，需要数据积累或架构重构

## Competitor Feature Analysis

| Feature | Kantar LINK AI | Zappi | System1 | Behavio | MiroFishmoody 策略 |
|---------|---------------|-------|---------|---------|-------------------|
| 速度 | 15min (AI) / 6hr (panel) | 数小时 | 数天 | 数天 | **< 5 min**（AI 合成人格，零招募成本）|
| 真人 panel | 有（全球 60+ 市场） | 有（自有 panel） | 有（~150 人） | 有（500+ 人） | **无** — 用 AI 合成受众替代 |
| 情绪分析 | 有 | 有 | 核心能力（FaceTrace） | 有（行为科学） | 通过 LLM persona 模拟情绪反应 |
| 视觉热力图 | 无 | 无 | 无 | 无 | **不做** — 用 LLM vision 替代 |
| 品牌契合度 | 有（Brand Linkage） | 有（Brand Fluency） | 有（Fluency Score） | 有 | 通过 BrandStateEngine 评估 |
| 历史基线 | 有（Kantar DB） | 有（Zappi norms） | 有 | 有 | 有（BaselineRanker + 自有历史数据）|
| 定价 | $$$$ (企业级) | $$$ (SaaS) | $$$ (SaaS) | $$ (SaaS) | **内部工具，零边际成本** |
| 定制化 | 低（标准化产品） | 中 | 低 | 低 | **高**（为 Moody 品类深度定制）|

### MiroFishmoody 的核心竞争叙事

> 我们不是在做一个 Kantar 替代品。我们是在用 AI 合成受众 + 品牌深度定制，让每一次 campaign 决策都有数据支撑，而不是花几万块买一次调研报告。速度快（分钟级）、成本低（接近零）、深度定制（按品类配置人格）是我们相对于外部工具的核心优势。

## Sources

- [Behavio: Ad Testing Software Guide 2026](https://www.behaviolabs.com/blog/ad-testing-software-what-it-is-how-it-works-the-best-platforms-in-2026)
- [Kantar: Ad Screening, Creative Testing & Effectiveness](https://www.kantar.com/Solutions/Creative)
- [Zappi: Digital Ad Testing](https://www.zappi.io/web/creative-digital/)
- [System1: Test Your Ad Platform](https://system1group.com/test-your-ad)
- [Sovran: 12 Best Creative Testing Tools 2026](https://sovran.ai/blog/creative-testing-software)
- [SuperAds: 6 Best Ad Testing Tools 2026](https://www.superads.ai/blog/best-ad-testing-tools)
- [Neurons: Ad Testing Methods](https://www.neuronsinc.com/ad-testing/methods)
- [Human Made Machine: Guide to Creative Pre-Testing](https://www.humanmademachine.com/insights/the-comprehensive-guide-to-creative-pre-testing-maximizing-campaign-performance)
- [Altair Media: Synthetic Audiences 2026](https://altair-media.com/posts/synthetic-audiences-in-market-research-hype-reality-and-outlook-for-2026)
- [Four Agency: AI-Assisted Creative Testing Synthetic Focus Groups](https://www.four.agency/news-insights/ai-assisted-creative-testing-synthetic-focus-groups)
- [Influencers Time: AI-Driven Synthetic Audiences 2025](https://www.influencers-time.com/ai-driven-synthetic-audiences-revolutionizing-marketing-2025/)
- [Pixis: How to Use Ad Pre-Testing](https://pixis.ai/blog/how-to-use-ad-pre-testing-in-your-campaigns/)

---
*Feature research for: Brand Campaign Pre-testing / 推演 (Moody Lenses Internal Tool)*
*Researched: 2026-03-17*
