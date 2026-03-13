"""
Dimension Evaluator — 从 panel scores 提取 5 个维度得分

每个维度映射到特定 persona 评分信号：
- thumb_stop: beauty_first 的 score 权重最大
- clarity: 全部 persona 的 objections 中"不清楚/混乱/不懂"类
- trust: eye_health + acuvue_switcher 的 score
- conversion_readiness: price_conscious 的 score + promo 相关信号
- claim_risk: objections 中"夸张/虚假/不可信"类密度（高=差）
"""

import math
from typing import List, Dict
from collections import defaultdict

from ..utils.logger import get_logger
from ..models.campaign import Campaign
from ..models.evaluation import PanelScore
from ..models.scoreboard import DimensionScore, DIMENSION_KEYS, DIMENSION_LABELS

logger = get_logger('ranker.dimension')

# 信任相关关键词（中文）
CLARITY_NEGATIVE_KEYWORDS = [
    "不清楚", "不明确", "困惑", "混乱", "不懂", "定位不清",
    "矛盾", "逻辑", "模糊", "不确定",
]

CLAIM_RISK_KEYWORDS = [
    "夸张", "虚假", "不可信", "没有依据", "缺乏", "数据",
    "临床", "背书", "不信任", "安全", "风险", "过度",
]


def _keyword_density(texts: List[str], keywords: List[str]) -> float:
    """计算关键词出现密度 (0-1)"""
    if not texts:
        return 0.0
    total_hits = 0
    for text in texts:
        for kw in keywords:
            if kw in text:
                total_hits += 1
    # 归一化：每条 text 平均命中 keyword 数 / keyword 总数
    return min(1.0, total_hits / (len(texts) * max(len(keywords), 1)) * 5)


def _softmax_probs(scores: Dict[str, float], temperature: float = 1.5) -> Dict[str, float]:
    """scores → 归一化概率"""
    if not scores:
        return {}
    max_v = max(scores.values())
    exp_vals = {k: math.exp((v - max_v) / temperature) for k, v in scores.items()}
    total = sum(exp_vals.values())
    if total == 0:
        n = len(scores)
        return {k: 1.0 / n for k in scores}
    return {k: v / total for k, v in exp_vals.items()}


class DimensionEvaluator:
    """维度评估器"""

    def evaluate(
        self,
        campaigns: List[Campaign],
        panel_scores: List[PanelScore],
    ) -> List[DimensionScore]:
        """
        计算每个维度中每个 campaign 的得分。
        返回 flat list of DimensionScore。
        """
        all_ids = [c.id for c in campaigns]

        # 按 campaign 分组
        by_campaign: Dict[str, List[PanelScore]] = defaultdict(list)
        for ps in panel_scores:
            by_campaign[ps.campaign_id].append(ps)

        # 按 persona 分组
        by_persona: Dict[str, Dict[str, List[PanelScore]]] = defaultdict(lambda: defaultdict(list))
        for ps in panel_scores:
            by_persona[ps.persona_id][ps.campaign_id].append(ps)

        results = []

        for dimension_key in DIMENSION_KEYS:
            raw_scores = {}
            for cid in all_ids:
                raw_scores[cid] = self._compute_raw(
                    dimension_key, cid, by_campaign.get(cid, []), by_persona,
                )

            probs = _softmax_probs(raw_scores, temperature=1.5)

            for cid in all_ids:
                results.append(DimensionScore(
                    dimension_key=dimension_key,
                    dimension_label=DIMENSION_LABELS[dimension_key],
                    campaign_id=cid,
                    score=probs.get(cid, 0),
                    raw_score=raw_scores.get(cid, 0),
                ))

        return results

    def _compute_raw(
        self,
        dimension_key: str,
        campaign_id: str,
        scores: List[PanelScore],
        by_persona: Dict[str, Dict[str, List[PanelScore]]],
    ) -> float:
        """计算某个维度某个 campaign 的原始分 (0-10)"""

        if dimension_key == "thumb_stop":
            # beauty_first persona 的 score 权重最大
            bf_scores = by_persona.get("beauty_first", {}).get(campaign_id, [])
            if bf_scores:
                return sum(s.score for s in bf_scores) / len(bf_scores)
            # fallback: 全体均分
            return sum(s.score for s in scores) / len(scores) if scores else 5.0

        elif dimension_key == "clarity":
            # 反向：objection 中"不清楚"类关键词越少越好
            all_obj = [o for s in scores for o in s.objections]
            density = _keyword_density(all_obj, CLARITY_NEGATIVE_KEYWORDS)
            return 10.0 * (1.0 - density)

        elif dimension_key == "trust":
            # eye_health + acuvue_switcher 的 score
            trust_personas = ["eye_health", "acuvue_switcher"]
            trust_scores = []
            for pid in trust_personas:
                ps_list = by_persona.get(pid, {}).get(campaign_id, [])
                trust_scores.extend(s.score for s in ps_list)
            if trust_scores:
                return sum(trust_scores) / len(trust_scores)
            return sum(s.score for s in scores) / len(scores) if scores else 5.0

        elif dimension_key == "conversion_readiness":
            # price_conscious + daily_wearer 的 score
            conv_personas = ["price_conscious", "daily_wearer"]
            conv_scores = []
            for pid in conv_personas:
                ps_list = by_persona.get(pid, {}).get(campaign_id, [])
                conv_scores.extend(s.score for s in ps_list)
            if conv_scores:
                return sum(conv_scores) / len(conv_scores)
            return sum(s.score for s in scores) / len(scores) if scores else 5.0

        elif dimension_key == "claim_risk":
            # 反向：risk 关键词越多越差
            all_obj = [o for s in scores for o in s.objections]
            density = _keyword_density(all_obj, CLAIM_RISK_KEYWORDS)
            return 10.0 * (1.0 - density)

        return 5.0
