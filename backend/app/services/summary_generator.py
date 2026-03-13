"""
Summary Generator — 生成评审总结报告

基于 panel scores、pairwise results、rankings 生成结构化总结。
"""

from typing import List, Dict, Any

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.retry import retry_with_backoff
from ..utils.logger import get_logger
from ..models.campaign import Campaign
from ..models.evaluation import CampaignRanking, PanelScore, PairwiseResult

logger = get_logger('ranker.summary')

SUMMARY_PROMPT = """你是 Moody Lenses 的营销策略顾问。请根据以下评审数据，生成一份简洁的 campaign 方案评审总结。

## 方案排名

{rankings_text}

## 分人群评分详情

{panel_text}

## Pairwise 对决结果

{pairwise_text}

请用 JSON 格式输出：
{{
  "summary": "3-5 句话的整体评审结论，包含推荐行动",
  "assumptions": ["本次评审的关键假设，例如目标人群的代表性、市场环境等"],
  "confidence_notes": ["置信度说明，例如哪些结论把握较大、哪些需要实际数据验证"]
}}

注意：
- 不要预测具体 ROAS / GMV 数字
- 聚焦方案之间的相对优劣
- 标出最值得关注的风险点"""


def _format_rankings(rankings: List[CampaignRanking]) -> str:
    lines = []
    for r in rankings:
        lines.append(
            f"#{r.rank} {r.campaign_name} — "
            f"综合分 {r.composite_score:.1f}, "
            f"panel均分 {r.panel_avg:.1f}, "
            f"对决 {r.pairwise_wins}胜{r.pairwise_losses}负, "
            f"判定: {r.verdict.value.upper()}"
        )
        if r.top_objections:
            lines.append(f"  主要反对: {'; '.join(r.top_objections)}")
        if r.top_strengths:
            lines.append(f"  主要优势: {'; '.join(r.top_strengths)}")
    return "\n".join(lines)


def _format_panel(panel_scores: List[PanelScore], campaigns: List[Campaign]) -> str:
    cmap = {c.id: c.name for c in campaigns}
    lines = []
    # 按 campaign 分组
    by_campaign: Dict[str, List[PanelScore]] = {}
    for ps in panel_scores:
        by_campaign.setdefault(ps.campaign_id, []).append(ps)

    for cid, scores in by_campaign.items():
        lines.append(f"\n### {cmap.get(cid, cid)}")
        for s in scores:
            lines.append(f"  {s.persona_name}: {s.score}/10 — {s.reasoning}")
    return "\n".join(lines)


def _format_pairwise(results: List[PairwiseResult], campaigns: List[Campaign]) -> str:
    cmap = {c.id: c.name for c in campaigns}
    lines = []
    for r in results:
        a_name = cmap.get(r.campaign_a_id, r.campaign_a_id)
        b_name = cmap.get(r.campaign_b_id, r.campaign_b_id)
        winner_name = cmap.get(r.winner_id, "平局") if r.winner_id else "平局"
        lines.append(f"{a_name} vs {b_name} → 胜者: {winner_name}")
    return "\n".join(lines)


class SummaryGenerator:
    """评审总结生成器"""

    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or LLMClient()

    def generate(
        self,
        campaigns: List[Campaign],
        rankings: List[CampaignRanking],
        panel_scores: List[PanelScore],
        pairwise_results: List[PairwiseResult],
    ) -> Dict[str, Any]:
        """生成总结，返回 {summary, assumptions, confidence_notes}。
        如果 LLM 返回不完整，自动重试一次。"""
        prompt = SUMMARY_PROMPT.format(
            rankings_text=_format_rankings(rankings),
            panel_text=_format_panel(panel_scores, campaigns),
            pairwise_text=_format_pairwise(pairwise_results, campaigns),
        )

        messages = [
            {"role": "user", "content": prompt},
        ]

        for attempt in range(2):
            try:
                result = self.llm.chat_json(
                    messages=messages,
                    temperature=0.4,
                    max_tokens=2048,
                )
            except Exception as e:
                logger.warning(f"Summary LLM call failed (attempt {attempt+1}): {e}")
                result = {}

            summary = result.get("summary", "")
            assumptions = result.get("assumptions", [])
            confidence = result.get("confidence_notes", [])

            # 质量检查：summary 至少 20 字且 assumptions 非空
            if len(summary) >= 20 and assumptions:
                break
            logger.warning(
                f"Summary 质量不足 (attempt {attempt+1}): "
                f"summary={len(summary)} chars, assumptions={len(assumptions)} items. "
                f"Retrying..."
            )

        # 如果两次都不够好，补一个 fallback
        if len(summary) < 20:
            top = rankings[0] if rankings else None
            summary = (
                f"评审完成。排名第一的方案为「{top.campaign_name}」"
                f"（综合分 {top.composite_score:.1f}，verdict: {top.verdict.value}）。"
                f"建议结合 objection 列表做进一步优化后再投放。"
            ) if top else "评审完成，请查看详细排名。"
        if not assumptions:
            assumptions = ["虚拟 persona 评审结果仅供参考，不代表真实用户反馈"]
        if not confidence:
            confidence = ["排名基于 LLM 多视角评审，实际效果需 A/B 测试验证"]

        return {
            "summary": summary,
            "assumptions": assumptions,
            "confidence_notes": confidence,
        }
