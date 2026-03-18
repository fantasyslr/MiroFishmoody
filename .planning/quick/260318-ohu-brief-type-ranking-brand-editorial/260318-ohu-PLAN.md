---
phase: quick-260318-ohu
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/services/campaign_scorer.py
  - backend/tests/fixtures/benchmark/brand_005.json
  - backend/tests/test_benchmark_runner.py
autonomous: true
requirements: [OHU-1, OHU-2]

must_haves:
  truths:
    - "brief_type=brand 时，高定情绪大片（emotional_resonance 强）在 ranking 中胜出明星同款快转化（conversion_readiness 强）"
    - "brief_type=conversion 时，ranking 结果不受 brand 权重影响"
    - "brief_type=None 时，排名行为与修复前完全一致（backward compat）"
    - "brand_005.json fixture 存在且 test_fixture_count 通过（12 个 fixture）"
  artifacts:
    - path: "backend/app/services/campaign_scorer.py"
      provides: "brief_type 加权维度分混入 overall_score"
      contains: "dim_weighted_scores"
    - path: "backend/tests/fixtures/benchmark/brand_005.json"
      provides: "明星同款 vs 高定情绪大片 benchmark case"
      contains: "brand_editorial"
    - path: "backend/tests/test_benchmark_runner.py"
      provides: "更新 fixture count 断言为 12"
  key_links:
    - from: "backend/app/services/campaign_scorer.py"
      to: "backend/app/services/submarket_evaluator.py"
      via: "dimension_results → dim_weighted_scores → blended into scores"
      pattern: "dim_weighted"
    - from: "backend/tests/fixtures/benchmark/brand_005.json"
      to: "backend/tests/test_benchmark_runner.py"
      via: "test_fixture_count 断言 len==12"
      pattern: "len(files) == 12"
---

<objective>
两项修复：

1. brief_type 权重接入最终 ranking：DimensionEvaluator 已对维度 softmax 概率按 brief_weights 缩放，但这些加权维度分未回流到 overall_score——排序仍由 probability_aggregator 的纯 BT+panel 概率决定。需在 CampaignScorer.score() 中将加权维度分求和，作为第三路信号混入最终排序分。

2. brand_editorial 失手 case 固化为 benchmark：新增 brand_005.json，场景"明星同款快转化 vs 高定情绪大片"，预期冠军为高定情绪大片（brand brief_type，emotional_resonance 权重 0.30 应拉开差距）。同步更新 test_fixture_count 断言为 12。

Purpose: 确保 brief_type 的权重配置对最终 ranking 真正生效，并用回归 fixture 防止此类失手重现。
Output: 修改后的 campaign_scorer.py，新 brand_005.json，更新的 test_benchmark_runner.py。
</objective>

<execution_context>
@/Users/slr/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@/Users/slr/MiroFishmoody/.planning/STATE.md
@/Users/slr/MiroFishmoody/backend/app/services/campaign_scorer.py
@/Users/slr/MiroFishmoody/backend/app/services/submarket_evaluator.py
@/Users/slr/MiroFishmoody/backend/app/services/brief_weights.py
@/Users/slr/MiroFishmoody/backend/app/services/probability_aggregator.py
@/Users/slr/MiroFishmoody/backend/tests/fixtures/benchmark/brand_001.json
@/Users/slr/MiroFishmoody/backend/tests/test_benchmark_runner.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 将加权维度分混入 campaign_scorer.py 的最终 overall_score</name>
  <files>backend/app/services/campaign_scorer.py</files>
  <behavior>
    - 测试1：brief_type=None 时，scores dict 与修复前一致（维度分混入权重为 0，backward compat）
    - 测试2：brief_type=brand 时，emotional_resonance 权重 0.30 使情感化方案 overall_score 高于促销方案
    - 测试3：brief_type=conversion 时，conversion_readiness 权重 0.35 使转化方案胜出
  </behavior>
  <action>
在 campaign_scorer.py 的 score() 方法中，在"Overall scores"块（probability_aggregator.aggregate 调用）之后、"Agent score contribution"块之前，插入如下逻辑：

