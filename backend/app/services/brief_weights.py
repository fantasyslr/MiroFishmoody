"""
Brief-Type 维度权重配置

每套权重对应一种 brief 类型，6 个维度权重之和必须为 1.0。
当前版本由专家设计，Phase 20 benchmark 命中率测量后可调参。

维度定义（来自 scoreboard.py）：
  thumb_stop          — 停留吸引力
  clarity             — 信息清晰度
  trust               — 信任感
  conversion_readiness — 转化就绪度
  claim_risk          — 声称风险（高 = 差）
  emotional_resonance — 情感共鸣（新增维度，当前 DimensionEvaluator 未输出时权重为 0）
"""

# 每套权重的版本标识符，写入 EvaluationResult.weight_profile_version
WEIGHT_PROFILE_VERSIONS: dict[str, str] = {
    "brand":      "brand-v1",
    "seeding":    "seeding-v1",
    "conversion": "conversion-v1",
}

# 各 brief 类型的维度权重，key 与 DIMENSION_KEYS 对齐
# 注：emotional_resonance 目前 DimensionEvaluator 不输出，权重占位 0.0 不影响评分
BRIEF_DIMENSION_WEIGHTS: dict[str, dict[str, float]] = {
    "brand": {
        "thumb_stop":           0.20,
        "clarity":              0.10,
        "trust":                0.15,
        "conversion_readiness": 0.10,
        "claim_risk":           0.15,
        "emotional_resonance":  0.30,  # 品牌传播核心维度（CONTEXT.md 锁定 0.30）
    },
    "seeding": {
        "thumb_stop":           0.20,
        "clarity":              0.15,
        "trust":                0.10,
        "conversion_readiness": 0.15,
        "claim_risk":           0.10,
        "emotional_resonance":  0.30,  # 达人种草 authenticity 映射为 emotional_resonance
    },
    "conversion": {
        "thumb_stop":           0.15,
        "clarity":              0.15,
        "trust":                0.10,
        "conversion_readiness": 0.35,  # 转化拉新核心维度（CONTEXT.md 锁定 0.35）
        "claim_risk":           0.25,
        "emotional_resonance":  0.00,
    },
}

# 合法值集合，用于 API 层快速校验
BRIEF_TYPE_VALUES: frozenset[str] = frozenset(BRIEF_DIMENSION_WEIGHTS.keys())
