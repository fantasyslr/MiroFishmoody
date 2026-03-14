"""
BrandState Engine — 品牌认知状态的构建、回放和预测

核心能力：
  1. 从历史 signals 构建 BrandState 快照（支持时间衰减加权）
  2. 从历史 intervention + outcome 回放状态转移（含竞品事件影响）
  3. 给出当前最新状态
  4. 预测一次干预的状态影响（Phase A: 基于规则 + 历史模式）
  5. 渠道效能加权 — 不同渠道对认知维度有不同影响系数
  6. 预算缩放 — 预算规模调节影响幅度（对数递减）
  7. 回测验证 — 留一法评估预测准确度
  8. 多步情景模拟 — 模拟一系列计划干预的累积效果
  9. 情景对比 — 并排比较多条时间线
"""

import math
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple

from ..models.brand_state import (
    BrandState,
    PerceptionVector,
    StateTransition,
    PERCEPTION_DIMENSIONS,
)
from ..models.brandiction import HistoricalIntervention, HistoricalOutcomeWindow
from .brandiction_store import BrandictionStore


# ------------------------------------------------------------------
# Theme → Dimension 映射（可扩展）
# ------------------------------------------------------------------

THEME_DIM_MAP: Dict[str, str] = {
    "science": "science_credibility",
    "science_credibility": "science_credibility",
    "professional": "science_credibility",
    "eye_health": "science_credibility",
    "comfort": "comfort_trust",
    "comfort_beauty": "comfort_trust",
    "beauty": "aesthetic_affinity",
    "aesthetic": "aesthetic_affinity",
    "price": "price_sensitivity",
    "discount": "price_sensitivity",
    "social": "social_proof",
    "kol": "social_proof",
    "ugc": "social_proof",
}


# ------------------------------------------------------------------
# 三层渠道模型：family → platform → market
# ------------------------------------------------------------------

# Layer 1: 渠道家族 — 按内容形态和用户行为分类
CHANNEL_FAMILIES: Dict[str, Dict[str, float]] = {
    "short_video": {
        "social_proof": 1.3,
        "aesthetic_affinity": 1.2,
        "science_credibility": 0.8,
    },
    "social_seed": {          # 种草 / 图文社区
        "aesthetic_affinity": 1.3,
        "social_proof": 1.2,
        "comfort_trust": 1.1,
    },
    "longform_content": {     # 长视频 / 公众号 / blog
        "science_credibility": 1.3,
        "comfort_trust": 1.2,
        "social_proof": 0.9,
    },
    "marketplace": {          # 电商平台
        "price_sensitivity": 1.3,
        "comfort_trust": 1.1,
        "social_proof": 0.9,
    },
    "search": {               # 搜索广告
        "science_credibility": 1.1,
        "price_sensitivity": 1.2,
    },
    "dtc_site": {             # 独立站 / DTC
        "comfort_trust": 1.2,
        "price_sensitivity": 1.1,
        "science_credibility": 1.1,
    },
    "crm": {                  # 私域 / 邮件 / 会员
        "comfort_trust": 1.3,
        "social_proof": 0.7,
        "skepticism": 0.8,   # 私域用户信任度高，质疑少
    },
    "influencer": {           # KOL / 达人 / affiliate
        "social_proof": 1.4,
        "aesthetic_affinity": 1.2,
        "skepticism": 1.1,   # 广告感可能引发质疑
    },
    "offline": {
        "comfort_trust": 1.4,
        "science_credibility": 1.2,
        "social_proof": 0.7,
    },
}

# Layer 2: 平台 → 家族归属 + 平台级 override
# format: (family, {dim: override_value, ...})
PLATFORM_REGISTRY: Dict[str, tuple] = {
    # 国内
    "douyin":       ("short_video",    {}),
    "kuaishou":     ("short_video",    {"social_proof": 1.2}),  # 快手社交稍弱于抖音
    "redbook":      ("social_seed",    {"aesthetic_affinity": 1.4}),  # 小红书颜值更强
    "weibo":        ("social_seed",    {"skepticism": 1.1, "aesthetic_affinity": 1.0}),  # 微博更多讨论/质疑
    "wechat":       ("longform_content", {"social_proof": 0.8}),  # 私域传播有限
    "bilibili":     ("longform_content", {"science_credibility": 1.4, "aesthetic_affinity": 1.1}),
    "zhihu":        ("longform_content", {"science_credibility": 1.3, "skepticism": 1.1}),
    "tmall":        ("marketplace",    {}),
    "jd":           ("marketplace",    {}),
    "pdd":          ("marketplace",    {"price_sensitivity": 1.5}),  # 拼多多价格导向更强
    "dewu":         ("marketplace",    {"aesthetic_affinity": 1.2}),  # 得物潮流属性
    # 海外
    "tiktok":       ("short_video",    {}),
    "instagram":    ("social_seed",    {"aesthetic_affinity": 1.4}),
    "youtube":      ("longform_content", {"science_credibility": 1.3}),
    "facebook":     ("social_seed",    {"social_proof": 1.1, "aesthetic_affinity": 1.0}),
    "pinterest":    ("social_seed",    {"aesthetic_affinity": 1.5}),
    "twitter":      ("social_seed",    {"skepticism": 1.2, "aesthetic_affinity": 0.9}),
    "google":       ("search",         {}),
    "amazon":       ("marketplace",    {}),
    "shopee":       ("marketplace",    {"price_sensitivity": 1.4}),
    "lazada":       ("marketplace",    {}),
    "rakuten":      ("marketplace",    {}),
    # 独立站 / DTC
    "shopify":      ("dtc_site",       {}),
    "dtc":          ("dtc_site",       {}),
    "landing_page": ("dtc_site",       {"science_credibility": 1.2}),
    # CRM / 私域
    "email":        ("crm",            {}),
    "sms":          ("crm",            {}),
    "wechat_crm":   ("crm",            {"comfort_trust": 1.4}),  # 微信私域信任最高
    "line":         ("crm",            {}),
    # Influencer / Affiliate
    "kol":          ("influencer",     {}),
    "koc":          ("influencer",     {"social_proof": 1.3, "skepticism": 0.9}),  # KOC 更真实
    "affiliate":    ("influencer",     {"price_sensitivity": 1.2}),
    # 线下
    "offline":      ("offline",        {}),
    "pop_up":       ("offline",        {"aesthetic_affinity": 1.3}),
    "optical_shop": ("offline",        {"science_credibility": 1.3, "comfort_trust": 1.5}),
}

