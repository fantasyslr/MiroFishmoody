"""
MockLLMClient — 确定性 LLM mock，用于 benchmark 回归测试

Duck-type 兼容 LLMClient，不依赖网络或 API key。
根据 messages 内容的关键词判断调用类型，返回预设响应。
"""

import re
from typing import List, Dict, Any


class MockLLMClient:
    """确定性 LLM mock，实现与 LLMClient 相同的 chat_json 接口。

    调用类型判断逻辑（按优先级）:
    1. 包含 pairwise 相关词 → PairwiseJudge 响应 (winner=A)
    2. 包含 summary 相关词 → SummaryGenerator 响应
    3. 包含 dimension_scores / objections / score → AudiencePanel 响应
    4. 其他 → fallback（返回通用 dict）
    """

    def __init__(self, api_key=None, base_url=None, model=None):
        # 不使用任何参数，不读取 Config 或环境变量
        pass

    def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Dict = None,
    ) -> str:
        """不被 runner 直接调用，返回空字符串。"""
        return ""

    def chat_json(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """根据消息内容返回确定性 JSON 响应。"""
        return self._dispatch(messages)

    def chat_multimodal(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: dict = None,
    ) -> str:
        """多模态版 chat，返回空字符串（runner 不会直接调用）。"""
        return ""

    def chat_multimodal_json(
        self,
        messages: list,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """多模态版 chat_json — 转发给 _dispatch，行为与 chat_json 相同。"""
        return self._dispatch(messages)

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _get_last_text(self, messages: List[Dict[str, Any]]) -> str:
        """从 messages 末尾提取纯文本内容（兼容 str 和 list content）。"""
        for msg in reversed(messages):
            content = msg.get("content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                # OpenAI Vision 格式：content 是 [{"type": "text", "text": "..."}, ...]
                texts = [
                    part.get("text", "")
                    for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                ]
                if texts:
                    return " ".join(texts)
        return ""

    def _dispatch(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """根据消息内容决定返回哪种 mock 响应。

        优先级（从高到低）:
        1. SummaryGenerator — prompt 包含 "confidence_notes" 字段定义（最特异）
        2. AudiencePanel — prompt 包含 "dimension_scores" 字段定义
        3. PairwiseJudge — prompt 包含 "reach_potential" 等维度名
        4. Fallback
        """
        text = self._get_last_text(messages).lower()

        # SummaryGenerator：prompt 要求输出 confidence_notes 字段（最特异）
        # 注意：SummaryGenerator prompt 也会包含 pairwise 词汇，所以必须先判断
        is_summary = "confidence_notes" in text or (
            "assumptions" in text and ("评审总结" in text or "总结报告" in text or
                                       "营销策略顾问" in text)
        )

        # AudiencePanel：prompt 要求输出 dimension_scores / objections
        is_panel = any(kw in text for kw in [
            "dimension_scores", "thumb_stop", "claim_risk", "conversion_readiness",
        ])

        # PairwiseJudge：prompt 包含 pairwise 评审维度名称
        is_pairwise = any(kw in text for kw in [
            "reach_potential", "conversion_potential", "brand_alignment",
            "risk_level", "feasibility", "哪个更优", "方案 a", "方案 b",
        ])

        if is_summary:
            return self._summary_response()
        if is_panel:
            return self._panel_response()
        if is_pairwise:
            return self._pairwise_response()
        return self._fallback_response()

    # ------------------------------------------------------------------ #
    #  Response templates
    # ------------------------------------------------------------------ #

    def _panel_response(self) -> Dict[str, Any]:
        """AudiencePanel 期望的格式：score + dimension_scores + objections + strengths + reasoning。"""
        return {
            "score": 6.5,
            "strengths": ["信息清晰", "视觉吸引力强"],
            "objections": ["缺乏差异化"],
            "reasoning": "方案整体质量良好，具有一定的市场潜力。",
            "dimension_scores": {
                "thumb_stop": 6.5,
                "clarity": 7.0,
                "trust": 6.0,
                "conversion_readiness": 6.5,
                "claim_risk": 5.5,
            },
        }

    def _pairwise_response(self) -> Dict[str, Any]:
        """PairwiseJudge 期望的格式：winner(A/B/tie) + dimensions + reasoning。

        始终返回 winner="A"（确定性规则）——因为 PairwiseJudge 会把 A/B
        映射为 campaign_a_id / campaign_b_id，所以 mock 必须固定选 A 或 B。
        选 A 意味着「传入 evaluate_pair(a, b) 时 a 总是胜出」。
        """
        return {
            "winner": "A",
            "dimensions": {
                "reach_potential": "A",
                "conversion_potential": "A",
                "brand_alignment": "A",
                "risk_level": "A",
                "feasibility": "A",
            },
            "reasoning": "方案A在关键维度上表现更优。",
        }

    def _summary_response(self) -> Dict[str, Any]:
        """SummaryGenerator 期望的格式：summary + assumptions + confidence_notes。
        summary 必须 >=20 字，否则 SummaryGenerator 会触发质量警告并重试。
        """
        return {
            "summary": "本次评审已完成，各方案已按综合得分完成排名，建议参考排名第一的方案进行后续投放决策。",
            "assumptions": ["评审基于提供的文案和方向描述", "mock环境确定性响应，不代表真实用户偏好"],
            "confidence_notes": ["mock环境，仅用于回归测试，实际效果需A/B测试验证"],
        }

    def _fallback_response(self) -> Dict[str, Any]:
        """通用 fallback，返回包含基础字段的 dict。"""
        return {
            "result": "ok",
            "reasoning": "mock fallback response",
        }
