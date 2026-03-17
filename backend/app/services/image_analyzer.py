"""
Image Analyzer — 图片内容分析服务

对 campaign plan 的素材图做多模态 LLM 分析，提取结构化视觉特征。
输出用于 Brandiction race 的 visual differentiation layer。

设计原则：
  - 有图片时：调用 LLM 多模态分析，返回结构化特征
  - 无图片 / 分析失败：返回 None，不影响主流程
  - 多张图片：逐张分析后聚合为 visual profile
"""

from typing import List, Dict, Any, Optional

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from ..utils.image_helpers import resolve_image_path, image_to_base64_part

logger = get_logger("ranker.image_analyzer")

ANALYSIS_SYSTEM_PROMPT = """你是一个视觉营销分析师，专门分析美妆/隐形眼镜品牌的营销素材图片。

请从以下维度分析这张素材图片，返回结构化 JSON：

1. creative_style: 素材风格，从以下选项中选一个：
   studio / ugc / editorial / product_only / lifestyle / meme / testimonial / mixed

2. product_visibility: 产品可见度，1-10（10=产品是绝对焦点）

3. human_presence: 人物出镜程度，从以下选项选：
   none / partial（局部如眼部特写）/ full_face / full_body / group

4. text_density: 文字密度，1-10（10=大面积文字覆盖）

5. visual_claim_focus: 素材主要传达的卖点方向，从以下选项选一个：
   science / comfort / aesthetic / price / social_proof / lifestyle / mixed

6. aesthetic_tone: 审美调性，从以下选项选一个：
   premium / clinical / playful / warm / edgy / minimalist / generic

7. trust_signal_strength: 信任信号强度，1-10（10=强临床/专业背书）

8. promo_intensity: 促销感强度，1-10（10=大面积价格/折扣信息）

9. premium_vs_mass: 高端感定位，从以下选项选：
   premium / mid / mass

10. visual_hooks: 视觉钩子列表，最多3个（如"眼部特写"、"对比图"、"KOL背书"等）

11. visual_risks: 视觉风险列表，最多3个（如"过度修图"、"文字过多"、"品牌调性偏移"等）

12. summary: 一段话总结这张图的营销效果（50字以内）

请以纯 JSON 格式输出，不要包含其他说明。"""


AGGREGATION_SYSTEM_PROMPT = """你是一个视觉营销分析师。以下是同一个营销方案的多张素材图分析结果。
请聚合为一个整体的 visual profile。

规则：
- creative_style: 选出现最多的，如果分散则选 mixed
- product_visibility: 取均值并四舍五入
- human_presence: 选最高出镜程度
- text_density: 取均值并四舍五入
- visual_claim_focus: 选出现最多的，分散则选 mixed
- aesthetic_tone: 选出现最多的，分散则选 mixed
- trust_signal_strength: 取均值并四舍五入
- promo_intensity: 取均值并四舍五入
- premium_vs_mass: 选出现最多的
- visual_hooks: 合并去重，最多保留5个
- visual_risks: 合并去重，最多保留5个
- summary: 写一段整体总结（80字以内）
- consistency_score: 素材之间的一致性，1-10（10=高度一致）
- dominant_creative_strategy: 一句话描述整体创意策略（20字以内）

请以纯 JSON 格式输出。"""