```python
# --- Brief-type dimension weight boost ---
# DimensionEvaluator 已按 brief_weights 缩放各维度 softmax 概率。
# 将加权维度分求和，作为第三路信号按固定权重混入 overall_score。
# brief_type=None 时 dim_weights={} → dim_boost 全为 0 → 行为不变。
DIM_BOOST_WEIGHT = float(os.environ.get('DIM_BOOST_WEIGHT', '0.15'))

if self.brief_type is not None:
    from .brief_weights import BRIEF_DIMENSION_WEIGHTS
    dim_weights = BRIEF_DIMENSION_WEIGHTS.get(self.brief_type.value, {})
else:
    dim_weights = {}

if dim_weights:
    # 提前计算 dimension_results（避免后面重复调用）
    _early_dim_results = self.dimension_eval.evaluate(
        campaigns, panel_scores, brief_type=self.brief_type
    )
    dim_by_cid_early: Dict[str, Dict[str, float]] = defaultdict(dict)
    for ds in _early_dim_results:
        dim_by_cid_early[ds.campaign_id][ds.dimension_key] = ds.score
    # 各 campaign 的加权维度分之和（已是 softmax×weight，天然可比）
    dim_weighted_scores = {
        cid: sum(dim_by_cid_early[cid].values())
        for cid in all_ids
    }
    # 归一化到 sum=1
    _dws_total = sum(dim_weighted_scores.values())
    if _dws_total > 0:
        dim_weighted_probs = {k: v / _dws_total for k, v in dim_weighted_scores.items()}
    else:
        dim_weighted_probs = {cid: 1.0 / len(all_ids) for cid in all_ids}
    # 混入：原始 prob 让步给维度信号
    scores = {
        cid: scores[cid] * (1.0 - DIM_BOOST_WEIGHT)
              + dim_weighted_probs.get(cid, 0) * DIM_BOOST_WEIGHT
        for cid in all_ids
    }
    # 后续 dimension_results 直接复用，避免重复 evaluate
    _prefetched_dim_results = _early_dim_results
else:
    _prefetched_dim_results = None
```

然后在"Dimension scores"块（`dimension_results = self.dimension_eval.evaluate(...)`）处，改为：

```python
# --- Dimension scores ---
if _prefetched_dim_results is not None:
    dimension_results = _prefetched_dim_results
else:
    dimension_results = self.dimension_eval.evaluate(
        campaigns, panel_scores, brief_type=self.brief_type
    )
```

注意：DIM_BOOST_WEIGHT 默认 0.15，表示维度信号贡献最终分的 15%。这足以在 brief_type 差异明显时翻转排名（emotional_resonance 权重 0.30 × dim_boost 0.15），又不会在无 brief_type 时改变任何行为。

不要修改 ProbabilityAggregator 或 DimensionEvaluator。只在 campaign_scorer.py 的 score() 方法内操作。
  </action>
  <verify>
    <automated>cd /Users/slr/MiroFishmoody/backend && uv run pytest tests/test_scorer.py tests/test_campaign_scorer_agent_scores.py tests/test_brief_weights.py -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>pytest 通过，且在手动验证中：brief_type=brand + 情感化方案 overall_score > 促销方案；brief_type=None 行为不变</done>
</task>

<task type="auto">
  <name>Task 2: 新增 brand_005.json 并更新 test_fixture_count 断言</name>
  <files>
    backend/tests/fixtures/benchmark/brand_005.json
    backend/tests/test_benchmark_runner.py
  </files>
  <action>
**创建 backend/tests/fixtures/benchmark/brand_005.json：**

场景：明星同款快转化 vs 高定情绪大片。
brief_type=brand，expected_winner_id=b005_b（高定情绪大片）。

