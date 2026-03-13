"""
Brief Parser — 将自然语言方案描述解析为结构化 Campaign 字段
"""

import json
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger

logger = get_logger('ranker.services.brief_parser')

PARSE_SYSTEM_PROMPT = """你是 Moody Lenses 的营销方案解析助手。
用户会用自然语言描述一个营销方案，你需要从中提取结构化信息。

Moody Lenses 背景：
- 独立美妆隐形眼镜品牌
- 两条产品线：colored_lenses（彩色美瞳）、moodyplus（透明硅水凝胶功能镜片）

请从用户描述中提取以下字段，如果某个字段用户没提到，留空字符串：
- name: 方案名称（简短概括，不超过 10 个字）
- target_audience: 目标受众
- core_message: 核心信息/卖点
- channels: 投放渠道（数组格式）
- creative_direction: 创意方向
- budget_range: 预算范围
- promo_mechanic: 促销机制
- kv_description: 主视觉描述

用 JSON 格式输出，不要添加任何解释。"""


class BriefParser:
    """将用户自由文本解析为结构化 Campaign 字段"""

    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or LLMClient()

    def parse(self, brief_text: str, product_line: str = "colored_lenses") -> dict:
        """
        解析自然语言 brief 文本为结构化字段。

        Returns:
            {"parsed": {...}, "confidence": "high"|"medium"|"low"}
        """
        if not brief_text or not brief_text.strip():
            raise ValueError("brief_text 不能为空")

        user_prompt = f"产品线：{product_line}\n\n用户描述：\n{brief_text.strip()}"

        try:
            result = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": PARSE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )

            # Normalize fields
            parsed = {
                "name": str(result.get("name", "")).strip(),
                "product_line": product_line,
                "target_audience": str(result.get("target_audience", "")).strip(),
                "core_message": str(result.get("core_message", "")).strip(),
                "channels": result.get("channels", []),
                "creative_direction": str(result.get("creative_direction", "")).strip(),
                "budget_range": str(result.get("budget_range", "")).strip(),
                "promo_mechanic": str(result.get("promo_mechanic", "")).strip(),
                "kv_description": str(result.get("kv_description", "")).strip(),
            }

            # Ensure channels is a list
            if isinstance(parsed["channels"], str):
                parsed["channels"] = [c.strip() for c in parsed["channels"].split(",") if c.strip()]

            # Confidence heuristic
            filled = sum(1 for k in ["name", "target_audience", "core_message", "creative_direction"]
                         if parsed[k])
            confidence = "high" if filled >= 3 else ("medium" if filled >= 2 else "low")

            return {"parsed": parsed, "confidence": confidence}

        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"Brief 解析失败: {e}")
            raise ValueError(f"Brief 解析失败，请切换到高级模式手动填写: {e}")
        except Exception as e:
            logger.error(f"Brief 解析异常: {e}", exc_info=True)
            raise ValueError(f"Brief 解析服务异常: {e}")
