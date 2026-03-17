"""
Audience Panel — 虚拟消费者视角评审

5 个固定 persona 对每个 campaign 打分 + 写 objection。
persona 基于 Moody Lenses 用户画像定制。
"""

import json
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.retry import retry_with_backoff
from ..utils.logger import get_logger
from ..utils.image_helpers import resolve_image_path, image_to_base64_part
from ..models.campaign import Campaign, ProductLine
from ..models.evaluation import PanelScore
from .persona_registry import PersonaRegistry

logger = get_logger('ranker.audience_panel')

SYSTEM_PROMPT = """你是一个消费者调研模拟器。你需要完全进入以下角色，从该消费者的真实视角评审一个美瞳/隐形眼镜品牌的营销方案。

你的角色：
{persona_description}

你的评审重点：
{evaluation_focus}

品牌背景：
- Moody Lenses 是独立美妆隐形眼镜品牌
- 两条产品线：colored lenses（彩色美瞳）和 moodyPlus（透明硅水凝胶功能镜片）
- 竞争定位：功能 + 美学，不打价格战
- moodyPlus 卖点：临床级透氧率，对标 Acuvue Define 用户

评审要求：
1. 从你这个角色的真实视角出发
2. 不要假装客气 — 如果方案对你没吸引力，直接说
3. 关注方案是否真正解决你的需求
4. 指出你会产生的具体疑虑和反对意见

同时请对以下 5 个维度打分（1-10）：
- thumb_stop: 停留吸引力（看到这个内容你会不会停下来看）
- clarity: 信息清晰度（核心卖点是否一看就懂）
- trust: 信任感（你会不会相信它说的）
- conversion_readiness: 转化就绪度（看完会不会想买）
- claim_risk: 声称可信度（10=完全可信，1=明显夸张）

请用 JSON 格式输出：
{{
  "score": <1-10 的整数，10=非常想买/参与，1=完全无感>,
  "strengths": ["方案的优点，从你的视角"],
  "objections": ["你的疑虑和反对意见"],
  "reasoning": "你的整体判断，2-3句话",
  "dimension_scores": {{
    "thumb_stop": <1-10>,
    "clarity": <1-10>,
    "trust": <1-10>,
    "conversion_readiness": <1-10>,
    "claim_risk": <1-10>
  }}
}}"""

USER_PROMPT = """请评审以下营销方案：

方案名称：{name}
产品线：{product_line}
目标受众：{target_audience}
核心信息：{core_message}
投放渠道：{channels}
创意方向：{creative_direction}
{optional_fields}"""


def _format_optional_fields(campaign: Campaign) -> str:
    parts = []
    if campaign.budget_range:
        parts.append(f"预算范围：{campaign.budget_range}")
    if campaign.kv_description:
        parts.append(f"主视觉描述：{campaign.kv_description}")
    if campaign.promo_mechanic:
        parts.append(f"促销机制：{campaign.promo_mechanic}")
    if campaign.extra:
        for k, v in campaign.extra.items():
            parts.append(f"{k}：{v}")
    return "\n".join(parts)


def _product_line_label(pl: ProductLine) -> str:
    return "彩色美瞳 (colored lenses)" if pl == ProductLine.COLORED else "moodyPlus 透明硅水凝胶镜片"


class AudiencePanel:
    """虚拟消费者评审面板"""

    def __init__(self, llm_client: LLMClient = None, persona_registry: PersonaRegistry = None, category: str = None):
        self.llm = llm_client or LLMClient()
        self._registry = persona_registry or PersonaRegistry()
        self.personas = self._registry.get_personas(category=category)

    def evaluate_campaign(self, campaign: Campaign, persona: Dict[str, Any]) -> PanelScore:
        """单个 persona 评审单个 campaign"""
        system_msg = SYSTEM_PROMPT.format(
            persona_description=persona["description"],
            evaluation_focus=persona["evaluation_focus"],
        )
        user_text = USER_PROMPT.format(
            name=campaign.name,
            product_line=_product_line_label(campaign.product_line),
            target_audience=campaign.target_audience,
            core_message=campaign.core_message,
            channels=", ".join(campaign.channels),
            creative_direction=campaign.creative_direction,
            optional_fields=_format_optional_fields(campaign),
        )

        system_message = {"role": "system", "content": system_msg}

        # Build message with optional images
        if hasattr(campaign, 'image_paths') and campaign.image_paths:
            content_parts = [{"type": "text", "text": user_text + "\n\n请同时参考提供的素材图片进行评审。如果有图片，请基于你看到的视觉效果评判视觉吸引力、信息传达、品牌调性等维度。"}]
            for img_url in campaign.image_paths[:5]:  # Max 5 images
                resolved = resolve_image_path(img_url)
                if resolved:
                    img_part = image_to_base64_part(resolved)
                    if img_part:
                        content_parts.append(img_part)
            user_message = {"role": "user", "content": content_parts}
            result = self.llm.chat_multimodal_json(
                messages=[system_message, user_message],
                temperature=Config.PANEL_TEMPERATURE,
            )
        else:
            user_message = {"role": "user", "content": user_text}
            result = self.llm.chat_json(
                messages=[system_message, user_message],
                temperature=Config.PANEL_TEMPERATURE,
                max_tokens=1024,
            )

        return PanelScore(
            persona_id=persona["id"],
            persona_name=persona["name"],
            campaign_id=campaign.id,
            score=float(result.get("score", 5)),
            objections=result.get("objections", []),
            strengths=result.get("strengths", []),
            reasoning=result.get("reasoning", ""),
            dimension_scores=result.get("dimension_scores", {}),
        )

    def evaluate_all(self, campaigns: List[Campaign], max_workers: int = 4) -> List[PanelScore]:
        """
        所有 persona 评审所有 campaign。
        并行执行，每个 (persona, campaign) 组合一次 LLM 调用。
        """
        scores: List[PanelScore] = []
        tasks = [
            (campaign, persona)
            for campaign in campaigns
            for persona in self.personas
        ]

        logger.info(f"开始 Audience Panel 评审: {len(campaigns)} 个方案 × {len(self.personas)} 个 persona = {len(tasks)} 次评审")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(self._safe_evaluate, campaign, persona): (campaign.id, persona["id"])
                for campaign, persona in tasks
            }
            for future in as_completed(future_map):
                campaign_id, persona_id = future_map[future]
                try:
                    score = future.result()
                    scores.append(score)
                    logger.info(f"  {persona_id} → {campaign_id}: {score.score}/10")
                except Exception as e:
                    logger.error(f"  {persona_id} → {campaign_id} 评审失败: {e}")

        return scores

    @retry_with_backoff(max_retries=2, initial_delay=1.0)
    def _safe_evaluate(self, campaign: Campaign, persona: Dict[str, Any]) -> PanelScore:
        return self.evaluate_campaign(campaign, persona)