```json
{
  "id": "brand_005",
  "brief_type": "brand",
  "expected_winner_id": "b005_b",
  "label_confidence": "high",
  "rationale": "高定情绪大片通过视觉诗意和品牌美学传递情感共鸣，契合 brand brief 中 emotional_resonance 权重 0.30 的优先级。明星同款快转化以 KOL 带货逻辑驱动，转化信号强但品牌调性弱，在 brand brief 下不应胜出。这是品牌评审中'明星快转化 vs 高定情绪大片'的典型失手场景，需作为回归 benchmark 固化。",
  "campaigns": [
    {
      "id": "b005_a",
      "name": "明星同款速抢 — KOL 快转化投流",
      "product_line": "colored_lenses",
      "target_audience": "18-28岁追星粉丝，决策快，价格敏感",
      "core_message": "和XX同款彩片，限时折扣，扫码直接买",
      "channels": ["抖音信息流", "小红书KOL合作"],
      "creative_direction": "明星同款对比图，右上角挂购物车链接，配文「她同款，速抢」",
      "kv_description": "明星近照 + 产品图拼接，强调价格标签和购物入口",
      "promo_mechanic": "限时7折，首购减30元"
    },
    {
      "id": "b005_b",
      "name": "高定情绪大片 — 品牌美学宣言",
      "product_line": "colored_lenses",
      "target_audience": "22-35岁有审美追求的都市女性，注重品牌调性",
      "core_message": "色彩是态度，不是装扮。moody 彩片，为有主见的眼神而生。",
      "channels": ["小红书品牌号", "微博开屏", "抖音品牌专区"],
      "creative_direction": "高端时装大片风格：模特凝视镜头，环境光戏剧性打光，无文字遮挡，画面留白70%，配乐沉浸感强",
      "kv_description": "胶片质感特写，眼神直视观众，彩片颜色在光线下呈现层次感，背景极简"
    }
  ]
}
```

**更新 backend/tests/test_benchmark_runner.py：**

将 test_fixture_count 中的断言从：
```python
assert len(files) == 11, f"Expected 11 fixtures, got {len(files)}: {files}"
```
改为：
```python
assert len(files) == 12, f"Expected 12 fixtures, got {len(files)}: {files}"
```

同时将 test_fixture_loading 中的断言从：
```python
assert len(files) >= 10, f"Expected >=10 fixtures, got {len(files)}"
```
改为：
```python
assert len(files) >= 11, f"Expected >=11 fixtures, got {len(files)}"
```

保留文件其余全部内容不变。
  </action>
  <verify>
    <automated>cd /Users/slr/MiroFishmoody/backend && uv run pytest tests/test_benchmark_runner.py -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>test_fixture_count 断言通过（12 个 fixture），brand_005.json 格式校验通过（brief_type=brand，expected_winner_id=b005_b 在 campaigns 中存在）</done>
</task>

</tasks>

<verification>
整体验证：

```bash
cd /Users/slr/MiroFishmoody/backend && uv run pytest tests/test_scorer.py tests/test_benchmark_runner.py tests/test_brief_weights.py tests/test_campaign_scorer_agent_scores.py -x -q 2>&1 | tail -30
```

手动验证 brief_type 权重是否真正影响 ranking（可在 Python REPL 中构造最小用例）：
- 两个 campaign：A 高 emotional_resonance 分，B 高 conversion_readiness 分
- brief_type=brand → A 应排 #1
- brief_type=conversion → B 应排 #1
- brief_type=None → 结果由原始 BT+panel 决定，不受维度权重影响
</verification>

<success_criteria>
- `uv run pytest tests/test_scorer.py tests/test_benchmark_runner.py -x -q` 全部通过
- brief_type=brand 时，DIM_BOOST_WEIGHT（默认 0.15）使情感化方案在 ranking 中胜出促销方案
- brief_type=None 时行为与修复前完全一致
- brand_005.json 存在，格式合规，expected_winner_id=b005_b
- test_fixture_count 断言为 12
</success_criteria>

<output>
完成后在 /Users/slr/MiroFishmoody/.planning/quick/260318-ohu-brief-type-ranking-brand-editorial/ 创建 260318-ohu-SUMMARY.md，记录：
- 修复方案（DIM_BOOST_WEIGHT 信号混入逻辑）
- 新增 fixture 路径
- 测试通过状态
- 已修改文件清单
</output>
