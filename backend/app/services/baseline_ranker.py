"""
Historical Baseline Ranker — 轨道 1：基于真实历史漏斗数据的 campaign 排序

不依赖感知模型、不使用手拍系数。
排序依据 = 历史相似组的真实 outcome 指标（ROAS / CPA / CVR / sessions→purchases 等）。

统计口径：
  - 每个 intervention 的多个 outcome window 先聚合为单条记录（取最新 window 或加权合并）
  - 然后在 intervention 粒度做均值/方差/漂移
  - 季节标签匹配的样本权重 ×2（加权而非硬过滤，避免稀疏）

核心方法:
  - query_baseline()  → 查历史相似组，返回指标统计
  - rank_campaigns()  → 多 plan 对比排序

冷启动策略（当同品类无数据时）：
  - 跨品类迁移：放宽 product_line，结果标记 cross_category，指标 ×0.7 折扣
  - 全量分位数：用全部历史数据的 P25/P50/P75 给出范围估计
"""

import math
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Tuple

from ..models.brandiction import HistoricalIntervention, HistoricalOutcomeWindow
from .brandiction_store import BrandictionStore


# ------------------------------------------------------------------
# 合法排序字段 & 常量
# ------------------------------------------------------------------

VALID_SORT_FIELDS = frozenset({
    "roas_mean", "purchase_rate", "revenue_mean", "cvr_mean",
    "ctr_mean", "aov_mean", "sessions_mean", "cpa",
})

# 季节匹配时同 season 的权重倍数（其他 season 权重 ×1）
_SEASON_WEIGHT_BOOST = 2.0

# 跨品类迁移的折扣系数
_CROSS_CATEGORY_DISCOUNT = 0.7

# 合法 season_tag 值
VALID_SEASON_TAGS = frozenset({"618", "double11", "cny", "regular", "38", "99"})


@dataclass
class BaselineStats:
    """一组历史 outcome 的统计摘要"""
    sample_size: int = 0

    # 广告指标
    roas_mean: Optional[float] = None
    roas_std: Optional[float] = None
    ctr_mean: Optional[float] = None
    cvr_mean: Optional[float] = None
    cpa: Optional[float] = None           # spend / purchases

    # DTC 漏斗
    sessions_mean: Optional[float] = None
    purchase_rate: Optional[float] = None  # purchases / sessions
    aov_mean: Optional[float] = None
    revenue_mean: Optional[float] = None

    # 漂移（近 30/60/90 天 vs 全量）
    drift_30d: Optional[Dict[str, float]] = None
    drift_60d: Optional[Dict[str, float]] = None
    drift_90d: Optional[Dict[str, float]] = None

    # 季节漂移
    seasonal_drift: Optional[Dict[str, Any]] = None

    # 冷启动提示
    cold_start_hint: Optional[Dict[str, Any]] = None

    # 匹配信息
    match_dimensions: List[str] = field(default_factory=list)
    match_quality: str = "exact"  # exact | partial | fallback | cross_category | cold_start | no_data

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class _AggregatedOutcome:
    """单个 intervention 的聚合 outcome（多 window 合并后）"""
    intervention_id: str
    season_tag: Optional[str] = None       # 季节标签
    date_start: Optional[str] = None       # intervention 开始日期
    latest_outcome_date: Optional[str] = None  # 最新 outcome window 日期（用于 drift）
    spend: Optional[float] = None
    weight: float = 1.0                    # 季节加权权重
    # 聚合后的指标（取最新 window 或加权）
    roas: Optional[float] = None
    ctr: Optional[float] = None
    cvr: Optional[float] = None
    sessions: Optional[int] = None
    purchases: Optional[int] = None
    aov: Optional[float] = None
    revenue: Optional[float] = None


