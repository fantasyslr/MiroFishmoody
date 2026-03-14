"""
Historical Baseline Ranker — 轨道 1：基于真实历史漏斗数据的 campaign 排序

不依赖感知模型、不使用手拍系数。
排序依据 = 历史相似组的真实 outcome 指标（ROAS / CPA / CVR / sessions→purchases 等）。

统计口径：
  - 每个 intervention 的多个 outcome window 先聚合为单条记录（取最新 window 或加权合并）
  - 然后在 intervention 粒度做均值/方差/漂移

核心方法:
  - query_baseline()  → 查历史相似组，返回指标统计
  - rank_campaigns()  → 多 plan 对比排序
"""

import math
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any, Tuple

from ..models.brandiction import HistoricalIntervention, HistoricalOutcomeWindow
from .brandiction_store import BrandictionStore


# ------------------------------------------------------------------
# 合法排序字段
# ------------------------------------------------------------------

VALID_SORT_FIELDS = frozenset({
    "roas_mean", "purchase_rate", "revenue_mean", "cvr_mean",
    "ctr_mean", "aov_mean", "sessions_mean", "cpa",
})


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

    # 匹配信息
    match_dimensions: List[str] = field(default_factory=list)
    match_quality: str = "exact"  # exact | partial | fallback

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class _AggregatedOutcome:
    """单个 intervention 的聚合 outcome（多 window 合并后）"""
    intervention_id: str
    date_start: Optional[str] = None       # intervention 开始日期
    latest_outcome_date: Optional[str] = None  # 最新 outcome window 日期（用于 drift）
    spend: Optional[float] = None
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
    ) -> BaselineStats:
        """
        给定一个 campaign plan，查找历史相似组并返回 outcome 统计。

        product_line 和 audience_segment 是硬过滤条件，不参与逐步放宽。
        plan 中的 market 也是硬过滤条件。

        匹配策略（在硬过滤后逐步放宽）：
        1. platform + channel_family + theme + landing_page
        2. platform + channel_family + theme
        3. channel_family + theme
        4. platform + channel_family
        5. channel_family
        6. （仅硬过滤）
        """
        # 硬过滤：product_line + audience_segment + market
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

        # 预加载 outcomes
        all_outcomes = {}
        for iv in filtered:
            all_outcomes[iv.intervention_id] = self.store.list_outcomes(iv.intervention_id)

        # 逐步放宽的软匹配维度
        match_levels = [
            ("platform", "channel_family", "theme", "landing_page"),
            ("platform", "channel_family", "theme"),
            ("channel_family", "theme"),
            ("platform", "channel_family"),
            ("channel_family",),
            (),  # 仅硬过滤
        ]

        # 计算 plan 实际指定了哪些软匹配维度
        _SOFT_DIMS = ("platform", "channel_family", "theme", "landing_page")
        plan_specified = tuple(
            d for d in _SOFT_DIMS
            if (plan.get(d) or "").strip()
        )

        for dims in match_levels:
            matched = self._match_interventions(plan, filtered, all_outcomes, dims)
            if len(matched) >= min_samples:
                agg = [self._aggregate_outcome(iv, ocs) for iv, ocs in matched]
                stats = self._compute_stats(agg)
                # match_dimensions = 硬过滤 + 实际生效的软匹配维度
                hard_dims = ["product_line", "audience_segment"]
                if plan_market:
                    hard_dims.append("market")
                effective_soft = [d for d in dims if d in plan_specified]
                stats.match_dimensions = hard_dims + effective_soft
                # match_quality 基于 plan 指定的维度中有多少真正参与了匹配
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
                return stats

        return BaselineStats(
            sample_size=0,
            match_dimensions=[],
            match_quality="no_data",
        )

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
    ) -> _AggregatedOutcome:
        """
        将一个 intervention 的多个 outcome window 聚合为单条记录。

        策略：
        - 累加型指标（sessions, purchases, revenue）：求和
        - 比率型指标（roas, ctr, cvr, aov）：取最新 window 的值
          （如果最新无值则 fallback 到任意有值的 window）
        """
        agg = _AggregatedOutcome(
            intervention_id=iv.intervention_id,
            date_start=iv.date_start,
            spend=iv.spend,
        )
        if not outcomes:
            return agg

        # 按 date_start 排序，最新的在最后
        sorted_oc = sorted(outcomes, key=lambda o: o.date_start or "")

        # 记录最新 outcome window 的日期（用于 drift 计算）
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
    def _compute_stats(aggregated: List[_AggregatedOutcome]) -> BaselineStats:
        """从 intervention 级聚合记录计算统计值。"""
        stats = BaselineStats(sample_size=len(aggregated))

        # ROAS (intervention 级)
        roas_vals = [a.roas for a in aggregated if a.roas is not None]
        if roas_vals:
            stats.roas_mean = round(_mean(roas_vals), 3)
            stats.roas_std = round(_std(roas_vals), 3) if len(roas_vals) > 1 else 0.0

        # CTR
        ctr_vals = [a.ctr for a in aggregated if a.ctr is not None]
        if ctr_vals:
            stats.ctr_mean = round(_mean(ctr_vals), 4)

        # CVR
        cvr_vals = [a.cvr for a in aggregated if a.cvr is not None]
        if cvr_vals:
            stats.cvr_mean = round(_mean(cvr_vals), 4)

        # CPA = total spend / total purchases (intervention 级)
        total_spend = sum(a.spend for a in aggregated if a.spend)
        total_purchases = sum(a.purchases for a in aggregated if a.purchases)
        if total_spend > 0 and total_purchases > 0:
            stats.cpa = round(total_spend / total_purchases, 2)

        # Sessions (intervention 级均值)
        sess_vals = [a.sessions for a in aggregated if a.sessions is not None]
        if sess_vals:
            stats.sessions_mean = round(_mean(sess_vals), 1)

        # Purchase rate = total purchases / total sessions (intervention 级)
        total_sessions = sum(a.sessions for a in aggregated if a.sessions)
        if total_sessions > 0 and total_purchases > 0:
            stats.purchase_rate = round(total_purchases / total_sessions, 4)

        # AOV
        aov_vals = [a.aov for a in aggregated if a.aov is not None]
        if aov_vals:
            stats.aov_mean = round(_mean(aov_vals), 2)

        # Revenue (intervention 级均值)
        rev_vals = [a.revenue for a in aggregated if a.revenue is not None]
        if rev_vals:
            stats.revenue_mean = round(_mean(rev_vals), 2)

        return stats

    @staticmethod
    def _compute_drift(
        aggregated: List[_AggregatedOutcome],
        days: int,
    ) -> Optional[Dict[str, float]]:
        """对比最近 N 天 vs 全量，看关键指标漂移。"""
        from datetime import datetime, timedelta

        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        # 用最新 outcome window 日期判断"近期"，而非 intervention 开始日期
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
