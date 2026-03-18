"""
BacktestEngine — 从 BrandStateEngine 提取的回测模块（TD-02 strangler fig）

留一法回测逻辑独立为此类，BrandStateEngine.backtest() 委托调用。
"""

from typing import Any, Dict, List

from ..models.brand_state import PERCEPTION_DIMENSIONS
from ..models.brandiction import HistoricalIntervention
from .brandiction_store import BrandictionStore


def _themes_match(query: str, candidate: str) -> bool:
    """
    判断两个 theme 是否匹配（从 brand_state_engine 复制，不依赖外部导入）。
    精确匹配或 token 级包含（用 _ 分词），不做单字符子串匹配。
    """
    if query == candidate:
        return True
    q_tokens = set(query.split("_"))
    c_tokens = set(candidate.split("_"))
    if len(q_tokens) == 1 and len(q_tokens & c_tokens) > 0:
        return True
    if len(c_tokens) == 1 and len(q_tokens & c_tokens) > 0:
        return True
    return False


class BacktestEngine:
    """
    留一法回测引擎。

    依赖 BrandictionStore 读数据，依赖外部 engine 提供
    compute_intervention_impact 和 _inject_competitor_delta。
    """

    def __init__(self, store: BrandictionStore, engine: Any):
        self.store = store
        self._engine = engine  # BrandStateEngine instance for helper methods

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
            raw_actual = self._engine.compute_intervention_impact(holdout, outcomes, market=market)
            actual_delta = self._engine._inject_competitor_delta(
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
                    d = self._engine.compute_intervention_impact(iv, oc, market=market)
                    d = self._engine._inject_competitor_delta(
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
                predicted = self._engine.compute_intervention_impact(dummy, [], market=market)
                predicted = self._engine._inject_competitor_delta(
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