# Layer 3: 市场调节系数 — 不同市场的用户行为差异
MARKET_ADJUSTMENTS: Dict[str, Dict[str, float]] = {
    "cn": {},  # 中国是基准市场，系数 1.0
    "us": {
        "science_credibility": 1.1,   # 美国消费者更看重科学背书
        "price_sensitivity": 0.9,     # 价格敏感度稍低
        "social_proof": 0.9,          # KOL 种草文化没国内强
    },
    "jp": {
        "science_credibility": 1.2,   # 日本极重品质/安全
        "comfort_trust": 1.2,
        "aesthetic_affinity": 1.1,
        "skepticism": 1.1,            # 日本消费者更审慎
    },
    "sea": {
        "price_sensitivity": 1.3,     # 东南亚价格敏感
        "social_proof": 1.2,          # 社交电商强
        "science_credibility": 0.9,
    },
    "eu": {
        "science_credibility": 1.1,
        "skepticism": 1.1,            # 欧洲消费者更审慎
        "price_sensitivity": 1.0,
    },
    "kr": {
        "aesthetic_affinity": 1.3,    # 韩国极重颜值
        "social_proof": 1.2,
        "comfort_trust": 1.1,
    },
}

# 向后兼容：旧的平面字典（由 PLATFORM_REGISTRY + CHANNEL_FAMILIES 生成）
def _build_channel_effectiveness() -> Dict[str, Dict[str, float]]:
    """从三层模型生成平面 platform→effectiveness 字典"""
    result = {}
    for platform, (family, overrides) in PLATFORM_REGISTRY.items():
        base = dict(CHANNEL_FAMILIES.get(family, {}))
        base.update(overrides)
        result[platform] = base
    return result

CHANNEL_EFFECTIVENESS: Dict[str, Dict[str, float]] = _build_channel_effectiveness()

# 竞品事件对 competitor_pressure 维度的影响幅度
COMPETITOR_IMPACT_MAP: Dict[str, float] = {
    "high": 0.08,
    "medium": 0.05,
    "low": 0.02,
}

# 预算缩放基准值 — 标准预算 50000 时乘数为 1.0
BUDGET_BASELINE = 50000.0

# 信号时间衰减半衰期（天）— 90 天前的信号权重约为最新的 50%
SIGNAL_HALF_LIFE_DAYS = 90