class HistoricalBaselineRanker:
    """基于真实历史数据的 campaign plan 排序引擎"""

    def __init__(self, store: BrandictionStore = None):
        self.store = store or BrandictionStore()

    # ------------------------------------------------------------------
    # 核心：查历史相似组
    # ------------------------------------------------------------------

    def query_baseline(
        self,
        plan: Dict[str, Any],
        product_line: str = "moodyplus",
        audience_segment: str = "general",
        min_samples: int = 2,
        season_tag: Optional[str] = None,
    ) -> BaselineStats:
        """
        给定一个 campaign plan，查找历史相似组并返回 outcome 统计。

        匹配策略（在硬过滤后逐步放宽）：
        1. platform + channel_family + theme + landing_page
        2. platform + channel_family + theme
        3. channel_family + theme
        4. platform + channel_family
        5. channel_family
        6. （仅硬过滤）

        如果同品类无数据，依次尝试：
        7. 跨品类迁移（match_quality=cross_category）
        8. 全量分位数估计（match_quality=cold_start）
        """
        # --- 阶段 1：同品类匹配 ---
        stats = self._query_same_category(
            plan, product_line, audience_segment, min_samples, season_tag,
        )
        if stats.sample_size > 0:
            return stats

        # --- 阶段 2：跨品类迁移 ---
        stats = self._query_cross_category(
            plan, product_line, audience_segment, min_samples, season_tag,
        )
        if stats.sample_size > 0:
            return stats

        # --- 阶段 3：全量分位数冷启动 ---
        return self._cold_start_estimate(plan)

    def _query_same_category(
        self,
        plan: Dict[str, Any],
        product_line: str,
        audience_segment: str,
        min_samples: int,
        season_tag: Optional[str],
    ) -> BaselineStats:
        """同品类内逐步松弛匹配。"""
        plan_market = (plan.get("market") or "").strip().lower()
        interventions = self.store.list_interventions()
        filtered = []
        for iv in interventions:
            if iv.product_line != product_line:
                continue
            if (iv.audience_segment or "general") != audience_segment:
                continue
            if plan_market and (iv.market or "cn").lower() != plan_market:
                continue
            filtered.append(iv)

        all_outcomes = {}
        for iv in filtered:
            all_outcomes[iv.intervention_id] = self.store.list_outcomes(iv.intervention_id)

        match_levels = [
            ("platform", "channel_family", "theme", "landing_page"),
            ("platform", "channel_family", "theme"),
            ("channel_family", "theme"),
            ("platform", "channel_family"),
            ("channel_family",),
            (),
        ]

        _SOFT_DIMS = ("platform", "channel_family", "theme", "landing_page")
        plan_specified = tuple(
            d for d in _SOFT_DIMS
            if (plan.get(d) or "").strip()
        )

        for dims in match_levels:
            matched = self._match_interventions(plan, filtered, all_outcomes, dims)
            if len(matched) >= min_samples:
                agg = [
                    self._aggregate_outcome(iv, ocs, season_tag)
                    for iv, ocs in matched
                ]
                stats = self._compute_stats_weighted(agg)
                hard_dims = ["product_line", "audience_segment"]
                if plan_market:
                    hard_dims.append("market")
                effective_soft = [d for d in dims if d in plan_specified]
                stats.match_dimensions = hard_dims + effective_soft
                n_specified = len(plan_specified)
                n_matched = len(effective_soft)
                if n_specified == 0:
                    stats.match_quality = "fallback"
                elif n_matched >= n_specified:
                    stats.match_quality = "exact"
                elif n_matched >= 1:
                    stats.match_quality = "partial"
                else:
                    stats.match_quality = "fallback"
                stats.drift_30d = self._compute_drift(agg, days=30)
                stats.drift_60d = self._compute_drift(agg, days=60)
                stats.drift_90d = self._compute_drift(agg, days=90)
                if season_tag:
                    stats.seasonal_drift = self._compute_seasonal_drift(agg, season_tag)
                return stats

        return BaselineStats(sample_size=0, match_dimensions=[], match_quality="no_data")

    def _query_cross_category(
        self,
        plan: Dict[str, Any],
        original_product_line: str,
        audience_segment: str,
        min_samples: int,
        season_tag: Optional[str],
    ) -> BaselineStats:
        """跨品类迁移：放宽 product_line，结果打折扣。"""
        plan_market = (plan.get("market") or "").strip().lower()
        interventions = self.store.list_interventions()
        filtered = []
        for iv in interventions:
            # 跳过同品类（已经在阶段 1 查过了）
            if iv.product_line == original_product_line:
                continue
            # 保留 audience_segment 硬过滤
            if (iv.audience_segment or "general") != audience_segment:
                continue
            if plan_market and (iv.market or "cn").lower() != plan_market:
                continue
            filtered.append(iv)

        if not filtered:
            return BaselineStats(sample_size=0, match_dimensions=[], match_quality="no_data")

        all_outcomes = {}
        for iv in filtered:
            all_outcomes[iv.intervention_id] = self.store.list_outcomes(iv.intervention_id)

        # 只尝试较宽松的匹配维度
        match_levels = [
            ("channel_family", "theme"),
            ("channel_family",),
            (),
        ]

        for dims in match_levels:
            matched = self._match_interventions(plan, filtered, all_outcomes, dims)
            if len(matched) >= min_samples:
                agg = [
                    self._aggregate_outcome(iv, ocs, season_tag)
                    for iv, ocs in matched
                ]
                stats = self._compute_stats_weighted(agg)
                # 折扣：跨品类转化率/ROAS 不能直接等同
                stats = self._apply_discount(stats, _CROSS_CATEGORY_DISCOUNT)
                stats.match_quality = "cross_category"
                dims_list = ["cross_category"]
                dims_list.extend(d for d in dims if (plan.get(d) or "").strip())
                stats.match_dimensions = dims_list
                stats.cold_start_hint = {
                    "type": "cross_category",
                    "source_product_lines": list(set(
                        iv.product_line for iv, _ in matched
                    )),
                    "discount_applied": _CROSS_CATEGORY_DISCOUNT,
                    "note": "跨品类迁移数据，指标已乘折扣系数，仅供参考",
                }
                if season_tag:
                    stats.seasonal_drift = self._compute_seasonal_drift(agg, season_tag)
                return stats

        return BaselineStats(sample_size=0, match_dimensions=[], match_quality="no_data")

    def _cold_start_estimate(self, plan: Dict[str, Any]) -> BaselineStats:
        """全量数据分位数估计，作为最后兜底。"""
        interventions = self.store.list_interventions()
        all_outcomes = {}
        for iv in interventions:
            all_outcomes[iv.intervention_id] = self.store.list_outcomes(iv.intervention_id)

        agg_list = []
        for iv in interventions:
            ocs = all_outcomes.get(iv.intervention_id, [])
            if ocs:
                agg_list.append(self._aggregate_outcome(iv, ocs))

        if not agg_list:
            return BaselineStats(
                sample_size=0,
                match_dimensions=[],
                match_quality="no_data",
            )

        # 计算分位数范围
        roas_vals = sorted(a.roas for a in agg_list if a.roas is not None)
        cvr_vals = sorted(a.cvr for a in agg_list if a.cvr is not None)
        rev_vals = sorted(a.revenue for a in agg_list if a.revenue is not None)

        def _percentiles(vals: list) -> Optional[Dict[str, float]]:
            if len(vals) < 3:
                return None
            return {
                "p25": round(vals[len(vals) // 4], 3),
                "p50": round(vals[len(vals) // 2], 3),
                "p75": round(vals[3 * len(vals) // 4], 3),
            }

        stats = BaselineStats(
            sample_size=0,  # 0 表示这不是直接匹配
            match_dimensions=[],
            match_quality="cold_start",
        )
        stats.cold_start_hint = {
            "type": "distribution_estimate",
            "total_interventions_in_db": len(agg_list),
            "note": "无历史相似案例，以下是全量数据的分位数范围，仅供粗略参考",
            "roas_range": _percentiles(roas_vals),
            "cvr_range": _percentiles(cvr_vals),
            "revenue_range": _percentiles(rev_vals),
        }
        # 用 P50 作为 score 的 fallback（但 data_sufficient=False）
        if roas_vals:
            stats.roas_mean = round(roas_vals[len(roas_vals) // 2] * _CROSS_CATEGORY_DISCOUNT, 3)
        if cvr_vals:
            stats.cvr_mean = round(cvr_vals[len(cvr_vals) // 2] * _CROSS_CATEGORY_DISCOUNT, 4)

        return stats

    # ------------------------------------------------------------------
    # 排序：多 plan 对比
    # ------------------------------------------------------------------

    def rank_campaigns(
        self,
        plans: List[Dict[str, Any]],
        sort_by: str = "roas_mean",
        product_line: str = "moodyplus",
        audience_segment: str = "general",
        min_samples: int = 2,
        season_tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        给定多个 campaign plan，查历史基线并排序。

        sort_by 可选: roas_mean, purchase_rate, revenue_mean, cvr_mean,
                      ctr_mean, aov_mean, sessions_mean, cpa
        """
        if sort_by not in VALID_SORT_FIELDS:
            raise ValueError(
                f"sort_by 必须是 {', '.join(sorted(VALID_SORT_FIELDS))} 之一，"
                f"收到: {sort_by!r}"
            )

        entries = []
        for i, plan in enumerate(plans):
            baseline = self.query_baseline(
                plan,
                product_line=product_line,
                audience_segment=audience_segment,
                min_samples=min_samples,
                season_tag=season_tag,
            )
            score = self._score(baseline, sort_by)
            entries.append({
                "plan": plan,
                "observed_baseline": baseline.to_dict(),
                "score": score,
                "data_sufficient": baseline.sample_size >= min_samples,
            })

        entries.sort(key=lambda e: (e["data_sufficient"], e["score"]), reverse=True)
        for rank, e in enumerate(entries, 1):
            e["rank"] = rank

        recommendation = self._generate_recommendation(entries, sort_by)

        return {
            "ranking": entries,
            "sort_by": sort_by,
            "recommendation": recommendation,
        }

    # ------------------------------------------------------------------
    # Outcome 聚合：多 window → 单条 intervention 级记录
    # ------------------------------------------------------------------

    @staticmethod
    def _aggregate_outcome(
        iv: HistoricalIntervention,
        outcomes: List[HistoricalOutcomeWindow],
        season_tag: Optional[str] = None,
    ) -> _AggregatedOutcome:
        """
        将一个 intervention 的多个 outcome window 聚合为单条记录。
        如果指定了 season_tag 且 intervention 的 season_tag 匹配，weight 设为 BOOST。
        """
        weight = 1.0
        if season_tag and iv.season_tag:
            if iv.season_tag.lower() == season_tag.lower():
                weight = _SEASON_WEIGHT_BOOST

        agg = _AggregatedOutcome(
            intervention_id=iv.intervention_id,
            season_tag=iv.season_tag,
            date_start=iv.date_start,
            spend=iv.spend,
            weight=weight,
        )
        if not outcomes:
            return agg

        sorted_oc = sorted(outcomes, key=lambda o: o.date_start or "")
        agg.latest_outcome_date = sorted_oc[-1].date_start or iv.date_start

        # 累加型
        agg.sessions = _sum_non_none([o.sessions for o in sorted_oc])
        agg.purchases = _sum_non_none([o.purchases for o in sorted_oc])
        agg.revenue = _sum_non_none([o.revenue for o in sorted_oc])

        # 比率型：取最新有值的
        agg.roas = _latest_non_none([o.roas for o in sorted_oc])
        agg.ctr = _latest_non_none([o.ctr for o in sorted_oc])
        agg.cvr = _latest_non_none([o.cvr for o in sorted_oc])
        agg.aov = _latest_non_none([o.aov for o in sorted_oc])

        return agg

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    @staticmethod
    def _match_interventions(
        plan: Dict[str, Any],
        interventions: List[HistoricalIntervention],
        all_outcomes: Dict[str, List[HistoricalOutcomeWindow]],
        dims: Tuple[str, ...],
    ) -> List[Tuple[HistoricalIntervention, List[HistoricalOutcomeWindow]]]:
        """按指定维度匹配 intervention，只返回有 outcome 的。"""
        matched = []
        for iv in interventions:
            outcomes = all_outcomes.get(iv.intervention_id, [])
            if not outcomes:
                continue
            if not _fields_match(plan, iv, dims):
                continue
            matched.append((iv, outcomes))
        return matched

    @staticmethod
    def _compute_stats_weighted(aggregated: List[_AggregatedOutcome]) -> BaselineStats:
        """从 intervention 级聚合记录计算加权统计值。"""
        stats = BaselineStats(sample_size=len(aggregated))

        # ROAS (加权平均)
        roas_pairs = [(a.roas, a.weight) for a in aggregated if a.roas is not None]
        if roas_pairs:
            stats.roas_mean = round(_weighted_mean(roas_pairs), 3)
            vals = [v for v, _ in roas_pairs]
            stats.roas_std = round(_std(vals), 3) if len(vals) > 1 else 0.0

        # CTR
        ctr_pairs = [(a.ctr, a.weight) for a in aggregated if a.ctr is not None]
        if ctr_pairs:
            stats.ctr_mean = round(_weighted_mean(ctr_pairs), 4)

        # CVR
        cvr_pairs = [(a.cvr, a.weight) for a in aggregated if a.cvr is not None]
        if cvr_pairs:
            stats.cvr_mean = round(_weighted_mean(cvr_pairs), 4)

        # CPA = weighted(spend) / weighted(purchases) (intervention 级)
        total_spend = sum(a.spend * a.weight for a in aggregated if a.spend)
        total_purchases = sum(a.purchases * a.weight for a in aggregated if a.purchases)
        if total_spend > 0 and total_purchases > 0:
            stats.cpa = round(total_spend / total_purchases, 2)

        # Sessions (加权平均)
        sess_pairs = [(a.sessions, a.weight) for a in aggregated if a.sessions is not None]
        if sess_pairs:
            stats.sessions_mean = round(_weighted_mean(sess_pairs), 1)

        # Purchase rate = weighted(purchases) / weighted(sessions) (intervention 级)
        total_sessions = sum(a.sessions * a.weight for a in aggregated if a.sessions)
        if total_sessions > 0 and total_purchases > 0:
            stats.purchase_rate = round(total_purchases / total_sessions, 4)

        # AOV
        aov_pairs = [(a.aov, a.weight) for a in aggregated if a.aov is not None]
        if aov_pairs:
            stats.aov_mean = round(_weighted_mean(aov_pairs), 2)

        # Revenue (加权平均)
        rev_pairs = [(a.revenue, a.weight) for a in aggregated if a.revenue is not None]
        if rev_pairs:
            stats.revenue_mean = round(_weighted_mean(rev_pairs), 2)

        return stats

    @staticmethod
    def _compute_seasonal_drift(
        aggregated: List[_AggregatedOutcome],
        season_tag: str,
    ) -> Optional[Dict[str, Any]]:
        """对比指定 season 和 regular（非大促）的关键指标差异。

        只拿 season_tag == 'regular' 或无标签的样本作为对照组，
        排除其他大促季数据（如用户选 618，不会把 double11 混入 regular）。
        """
        in_season = [a for a in aggregated if (a.season_tag or "").lower() == season_tag.lower()]
        regular = [
            a for a in aggregated
            if (a.season_tag or "regular").lower() == "regular"
        ]

        if not in_season or not regular:
            return None

        drift: Dict[str, Any] = {
            "current_season": season_tag,
            "sample_in_season": len(in_season),
            "sample_regular": len(regular),
        }

        season_roas = [a.roas for a in in_season if a.roas is not None]
        regular_roas = [a.roas for a in regular if a.roas is not None]
        if season_roas and regular_roas:
            drift["season_vs_regular_roas"] = round(
                _mean(season_roas) - _mean(regular_roas), 3
            )

        season_cvr = [a.cvr for a in in_season if a.cvr is not None]
        regular_cvr = [a.cvr for a in regular if a.cvr is not None]
        if season_cvr and regular_cvr:
            drift["season_vs_regular_cvr"] = round(
                _mean(season_cvr) - _mean(regular_cvr), 4
            )

        return drift

    @staticmethod
    def _apply_discount(stats: BaselineStats, discount: float) -> BaselineStats:
        """对统计指标应用折扣系数（用于跨品类迁移）。"""
        if stats.roas_mean is not None:
            stats.roas_mean = round(stats.roas_mean * discount, 3)
        if stats.cvr_mean is not None:
            stats.cvr_mean = round(stats.cvr_mean * discount, 4)
        if stats.purchase_rate is not None:
            stats.purchase_rate = round(stats.purchase_rate * discount, 4)
        if stats.revenue_mean is not None:
            stats.revenue_mean = round(stats.revenue_mean * discount, 2)
        if stats.ctr_mean is not None:
            stats.ctr_mean = round(stats.ctr_mean * discount, 4)
        # CPA 反向：打折后 CPA 应该更高（更保守）
        if stats.cpa is not None:
            stats.cpa = round(stats.cpa / discount, 2)
        return stats

    @staticmethod
    def _compute_drift(
        aggregated: List[_AggregatedOutcome],
        days: int,
    ) -> Optional[Dict[str, float]]:
        """对比最近 N 天 vs 全量，看关键指标漂移。"""
        from datetime import datetime, timedelta

        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        recent = [
            a for a in aggregated
            if (a.latest_outcome_date or a.date_start or "") >= cutoff
        ]

        if len(recent) < 1 or len(aggregated) < 2:
            return None

        drift = {}

        all_roas = [a.roas for a in aggregated if a.roas is not None]
        rec_roas = [a.roas for a in recent if a.roas is not None]
        if all_roas and rec_roas:
            drift["roas"] = round(_mean(rec_roas) - _mean(all_roas), 3)

        all_sess = sum(a.sessions or 0 for a in aggregated)
        all_purch = sum(a.purchases or 0 for a in aggregated)
        rec_sess = sum(a.sessions or 0 for a in recent)
        rec_purch = sum(a.purchases or 0 for a in recent)
        if all_sess > 0 and rec_sess > 0 and all_purch > 0:
            drift["purchase_rate"] = round(
                (rec_purch / rec_sess) - (all_purch / all_sess), 4
            )

        return drift if drift else None

    @staticmethod
    def _score(stats: BaselineStats, sort_by: str) -> float:
        """从 stats 中提取排序分数。"""
        val = getattr(stats, sort_by, None)
        if val is None:
            return -999.0
        return float(val)

    @staticmethod
    def _generate_recommendation(entries: List[Dict], sort_by: str) -> str:
        """基于排名结果生成推荐文本。"""
        valid = [e for e in entries if e["data_sufficient"]]
        if not valid:
            # 检查是否有冷启动提示
            cold = [e for e in entries if e["observed_baseline"].get("cold_start_hint")]
            if cold:
                hint = cold[0]["observed_baseline"]["cold_start_hint"]
                hint_type = hint.get("type", "")
                if hint_type == "cross_category":
                    return (
                        "同品类历史数据不足，已使用跨品类迁移数据（打折后）作为参考。"
                        "建议先小规模测试验证。"
                    )
                elif hint_type == "distribution_estimate":
                    return (
                        "无历史相似案例，仅提供全量数据的分位数范围估计。"
                        "建议以小预算测试后再做决策。"
                    )
            return "历史数据不足，无法给出基线排序。建议先积累更多 campaign 数据。"

        best = valid[0]
        plan = best["plan"]
        baseline = best["observed_baseline"]
        name = plan.get("name", plan.get("theme", "未命名"))

        parts = [f"历史基线排序推荐「{name}」"]
        sample = baseline.get("sample_size", 0)
        parts.append(f"基于 {sample} 条历史相似案例")

        if "roas_mean" in baseline and baseline["roas_mean"] is not None:
            parts.append(f"历史 ROAS 均值 {baseline['roas_mean']:.2f}")
        if "purchase_rate" in baseline and baseline["purchase_rate"] is not None:
            parts.append(f"购买转化率 {baseline['purchase_rate']:.2%}")

        quality = baseline.get("match_quality", "unknown")
        if quality == "partial":
            parts.append("（部分维度匹配，置信度有限）")
        elif quality == "fallback":
            parts.append("（粗粒度匹配，仅供参考）")
        elif quality == "cross_category":
            parts.append("（跨品类迁移数据，已打折扣，仅供参考）")

        # 季节提示
        seasonal = baseline.get("seasonal_drift")
        if seasonal and seasonal.get("season_vs_regular_roas") is not None:
            roas_diff = seasonal["season_vs_regular_roas"]
            season_name = seasonal.get("current_season", "")
            if roas_diff > 0:
                parts.append(f"{season_name} 期间历史 ROAS 比日常高 {roas_diff:.2f}")
            elif roas_diff < 0:
                parts.append(f"{season_name} 期间历史 ROAS 比日常低 {abs(roas_diff):.2f}")

        return "。".join(parts) + "。"


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _fields_match(
    plan: Dict[str, Any],
    iv: HistoricalIntervention,
    dims: Tuple[str, ...],
) -> bool:
    """检查 plan 和 intervention 在指定维度上是否匹配。"""
    for dim in dims:
        plan_val = (plan.get(dim) or "").lower().strip()
        if not plan_val:
            continue
        iv_val = (getattr(iv, dim, None) or "").lower().strip()
        if not iv_val:
            return False
        if plan_val != iv_val:
            return False
    return True


def _mean(vals: list) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _weighted_mean(pairs: List[Tuple[float, float]]) -> float:
    """加权平均。pairs = [(value, weight), ...]"""
    total_weight = sum(w for _, w in pairs)
    if total_weight == 0:
        return 0.0
    return sum(v * w for v, w in pairs) / total_weight


def _std(vals: list) -> float:
    if len(vals) < 2:
        return 0.0
    m = _mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))


def _sum_non_none(vals: list) -> Optional[int]:
    """Sum non-None values; return None if all are None."""
    valid = [v for v in vals if v is not None]
    return sum(valid) if valid else None


def _latest_non_none(vals: list):
    """Return the last non-None value (assumes sorted by date)."""
    for v in reversed(vals):
        if v is not None:
            return v
    return None
