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
from ..models.campaign import Campaign, ProductLine
from ..models.evaluation import PanelScore

logger = get_logger('ranker.audience_panel')

# Moody Lenses 定制 persona
PERSONAS: List[Dict[str, Any]] = [
    {
        "id": "daily_wearer",
        "name": "日抛隐形眼镜老用户",
        "description": (
            "28岁女性，每天佩戴隐形眼镜5年以上。"
            "关注舒适度、含水量、透氧性。对品牌有一定忠诚度，"
            "但愿意尝试更舒适的新产品。对健康声称敏感，讨厌夸张宣传。"
            "主要在小红书和朋友推荐中了解新品。"
        ),
        "evaluation_focus": "产品舒适度声称是否可信、是否解决实际佩戴痛点",
    },
    {
        "id": "acuvue_switcher",
        "name": "Acuvue Define 现有用户",
        "description": (
            "25岁女性，使用 Acuvue Define 2年。喜欢自然放大效果，"
            "但觉得 Acuvue 选择少、价格高。关注眼健康，"
            "但也想要更多花色选择。会比较透氧率等参数。"
            "是 moodyPlus 的核心目标用户。"
        ),
        "evaluation_focus": "能否说服她从 Acuvue 转换、功能性证据是否充分",
    },
    {
        "id": "beauty_first",
        "name": "美瞳新用户（颜值驱动）",
        "description": (
            "22岁女大学生，第一次考虑戴美瞳。被社交媒体上的妆容效果吸引，"
            "最关心颜色好不好看、直径是否够大、能否出片。"
            "对隐形眼镜技术参数不敏感，但怕不舒服。"
            "主要在抖音和小红书种草。"
        ),
        "evaluation_focus": "视觉吸引力、种草力、是否降低尝试门槛",
    },
    {
        "id": "price_conscious",
        "name": "价格敏感用户",
        "description": (
            "24岁职场新人，月消耗1-2盒日抛。会比价，"
            "关注性价比但不追求最低价。对促销机制敏感（满减、囤货优惠）。"
            "品牌忠诚度低，哪家划算买哪家。"
        ),
        "evaluation_focus": "价格信号是否合理、促销机制吸引力、复购动力",
    },
    {
        "id": "eye_health",
        "name": "眼健康关注者",
        "description": (
            "30岁女性，有过角膜炎经历，现在非常注重眼健康。"
            "选镜片首先看材质（硅水凝胶优先）、透氧率、含水量。"
            "对'美'的需求排第二。信任专业渠道推荐（眼科医生、专业测评），"
            "反感纯颜值营销。是 moodyPlus 硅水凝胶系列的高价值用户。"
        ),
        "evaluation_focus": "健康声称是否有临床依据、材质信息是否透明",
    },
]

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

请用 JSON 格式输出：
{{
  "score": <1-10 的整数，10=非常想买/参与，1=完全无感>,
  "strengths": ["方案的优点，从你的视角"],
  "objections": ["你的疑虑和反对意见"],
  "reasoning": "你的整体判断，2-3句话"
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

    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or LLMClient()
        self.personas = PERSONAS

    def evaluate_campaign(self, campaign: Campaign, persona: Dict[str, Any]) -> PanelScore:
        """单个 persona 评审单个 campaign"""
        system_msg = SYSTEM_PROMPT.format(
            persona_description=persona["description"],
            evaluation_focus=persona["evaluation_focus"],
        )
        user_msg = USER_PROMPT.format(
            name=campaign.name,
            product_line=_product_line_label(campaign.product_line),
            target_audience=campaign.target_audience,
            core_message=campaign.core_message,
            channels=", ".join(campaign.channels),
            creative_direction=campaign.creative_direction,
            optional_fields=_format_optional_fields(campaign),
        )

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

        result = self.llm.chat_json(
            messages=messages,
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
