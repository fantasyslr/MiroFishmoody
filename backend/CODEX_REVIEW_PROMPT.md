# Codex Review Prompt — Brandiction Engine PR7 + PR8 + PR8.1

## 背景
这是 Moody Lenses（隐形眼镜品牌）的 Brandiction Engine（brand + prediction），一个品牌认知状态预测系统。当前代码跨 3 个 PR 迭代：

- **PR7**: 三层渠道模型（channel_family → platform → market）
- **PR8**: 轻量 agent diffusion 仿真层（32 个消费者 agent，稀疏图扩散）
- **PR8.1**: diffusion 语义修复（platform-aware, zero-exposure guard, budget=0 fix）

所有代码未提交，需要 review 后再做一次性 commit。

## 需要 Review 的文件

### 核心代码（按依赖顺序）
1. `app/models/brand_state.py` — 7 维认知向量 + BrandState/StateTransition 数据模型
2. `app/models/brandiction.py` — HistoricalIntervention/Outcome/Signal/CompetitorEvent 数据模型
3. `app/services/brandiction_store.py` — SQLite 持久化层（singleton, merge upsert, migration）
4. `app/services/brand_state_engine.py` — 核心引擎（三层渠道模型, predict, replay, backtest, simulate, compare, diffusion 集成）
5. `app/services/agent_diffusion.py` — Agent 扩散引擎（8 archetype × 3-5 clones, 稀疏图, platform-aware exposure）
6. `app/api/brandiction.py` — Flask API 路由层

### 测试
7. `tests/test_pr7_channel_model.py` — 77 tests（渠道模型 + market 隔离）
8. `tests/test_pr8_agent_diffusion.py` — 53 tests（agent diffusion + 语义修复）

## Review 重点

### 1. 架构合理性
- 三层渠道模型（family → platform → market）的分层是否清晰？系数是否合理？
- agent diffusion 只影响 3 个不确定维度（social_proof, skepticism, competitor_pressure），规则维度（science_credibility, comfort_trust, aesthetic_affinity, price_sensitivity）由历史+规则驱动——这个分界是否合理？
- `predict_with_diffusion` 的混合策略 `merged_delta[d] = rule_delta[d] + agent_delta[d] × 0.5` 是否合理？

### 2. 语义正确性
- `_apply_exposure()` 中 platform modifier 的方向性：
  - `social_proof`: `+effect * sp_mod`（modifier > 1 → 更强推动）
  - `skepticism`: `-effect * 0.5 / max(0.5, sk_mod)`（modifier > 1 → 减少效果变弱，因为平台激发质疑）
  - `competitor_pressure`: `-effect * 0.3 / max(0.5, cp_mod)`
  - 这个逻辑是否有 bug？有没有更好的建模方式？
- `compute_budget_exposure_strength(budget=0) → 0.0`，零曝光早返回是否正确？
- `_apply_budget_scaling` 中 `budget=0 → return delta`（不缩放），但 diffusion 侧 `budget=0 → strength=0 → 跳过仿真`——两边逻辑是否一致？

### 3. 数据一致性
- `market` 作为 first-class 维度是否全链路贯通？（模型 → store → engine → API）
- 确定性 ID pattern（`bs-after-{iv_id}-{market}`, `tr-{iv_id}-{market}`）是否有碰撞风险？
- singleton store 在测试中是否有数据泄漏风险？

### 4. 代码质量
- 有没有死代码、未使用的导入、不必要的复杂度？
- `_merge_upsert` 中 SQL 拼接是否有注入风险？（表名和列名来自代码内部常量，不来自用户输入）
- archetype 参数（sensitivity, base_tendency, resistance, influence_weight）的数值是否合理？

### 5. 测试覆盖
- 测试是否覆盖了核心路径？有没有漏测的边界条件？
- 有没有脆弱的断言（容易因为参数微调而 break 的）？

### 6. 准备写但还没写的部分
以下是计划中的后续 PR，需要评估当前架构是否能支撑：
- **PR9**: 四层 agent 重构（KOL 6 + KOC 9 + Consumer 40-48 = 55-63 agents）
- **PR10**: platform-aware diffusion graph（图结构按角色分层）
- **PR11**: echo chamber + competitor pull（同类强化系数）
- 数据管道：Meta Marketing API → 素材分类 → interventions; 独立站数据 → outcomes

## 输出格式
请按以下格式输出 review 结果：

```
## [Critical] 标题
文件:行号 — 描述

## [High] 标题
文件:行号 — 描述

## [Medium] 标题
文件:行号 — 描述

## [Low] 标题
文件:行号 — 描述

## [Good] 值得保留的设计决策
描述
```