class BrandStateEngine:
    """构建和管理 BrandState 的核心引擎"""

    def __init__(self, store: BrandictionStore = None):
        self.store = store or BrandictionStore()

    # ------------------------------------------------------------------
    # 从 signals 构建快照
    # ------------------------------------------------------------------

    def build_state_from_signals(
        self,
        as_of_date: str,
        product_line: str = "moodyplus",
        audience_segment: str = "general",
        use_decay: bool = True,
        market: str = "cn",
    ) -> BrandState:
        """
        从历史 signals 构建某个日期的 BrandState。
        每个 dimension 按时间衰减加权平均（半衰期 90 天）。
        如果同维度只有一条信号则直接使用该值。
        """
        state_id = f"bs-{as_of_date}-{str(uuid.uuid4())[:8]}"
        state = self._compute_state_from_signals(
            state_id, as_of_date, product_line, audience_segment, use_decay, market,
        )
        self.store.save_brand_state(state)
        return state

    def _compute_state_from_signals(
        self,
        state_id: str,
        as_of_date: str,
        product_line: str = "moodyplus",
        audience_segment: str = "general",
        use_decay: bool = True,
        market: str = "cn",
    ) -> BrandState:
        """
        从 signals 计算 BrandState（纯计算，不保存）。
        build_state_from_signals 和 _build_state_from_signals_deterministic 都复用此方法。
        """
        signals = self.store.list_signals(
            product_line=product_line, audience_segment=audience_segment,
            date_to=as_of_date, market=market,
        )

        # 按 dimension 分组
        dim_signals: Dict[str, List[tuple]] = {}
        for sig in signals:
            if sig.dimension and sig.value is not None:
                dim_signals.setdefault(sig.dimension, []).append(
                    (sig.value, sig.date, sig.source)
                )

        # 按 dimension 计算加权值
        dim_values: Dict[str, float] = {}
        dim_sources: Dict[str, str] = {}
        ref_date = _parse_date(as_of_date)

        for dim, entries in dim_signals.items():
            if len(entries) == 1:
                dim_values[dim] = entries[0][0]
                dim_sources[dim] = f"{entries[0][2] or 'signal'}@{entries[0][1]}"
                continue

            if use_decay and ref_date:
                weighted_sum = 0.0
                weight_total = 0.0
                latest_source = entries[-1]
                for val, date_str, source in entries:
                    w = _decay_weight(date_str, ref_date)
                    weighted_sum += val * w
                    weight_total += w
                if weight_total > 0:
                    dim_values[dim] = weighted_sum / weight_total
                dim_sources[dim] = f"{latest_source[2] or 'signal'}@{latest_source[1]}(weighted)"
            else:
                latest = entries[-1]
                dim_values[dim] = latest[0]
                dim_sources[dim] = f"{latest[2] or 'signal'}@{latest[1]}"

        pv_dict = {}
        for dim in PERCEPTION_DIMENSIONS:
            if dim in dim_values:
                pv_dict[dim] = dim_values[dim]
        perception = PerceptionVector.from_dict(pv_dict)

        evidence = list(dim_sources.values())
        confidence = min(0.9, 0.3 + 0.1 * len(dim_values))

        return BrandState(
            state_id=state_id,
            as_of_date=as_of_date,
            product_line=product_line,
            audience_segment=audience_segment,
            market=market,
            perception=perception,
            confidence=confidence,
            evidence_sources=evidence,
        )

    # ------------------------------------------------------------------
    # 从历史 outcome 推算干预影响
    # ------------------------------------------------------------------

    def compute_intervention_impact(
        self,
        intervention: HistoricalIntervention,
        outcomes: List[HistoricalOutcomeWindow],
        market: str = "cn",
    ) -> Dict[str, float]:
        """
        根据 intervention 的 theme、channel_mix、budget 和 outcomes 指标，
        推算对 perception 各维度的 delta。

        Phase A+ 规则：
        - theme 对应的维度得到正向推动
        - channel_mix 的渠道效能系数加权
        - budget 对数缩放（50k=1.0 基准，更大预算边际递减）
        - CTR/CVR 好 → social_proof 上升
        - 评论情感正 → 对应维度上升
        - ROAS 低 → price_sensitivity 可能上升
        """
        delta: Dict[str, float] = {d: 0.0 for d in PERCEPTION_DIMENSIONS}

        # Theme 映射（先应用，即使无 outcome 也有基线推动）
        theme = (intervention.theme or "").lower()
        primary_dim = THEME_DIM_MAP.get(theme)
        if primary_dim:
            delta[primary_dim] += 0.05  # 基线正向

        if not outcomes:
            # 应用渠道和预算缩放后 clamp 返回
            delta = self._apply_channel_scaling(delta, intervention.channel_mix, market=market)
            delta = self._apply_budget_scaling(delta, intervention.budget)
            for k in delta:
                delta[k] = round(max(-0.3, min(0.3, delta[k])), 4)
            return delta

        # 聚合 outcome 指标
        avg_ctr = _avg([o.ctr for o in outcomes if o.ctr is not None])
        avg_cvr = _avg([o.cvr for o in outcomes if o.cvr is not None])
        avg_roas = _avg([o.roas for o in outcomes if o.roas is not None])
        avg_sentiment = _avg([o.comment_sentiment for o in outcomes if o.comment_sentiment is not None])
        avg_brand_lift = _avg([o.brand_lift for o in outcomes if o.brand_lift is not None])
        avg_search_delta = _avg([o.search_trend_delta for o in outcomes if o.search_trend_delta is not None])

        # 指标驱动的调整
        if avg_brand_lift is not None:
            if primary_dim:
                delta[primary_dim] += avg_brand_lift * 0.3
            else:
                delta["social_proof"] += avg_brand_lift * 0.2

        if avg_search_delta is not None:
            delta["social_proof"] += avg_search_delta * 0.15

        if avg_sentiment is not None:
            if avg_sentiment > 0:
                delta["social_proof"] += avg_sentiment * 0.1
                if primary_dim:
                    delta[primary_dim] += avg_sentiment * 0.05
            else:
                delta["skepticism"] += abs(avg_sentiment) * 0.1

        if avg_ctr is not None and avg_ctr > 0.03:
            delta["social_proof"] += 0.02

        if avg_cvr is not None and avg_cvr > 0.02:
            delta["comfort_trust"] += 0.01

        if avg_roas is not None and avg_roas < 1.0:
            delta["price_sensitivity"] += 0.03

        # 渠道效能加权 + 预算缩放
        delta = self._apply_channel_scaling(delta, intervention.channel_mix, market=market)
        delta = self._apply_budget_scaling(delta, intervention.budget)

        # Clamp deltas
        for k in delta:
            delta[k] = round(max(-0.3, min(0.3, delta[k])), 4)

        return delta

    # ------------------------------------------------------------------
    # 渠道效能 + 预算缩放
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_channel_scaling(
        delta: Dict[str, float],
        channel_mix: Optional[List[str]],
        market: str = "cn",
    ) -> Dict[str, float]:
        """
        根据 channel_mix 中各渠道的效能系数，加权调整 delta。
        多渠道取各渠道系数的平均值。
        最后叠加 market 调节系数。
        """
        if not channel_mix:
            # 即使没有渠道，仍然应用 market 调节
            if market and market != "cn":
                mkt = MARKET_ADJUSTMENTS.get(market, {})
                if mkt:
                    result = dict(delta)
                    for dim in PERCEPTION_DIMENSIONS:
                        result[dim] = result[dim] * mkt.get(dim, 1.0)
                    return result
            return delta

        # 收集各渠道对每个维度的系数
        dim_multipliers: Dict[str, List[float]] = {d: [] for d in PERCEPTION_DIMENSIONS}
        for ch in channel_mix:
            ch_lower = ch.lower().strip()
            eff = CHANNEL_EFFECTIVENESS.get(ch_lower, {})
            for dim in PERCEPTION_DIMENSIONS:
                dim_multipliers[dim].append(eff.get(dim, 1.0))

        # 取平均后应用
        result = dict(delta)
        for dim in PERCEPTION_DIMENSIONS:
            mults = dim_multipliers[dim]
            if mults:
                avg_mult = sum(mults) / len(mults)
                result[dim] = result[dim] * avg_mult

        # Layer 3: 市场调节
        if market and market != "cn":
            mkt = MARKET_ADJUSTMENTS.get(market, {})
            for dim in PERCEPTION_DIMENSIONS:
                if dim in mkt:
                    result[dim] = result[dim] * mkt[dim]

        return result

    @staticmethod
    def _apply_budget_scaling(
        delta: Dict[str, float],
        budget: Optional[float],
    ) -> Dict[str, float]:
        """
        预算对数缩放：budget=50000 时 multiplier=1.0。
        更大预算边际递减（log2 scale），更小预算效果打折。
        公式: multiplier = log2(budget / baseline + 1)
        """
        if not budget or budget <= 0:
            return delta

        multiplier = math.log2(budget / BUDGET_BASELINE + 1)
        # 限制范围 [0.3, 2.0]，防止极端值
        multiplier = max(0.3, min(2.0, multiplier))

        return {k: v * multiplier for k, v in delta.items()}

    # ------------------------------------------------------------------
    # 回放：用历史数据重建状态时间线
    # ------------------------------------------------------------------

    def replay_history(
        self,
        product_line: str = "moodyplus",
        audience_segment: str = "general",
        initial_state: Optional[BrandState] = None,
        market: str = "cn",
    ) -> List[BrandState]:
        """
        按时间顺序回放所有历史 intervention，
        生成一条 BrandState 时间线。

        幂等：使用基于 intervention_id 的确定性 ID，
        多次 replay 同一批数据不会产生重复行。
        按 product_line + audience_segment + market 过滤 intervention。
        """
        interventions = self.store.list_interventions()
        interventions = [
            iv for iv in interventions
            if iv.product_line == product_line
            and (iv.audience_segment or "general") == audience_segment
            and (iv.market or "cn") == market
        ]
        interventions.sort(key=lambda iv: iv.date_start or "")

        if not interventions:
            return []

        # 预加载竞品事件（按日期排序，按 market 过滤）
        competitor_events = self.store.list_competitor_events(market=market)

        # 初始状态（确定性 ID）
        if initial_state is None:
            first_date = interventions[0].date_start or "2025-01-01"
            initial_state = self._build_state_from_signals_deterministic(
                as_of_date=first_date, product_line=product_line,
                audience_segment=audience_segment, market=market,
            )

        states = [initial_state]
        current = initial_state

        for iv in interventions:
            outcomes = self.store.list_outcomes(iv.intervention_id)
            raw_delta = self.compute_intervention_impact(iv, outcomes, market=market)

            # 叠加竞品事件（使用共享 helper）
            delta = self._inject_competitor_delta(
                raw_delta, iv.date_start, iv.date_end, competitor_events,
            )

            # 确定性 ID：基于 intervention_id + market 派生
            new_perception = current.perception.apply_delta(delta)
            new_date = iv.date_end or iv.date_start or current.as_of_date
            state_id = f"bs-after-{iv.intervention_id}-{market}"

            has_competitor = delta.get("competitor_pressure", 0) != raw_delta.get("competitor_pressure", 0)
            evidence = [f"intervention:{iv.intervention_id}"]
            if has_competitor:
                evidence.append("competitor_events_in_window")

            new_state = BrandState(
                state_id=state_id,
                as_of_date=new_date,
                product_line=product_line,
                audience_segment=audience_segment,
                market=market,
                perception=new_perception,
                confidence=min(0.9, current.confidence + 0.02),
                evidence_sources=evidence,
            )
            self.store.save_brand_state(new_state)

            # 确定性 transition ID
            tr = StateTransition(
                transition_id=f"tr-{iv.intervention_id}-{market}",
                intervention_id=iv.intervention_id,
                state_before_id=current.state_id,
                state_after_id=new_state.state_id,
                market=market,
                delta=delta,
                confidence=new_state.confidence,
                method="historical",
            )
            self.store.save_transition(tr)

            states.append(new_state)
            current = new_state

        return states

    @staticmethod
    def _compute_competitor_pressure(
        date_start: Optional[str],
        date_end: Optional[str],
        competitor_events: list,
    ) -> Dict[str, float]:
        """
        计算时间窗口内竞品事件对 competitor_pressure 的叠加影响。
        """
        if not date_start or not competitor_events:
            return {}

        end = date_end or date_start
        pressure = 0.0
        for ev in competitor_events:
            if ev.date and date_start <= ev.date <= end:
                impact = (ev.impact_estimate or "low").lower()
                pressure += COMPETITOR_IMPACT_MAP.get(impact, 0.02)

        if pressure < 0.001:
            return {}

        # Clamp 竞品压力增量
        pressure = min(0.15, pressure)
        return {"competitor_pressure": round(pressure, 4)}

    @staticmethod
    def _inject_competitor_delta(
        delta: Dict[str, float],
        date_start: Optional[str],
        date_end: Optional[str],
        competitor_events: list,
    ) -> Dict[str, float]:
        """
        共享 helper：将竞品事件压力注入到 delta 并重新 clamp。
        replay() 和 backtest() 都应使用此方法以保持口径一致。
        """
        comp = BrandStateEngine._compute_competitor_pressure(
            date_start, date_end, competitor_events,
        )
        if not comp:
            return delta
        result = dict(delta)
        for dim, v in comp.items():
            result[dim] = result.get(dim, 0.0) + v
        for k in result:
            result[k] = round(max(-0.3, min(0.3, result[k])), 4)
        return result

    def _build_state_from_signals_deterministic(
        self,
        as_of_date: str,
        product_line: str = "moodyplus",
        audience_segment: str = "general",
        market: str = "cn",
    ) -> BrandState:
        """
        build_state_from_signals 的幂等版本，复用同一套 decay 逻辑，
        只将 state_id 替换为确定性 ID（含 market 以防跨市场覆盖）。
        """
        det_id = f"bs-initial-{product_line}-{audience_segment}-{market}"
        state = self._compute_state_from_signals(
            det_id, as_of_date, product_line, audience_segment, market=market,
        )
        self.store.save_brand_state(state)
        return state

    # ------------------------------------------------------------------
    # 预测：给定干预计划，预估状态变化
    # ------------------------------------------------------------------

    def predict_impact(
        self,
        intervention_plan: Dict[str, Any],
        base_state: Optional[BrandState] = None,
        product_line: str = "moodyplus",
        audience_segment: str = "general",
        market: str = "cn",
    ) -> Dict[str, Any]:
        """
        给定一个干预计划（theme、channel_mix、budget 等），
        基于历史模式预估对 BrandState 的影响。

        返回：
        {
          "current_state": {...},
          "predicted_state": {...},
          "delta": {...},
          "confidence": float,
          "reasoning": str,
        }
        """
        # 获取当前状态
        if base_state is None:
            base_state = self.store.get_latest_brand_state(product_line, audience_segment, market=market)
        if base_state is None:
            base_state = BrandState(
                state_id="default",
                as_of_date="2025-01-01",
                product_line=product_line,
                audience_segment=audience_segment,
                market=market,
            )

        # 查找历史上相似 theme 的干预效果
        theme = intervention_plan.get("theme", "")
        if not theme or not theme.strip():
            raise ValueError("intervention_plan 必须包含 theme 参数")
        historical = self._find_similar_interventions(theme, product_line, audience_segment, market=market)

        if historical:
            # 基于历史均值预估
            all_deltas = []
            for iv, outcomes in historical:
                d = self.compute_intervention_impact(iv, outcomes, market=market)
                all_deltas.append(d)

            avg_delta = {dim: 0.0 for dim in PERCEPTION_DIMENSIONS}
            for d in all_deltas:
                for dim in PERCEPTION_DIMENSIONS:
                    avg_delta[dim] += d.get(dim, 0.0)
            for dim in avg_delta:
                avg_delta[dim] = round(avg_delta[dim] / len(all_deltas), 4)

            confidence = min(0.8, 0.3 + 0.1 * len(historical))
            reasoning = f"基于 {len(historical)} 条历史相似干预的平均效果"
        else:
            # 无历史数据，用默认启发式（传入渠道和预算以应用缩放）
            dummy_iv = HistoricalIntervention(
                intervention_id="predict",
                run_id="predict",
                theme=theme,
                product_line=product_line,
                channel_mix=intervention_plan.get("channel_mix"),
                budget=intervention_plan.get("budget"),
            )
            avg_delta = self.compute_intervention_impact(dummy_iv, [], market=market)
            confidence = 0.2
            reasoning = "无历史数据，基于主题启发式估算"

        predicted_perception = base_state.perception.apply_delta(avg_delta)

        return {
            "current_state": base_state.to_dict(),
            "predicted_state": {
                "perception": predicted_perception.to_dict(),
                "as_of_date": intervention_plan.get("date_end", base_state.as_of_date),
            },
            "delta": avg_delta,
            "confidence": confidence,
            "reasoning": reasoning,
            "similar_interventions": len(historical) if historical else 0,
        }

    def predict_with_diffusion(
        self,
        intervention_plan: Dict[str, Any],
        base_state: Optional[BrandState] = None,
        product_line: str = "moodyplus",
        audience_segment: str = "general",
        market: str = "cn",
        diffusion_rounds: int = 6,
        diffusion_seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        predict_impact + agent diffusion 增强。

        规则维度（science_credibility / comfort_trust / aesthetic_affinity / price_sensitivity）
        仍由 predict_impact 的历史+规则引擎计算。

        不确定维度（social_proof / skepticism / competitor_pressure）
        由 agent diffusion 仿真叠加调整。

        返回包含 predict_impact 的所有字段 + diffusion 详情。
        """
        from .agent_diffusion import (
            AgentDiffusionEngine, resolve_channel_families, compute_budget_exposure_strength,
        )

        # 先跑标准 predict
        result = self.predict_impact(
            intervention_plan, base_state, product_line, audience_segment, market,
        )
        rule_delta = result["delta"]

        # 准备 diffusion 参数
        current_perception = result["current_state"]["perception"]
        raw_platforms = intervention_plan.get("channel_mix") or []
        channel_families = resolve_channel_families(raw_platforms)
        exposure_strength = compute_budget_exposure_strength(intervention_plan.get("budget"))

        # 运行 diffusion（传入 platforms 以启用 platform-level 差异化）
        diffusion_engine = AgentDiffusionEngine(seed=diffusion_seed)
        diff_result = diffusion_engine.simulate(
            intervention_plan=intervention_plan,
            current_state=current_perception,
            channel_families=channel_families,
            rounds=diffusion_rounds,
            exposure_strength=exposure_strength,
            platforms=raw_platforms,
        )

        # 合并 delta：规则维度用 rule_delta，不确定维度混合
        # 混合策略：agent_delta 作为修正项叠加（权重 0.5）
        agent_delta = diff_result["agent_delta"]
        merged_delta = dict(rule_delta)
        for d in ["social_proof", "skepticism", "competitor_pressure"]:
            merged_delta[d] = round(rule_delta.get(d, 0.0) + agent_delta.get(d, 0.0) * 0.5, 4)
            merged_delta[d] = max(-0.3, min(0.3, merged_delta[d]))

        # 用 merged delta 重新计算 predicted_state
        if base_state is None:
            base_state = self.store.get_latest_brand_state(product_line, audience_segment, market=market)
        if base_state is None:
            base_state = BrandState(
                state_id="default", as_of_date="2025-01-01",
                product_line=product_line, audience_segment=audience_segment, market=market,
            )
        merged_perception = base_state.perception.apply_delta(merged_delta)

        result["delta"] = merged_delta
        result["predicted_state"]["perception"] = merged_perception.to_dict()
        result["diffusion"] = {
            "agent_delta": agent_delta,
            "rule_delta": {d: rule_delta.get(d, 0.0) for d in ["social_proof", "skepticism", "competitor_pressure"]},
            "agent_count": diff_result["agent_count"],
            "rounds": diff_result["rounds"],
            "convergence_round": diff_result["convergence_round"],
            "archetype_breakdown": diff_result["archetype_breakdown"],
        }
        # Only boost confidence if diffusion actually produced non-zero deltas
        has_nonzero_agent = any(abs(v) > 1e-6 for v in agent_delta.values())
        if has_nonzero_agent:
            result["confidence"] = min(0.9, result["confidence"] + 0.05)
            result["reasoning"] += " + agent diffusion 仿真"

        return result

    def _find_similar_interventions(
        self, theme: str, product_line: str, audience_segment: str = "general",
        market: str = "cn",
    ) -> List[tuple]:
        """查找历史上相同 theme + segment + market 的干预及其 outcomes"""
        if not theme or not theme.strip():
            return []
        all_ivs = self.store.list_interventions()
        results = []
        theme_lower = theme.lower()
        for iv in all_ivs:
            if iv.product_line != product_line:
                continue
            if (iv.audience_segment or "general") != audience_segment:
                continue
            if (iv.market or "cn") != market:
                continue
            iv_theme = (iv.theme or "").lower()
            if iv_theme and _themes_match(theme_lower, iv_theme):
                outcomes = self.store.list_outcomes(iv.intervention_id)
                results.append((iv, outcomes))
        return results

    # ------------------------------------------------------------------
    # 认知路径概率板
    # ------------------------------------------------------------------

    def cognition_probability_board(
        self,
        intervention_plans: List[Dict[str, Any]],
        product_line: str = "moodyplus",
        audience_segment: str = "general",
        market: str = "cn",
    ) -> Dict[str, Any]:
        """
        认知路径概率板 — Phase A 的核心输出。

        输入多个干预计划（不同认知路径），输出每条路径的预估效果对比。

        返回：
        {
          "current_state": {...},
          "paths": [
            {
              "plan": {...},
              "predicted_delta": {...},
              "predicted_state": {...},
              "confidence": float,
              "reasoning": str,
              "dimension_impacts": {...},  # 每个维度的影响方向和幅度
            },
            ...
          ],
          "recommendation": str,
        }
        """
        base_state = self.store.get_latest_brand_state(product_line, audience_segment, market=market)
        if base_state is None:
            base_state = BrandState(
                state_id="default",
                as_of_date="2025-01-01",
                product_line=product_line,
                audience_segment=audience_segment,
                market=market,
            )

        paths = []
        for plan in intervention_plans:
            prediction = self.predict_impact(plan, base_state, product_line, audience_segment, market=market)
            delta = prediction["delta"]

            # 按影响幅度排序维度
            dimension_impacts = {}
            for dim in PERCEPTION_DIMENSIONS:
                v = delta.get(dim, 0.0)
                if abs(v) > 0.001:
                    direction = "↑" if v > 0 else "↓"
                    dimension_impacts[dim] = {
                        "delta": v,
                        "direction": direction,
                        "magnitude": "strong" if abs(v) >= 0.05 else "moderate" if abs(v) >= 0.02 else "weak",
                    }

            paths.append({
                "plan": plan,
                "predicted_delta": delta,
                "predicted_state": prediction["predicted_state"],
                "confidence": prediction["confidence"],
                "reasoning": prediction["reasoning"],
                "dimension_impacts": dimension_impacts,
            })

        # 简单推荐逻辑：选 confidence × 正向总 delta 最大的
        recommendation = ""
        if paths:
            scored = []
            for i, p in enumerate(paths):
                positive_delta = sum(
                    v for k, v in p["predicted_delta"].items()
                    if v > 0 and k != "skepticism" and k != "price_sensitivity"
                )
                scored.append((positive_delta * p["confidence"], i))
            scored.sort(reverse=True)
            best_score = scored[0][0]
            best_idx = scored[0][1]
            best_plan = paths[best_idx]["plan"]
            if best_score > 0.001:
                recommendation = (
                    f"建议优先 \"{best_plan.get('theme', '未命名')}\" 路径，"
                    f"预计对品牌认知有正向影响"
                )
            else:
                recommendation = "当前各路径预估影响接近零，建议补充历史数据后再做判断"

        return {
            "current_state": base_state.to_dict(),
            "paths": paths,
            "recommendation": recommendation,
        }

    # ------------------------------------------------------------------
    # 多步情景模拟
    # ------------------------------------------------------------------

    def simulate_scenario(
        self,
        steps: List[Dict[str, Any]],
        product_line: str = "moodyplus",
        audience_segment: str = "general",
        base_state: Optional[BrandState] = None,
        scenario_id: Optional[str] = None,
        market: str = "cn",
    ) -> Dict[str, Any]:
        """
        模拟一系列计划干预的累积效果。

        steps: [
          {"theme": "science", "channel_mix": ["bilibili"], "budget": 50000,
           "date_start": "2025-07-01", "date_end": "2025-07-31"},
          {"theme": "comfort", "channel_mix": ["redbook"], "budget": 80000,
           "date_start": "2025-08-01", "date_end": "2025-08-31"},
        ]

        返回：
        {
          "scenario_id": str,
          "initial_state": {...},
          "timeline": [
            {"step": 0, "plan": {...}, "delta": {...}, "state_after": {...}, "confidence": float},
            ...
          ],
          "final_state": {...},
          "cumulative_delta": {...},
        }
        """
        if not steps:
            raise ValueError("scenario steps 不能为空")

        for i, step in enumerate(steps):
            if not (step.get("theme") or "").strip():
                raise ValueError(f"steps[{i}] 缺少 theme 参数")

        if base_state is None:
            base_state = self.store.get_latest_brand_state(product_line, audience_segment, market=market)
        if base_state is None:
            base_state = BrandState(
                state_id="default",
                as_of_date="2025-01-01",
                product_line=product_line,
                audience_segment=audience_segment,
                market=market,
            )

        sid = scenario_id or f"sc-{str(uuid.uuid4())[:8]}"
        current = base_state
        timeline = []
        cumulative_delta = {d: 0.0 for d in PERCEPTION_DIMENSIONS}

        for i, step in enumerate(steps):
            prediction = self.predict_impact(
                step, base_state=current,
                product_line=product_line,
                audience_segment=audience_segment,
                market=market,
            )
            delta = prediction["delta"]

            # 累积
            for d in PERCEPTION_DIMENSIONS:
                cumulative_delta[d] += delta.get(d, 0.0)

            # 用预测的 perception 构建下一步的 base_state
            new_perception = current.perception.apply_delta(delta)
            step_date = step.get("date_end", step.get("date_start", current.as_of_date))
            next_state = BrandState(
                state_id=f"{sid}-step-{i}",
                as_of_date=step_date,
                product_line=product_line,
                audience_segment=audience_segment,
                perception=new_perception,
                confidence=prediction["confidence"],
            )

            timeline.append({
                "step": i,
                "plan": step,
                "delta": delta,
                "state_after": {
                    "perception": new_perception.to_dict(),
                    "as_of_date": step_date,
                },
                "confidence": prediction["confidence"],
                "reasoning": prediction["reasoning"],
            })
            current = next_state

        # Round cumulative
        for d in cumulative_delta:
            cumulative_delta[d] = round(cumulative_delta[d], 4)

        return {
            "scenario_id": sid,
            "initial_state": base_state.to_dict(),
            "timeline": timeline,
            "final_state": {
                "perception": current.perception.to_dict(),
                "as_of_date": current.as_of_date,
            },
            "cumulative_delta": cumulative_delta,
            "steps_count": len(steps),
        }

    def compare_scenarios(
        self,
        scenarios: List[Dict[str, Any]],
        product_line: str = "moodyplus",
        audience_segment: str = "general",
        market: str = "cn",
    ) -> Dict[str, Any]:
        """
        并排比较多条情景时间线。

        scenarios: [
          {
            "name": "重科普路线",
            "steps": [{"theme": "science", ...}, ...]
          },
          {
            "name": "颜值种草路线",
            "steps": [{"theme": "beauty", ...}, ...]
          }
        ]

        返回每条情景的最终状态 + 排名 + 推荐。
        """
        if not scenarios:
            raise ValueError("scenarios 不能为空")

        base_state = self.store.get_latest_brand_state(product_line, audience_segment, market=market)
        if base_state is None:
            base_state = BrandState(
                state_id="default",
                as_of_date="2025-01-01",
                product_line=product_line,
                audience_segment=audience_segment,
                market=market,
            )

        results = []
        for idx, sc in enumerate(scenarios):
            name = sc.get("name", f"scenario_{idx}")
            steps = sc.get("steps", [])
            if not steps:
                results.append({
                    "name": name,
                    "error": "steps 为空",
                })
                continue

            try:
                sim = self.simulate_scenario(
                    steps=steps,
                    product_line=product_line,
                    audience_segment=audience_segment,
                    base_state=base_state,
                    scenario_id=f"cmp-{idx}",
                    market=market,
                )
                # 打分：正向 delta 总和 × 平均 confidence
                cd = sim["cumulative_delta"]
                positive_delta = sum(
                    v for k, v in cd.items()
                    if v > 0 and k != "skepticism" and k != "price_sensitivity"
                )
                # scenario-level confidence = timeline 各步 confidence 的平均值
                step_confidences = [s["confidence"] for s in sim["timeline"]]
                avg_confidence = (
                    sum(step_confidences) / len(step_confidences)
                    if step_confidences else 0.2
                )
                score = positive_delta * avg_confidence
                results.append({
                    "name": name,
                    "final_state": sim["final_state"],
                    "cumulative_delta": cd,
                    "steps_count": sim["steps_count"],
                    "score": round(score, 4),
                    "confidence": round(avg_confidence, 4),
                    "timeline": sim["timeline"],
                })
            except Exception as e:
                results.append({
                    "name": name,
                    "error": str(e),
                })

        # 排序
        valid = [r for r in results if "error" not in r]
        valid.sort(key=lambda r: r["score"], reverse=True)
        for rank, r in enumerate(valid, 1):
            r["rank"] = rank

        # 推荐
        recommendation = ""
        if valid and valid[0]["score"] > 0.001:
            recommendation = (
                f"建议采用 \"{valid[0]['name']}\" 路线，"
                f"预计累积正向认知提升最大（score={valid[0]['score']:.3f}）"
            )
        elif valid:
            recommendation = "各路线预估累积影响接近零，建议补充历史数据后再做判断"

        return {
            "current_state": base_state.to_dict(),
            "scenarios": results,
            "recommendation": recommendation,
        }

    # ------------------------------------------------------------------
    # 回测验证
    # ------------------------------------------------------------------

    def backtest(
        self,
        product_line: str = "moodyplus",
        audience_segment: str = "general",
        market: str = "cn",
    ) -> Dict[str, Any]:
        """
        留一法回测：依次将每个 intervention 作为 holdout，
        用其余数据的模式预测它的 delta，
        然后与实际观测到的 delta 比较。

        返回：
        {
          "total_interventions": int,
          "tested": int,      # 有 outcome 的才能测
          "skipped": int,     # theme 为空 or 无 outcome
          "mean_absolute_error": float,  # 各维度绝对误差的均值
          "per_dimension_mae": {...},
          "details": [...]    # 每条的预测 vs 实际
        }
        """
        interventions = self.store.list_interventions()
        interventions = [
            iv for iv in interventions
            if iv.product_line == product_line
            and (iv.audience_segment or "general") == audience_segment
            and (iv.market or "cn") == market
        ]

        # 预加载竞品事件（与 replay 共享同一套逻辑，按 market 过滤）
        competitor_events = self.store.list_competitor_events(market=market)

        details = []
        dim_errors: Dict[str, List[float]] = {d: [] for d in PERCEPTION_DIMENSIONS}
        skipped = 0

        for i, holdout in enumerate(interventions):
            # 跳过无 theme 或无 outcome 的
            theme = (holdout.theme or "").strip()
            if not theme:
                skipped += 1
                continue

            outcomes = self.store.list_outcomes(holdout.intervention_id)
            if not outcomes:
                skipped += 1
                continue

            # 实际 delta（来自真实 outcome + 竞品事件，与 replay 共享 helper）
            raw_actual = self.compute_intervention_impact(holdout, outcomes, market=market)
            actual_delta = self._inject_competitor_delta(
                raw_actual, holdout.date_start, holdout.date_end, competitor_events,
            )

            # 预测 delta：用除 holdout 外的同 theme 干预
            similar = []
            for j, iv in enumerate(interventions):
                if j == i:
                    continue
                iv_theme = (iv.theme or "").lower()
                if iv_theme and _themes_match(theme.lower(), iv_theme):
                    iv_outcomes = self.store.list_outcomes(iv.intervention_id)
                    if iv_outcomes:
                        similar.append((iv, iv_outcomes))

            if similar:
                pred_deltas = []
                for iv, oc in similar:
                    d = self.compute_intervention_impact(iv, oc, market=market)
                    d = self._inject_competitor_delta(
                        d, iv.date_start, iv.date_end, competitor_events,
                    )
                    pred_deltas.append(d)
                predicted = {d: 0.0 for d in PERCEPTION_DIMENSIONS}
                for pd in pred_deltas:
                    for d in PERCEPTION_DIMENSIONS:
                        predicted[d] += pd.get(d, 0.0)
                for d in predicted:
                    predicted[d] = round(predicted[d] / len(pred_deltas), 4)
                method = "historical_average"
            else:
                dummy = HistoricalIntervention(
                    intervention_id="bt", run_id="bt",
                    theme=theme, product_line=product_line,
                    channel_mix=holdout.channel_mix,
                    budget=holdout.budget,
                )
                predicted = self.compute_intervention_impact(dummy, [], market=market)
                predicted = self._inject_competitor_delta(
                    predicted, holdout.date_start, holdout.date_end, competitor_events,
                )
                method = "heuristic_fallback"

            # 计算每维度绝对误差
            errors = {}
            for d in PERCEPTION_DIMENSIONS:
                err = abs(predicted.get(d, 0.0) - actual_delta.get(d, 0.0))
                errors[d] = round(err, 4)
                dim_errors[d].append(err)

            details.append({
                "intervention_id": holdout.intervention_id,
                "theme": theme,
                "method": method,
                "similar_count": len(similar),
                "actual_delta": actual_delta,
                "predicted_delta": predicted,
                "absolute_errors": errors,
                "mean_error": round(sum(errors.values()) / len(errors), 4),
            })

        # 汇总
        per_dim_mae = {}
        all_errors = []
        for d in PERCEPTION_DIMENSIONS:
            if dim_errors[d]:
                mae = sum(dim_errors[d]) / len(dim_errors[d])
                per_dim_mae[d] = round(mae, 4)
                all_errors.extend(dim_errors[d])

        overall_mae = round(sum(all_errors) / len(all_errors), 4) if all_errors else 0.0

        return {
            "total_interventions": len(interventions),
            "tested": len(details),
            "skipped": skipped,
            "mean_absolute_error": overall_mae,
            "per_dimension_mae": per_dim_mae,
            "details": details,
        }


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _themes_match(query: str, candidate: str) -> bool:
    """
    判断两个 theme 是否匹配。
    精确匹配或 token 级包含（用 _ 分词），不做单字符子串匹配。
    例如: "science" 匹配 "science_credibility"，但 "s" 不匹配 "science"。
    """
    if query == candidate:
        return True
    query_tokens = set(query.split("_"))
    candidate_tokens = set(candidate.split("_"))
    # query 的所有 token 都出现在 candidate 中（且每个 token 至少 3 字符）
    if all(len(t) >= 3 for t in query_tokens) and query_tokens <= candidate_tokens:
        return True
    if all(len(t) >= 3 for t in candidate_tokens) and candidate_tokens <= query_tokens:
        return True
    return False


def _avg(values: list) -> Optional[float]:
    """安全平均值"""
    valid = [v for v in values if v is not None]
    return sum(valid) / len(valid) if valid else None


def _parse_date(date_str: str) -> Optional[datetime]:
    """尝试解析 ISO 日期字符串"""
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _decay_weight(date_str: str, ref_date: datetime) -> float:
    """
    计算时间衰减权重：exp(-lambda * days_ago)
    半衰期 = SIGNAL_HALF_LIFE_DAYS 天，lambda = ln(2) / half_life
    """
    d = _parse_date(date_str)
    if d is None:
        return 1.0
    days_ago = (ref_date - d).days
    if days_ago <= 0:
        return 1.0
    lam = math.log(2) / SIGNAL_HALF_LIFE_DAYS
    return math.exp(-lam * days_ago)