class ImageAnalyzer:
    """素材图片内容分析器"""

    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or LLMClient()

    def analyze_single_image(self, image_path: str) -> Optional[Dict[str, Any]]:
        """分析单张图片，返回结构化视觉特征"""
        resolved = resolve_image_path(image_path)
        if not resolved:
            logger.warning(f"图片路径无法解析: {image_path}")
            return None

        img_part = image_to_base64_part(resolved)
        if not img_part:
            return None

        try:
            result = self.llm.chat_multimodal_json(
                messages=[
                    {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "请分析这张营销素材图片。"},
                            img_part,
                        ],
                    },
                ],
                temperature=0.2,
                max_tokens=1024,
            )
            return result
        except Exception as e:
            logger.error(f"图片分析 LLM 调用失败: {e}")
            return None

    def analyze_plan_images(
        self, image_paths: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        分析一个 plan 的所有素材图片。

        - 0 张图片：返回 None
        - 1 张图片：直接返回单张分析结果
        - 多张图片：逐张分析后聚合

        返回结构化 visual profile dict，或 None。
        """
        if not image_paths:
            return None

        valid_paths = [p for p in image_paths if resolve_image_path(p)]
        if not valid_paths:
            return None

        # 最多分析 5 张
        valid_paths = valid_paths[:5]

        if len(valid_paths) == 1:
            result = self.analyze_single_image(valid_paths[0])
            if result:
                result["image_count"] = 1
                result["consistency_score"] = 10
                result.setdefault("dominant_creative_strategy", result.get("summary", ""))
            return result

        # 多张图：逐张分析
        individual_results = []
        for path in valid_paths:
            analysis = self.analyze_single_image(path)
            if analysis:
                individual_results.append(analysis)

        if not individual_results:
            return None

        if len(individual_results) == 1:
            individual_results[0]["image_count"] = 1
            individual_results[0]["consistency_score"] = 10
            return individual_results[0]

        # 聚合多张分析结果
        return self._aggregate_analyses(individual_results)

    def _aggregate_analyses(
        self, analyses: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """用 LLM 聚合多张图片分析结果"""
        import json

        analyses_text = json.dumps(analyses, ensure_ascii=False, indent=2)

        try:
            result = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": AGGREGATION_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"以下是 {len(analyses)} 张素材图的分析结果，请聚合为整体 visual profile：\n\n{analyses_text}",
                    },
                ],
                temperature=0.2,
                max_tokens=1024,
            )
            result["image_count"] = len(analyses)
            return result
        except Exception as e:
            logger.error(f"图片聚合分析失败: {e}")
            # Fallback: 用第一张的结果 + 手动聚合数值
            fallback = dict(analyses[0])
            fallback["image_count"] = len(analyses)
            fallback["consistency_score"] = 5
            fallback["summary"] = f"共 {len(analyses)} 张素材，聚合分析失败，使用首张结果"
            return fallback


def compute_visual_score(profile: Dict[str, Any]) -> float:
    """
    从 visual profile 计算一个 0-1 的综合视觉质量分数。

    权重分配（隐形眼镜品牌视角）：
    - trust_signal_strength: 20% — 信任是高客单价品类的关键
    - product_visibility: 15% — 产品可见度影响记忆度
    - aesthetic_tone 匹配度: 15% — premium/clinical 加分
    - promo_intensity (反向): 15% — 低促销感 = 品牌保护
    - text_density (适中最优): 10% — 3-5 最优
    - visual_hooks 数量: 10% — 有钩子 = 更好的停留
    - visual_risks 数量 (反向): 10% — 风险越少越好
    - consistency_score: 5% — 多张素材的一致性
    """
    score = 0.0

    # trust_signal_strength: 1-10 → 0-1
    trust = profile.get("trust_signal_strength", 5)
    if isinstance(trust, (int, float)):
        score += 0.20 * (trust / 10.0)

    # product_visibility: 1-10 → 0-1
    product_vis = profile.get("product_visibility", 5)
    if isinstance(product_vis, (int, float)):
        score += 0.15 * (product_vis / 10.0)

    # aesthetic_tone: premium/clinical = 1.0, minimalist = 0.8, warm = 0.7, others = 0.5
    tone_map = {
        "premium": 1.0, "clinical": 0.9, "minimalist": 0.8,
        "warm": 0.7, "edgy": 0.6, "playful": 0.5, "generic": 0.3,
    }
    tone = profile.get("aesthetic_tone", "generic")
    score += 0.15 * tone_map.get(tone, 0.5)

    # promo_intensity (反向): 低促销感更好
    promo = profile.get("promo_intensity", 5)
    if isinstance(promo, (int, float)):
        score += 0.15 * (1.0 - promo / 10.0)

    # text_density: 适中最优 (3-5 = 1.0, 偏离递减)
    text_d = profile.get("text_density", 5)
    if isinstance(text_d, (int, float)):
        optimal = 4.0
        deviation = abs(text_d - optimal) / 6.0
        score += 0.10 * max(0.0, 1.0 - deviation)

    # visual_hooks 数量
    hooks = profile.get("visual_hooks", [])
    if isinstance(hooks, list):
        score += 0.10 * min(len(hooks) / 3.0, 1.0)

    # visual_risks (反向)
    risks = profile.get("visual_risks", [])
    if isinstance(risks, list):
        score += 0.10 * max(0.0, 1.0 - len(risks) / 3.0)

    # consistency_score
    consistency = profile.get("consistency_score", 7)
    if isinstance(consistency, (int, float)):
        score += 0.05 * (consistency / 10.0)

    return round(min(max(score, 0.0), 1.0), 3)
