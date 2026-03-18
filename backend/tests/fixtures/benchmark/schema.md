# Benchmark Dataset Schema

每个 benchmark fixture 是一个 JSON 文件，描述一次假设的 campaign 评审场景。

## 必填字段

| 字段 | 类型 | 约束 |
|------|------|------|
| `id` | string | 与文件名一致，如 "brand_001" |
| `brief_type` | string | "brand" / "seeding" / "conversion" |
| `expected_winner_id` | string | 必须是 campaigns[] 中某个 campaign 的 id |
| `label_confidence` | string | "high" / "medium" / "low" |
| `rationale` | string | 标注理由（中文），≥ 20 字 |
| `campaigns` | array | 2-5 个 campaign 对象 |

## campaigns[] 中每个 campaign 对象

| 字段 | 类型 | 约束 |
|------|------|------|
| `id` | string | 在本文件内唯一 |
| `name` | string | 方案名称 |
| `product_line` | string | "colored_lenses" / "moodyplus" |
| `target_audience` | string | 目标受众描述 |
| `core_message` | string | 核心信息 |
| `channels` | array | 至少 1 个渠道字符串 |
| `creative_direction` | string | 创意方向描述 |

## 可选字段（campaign 对象）

- `budget_range`: string
- `kv_description`: string
- `promo_mechanic`: string

## 命名规范

文件名格式: `{brief_type}_{NNN}.json`，NNN 三位数字，如 `brand_001.json`

## 评分规则说明

runner 调用真实 EvaluationOrchestrator（注入 mock LLMClient），
对比 result.rankings[0].campaign_id 与 expected_winner_id。
相符 = 命中（hit），不符 = 未命中（miss）。
label_confidence="low" 的样本计入分母但标记为 uncertain。
