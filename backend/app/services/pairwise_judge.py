"""
Pairwise Judge Engine — 方案两两对决

每对方案由 3 个独立 judge agent 评审，多数票表决。
使用 Bradley-Terry 模型计算全局排序。
"""

import math
from itertools import combinations
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..config import Config
from ..utils.llm_client import LLMClient
from ..utils.retry import retry_with_backoff
from ..utils.logger import get_logger
from ..utils.image_helpers import resolve_image_path, image_to_base64_part
from ..models.campaign import Campaign, ProductLine
from ..models.evaluation import PairwiseResult

logger = get_logger('ranker.pairwise_judge')

DIMENSIONS = [
    "reach_potential",       # 触达潜力
    "conversion_potential",  # 转化潜力
    "brand_alignment",       # 品牌一致性
    "risk_level",            # 风险水平（低风险方胜出）
    "feasibility",           # 可执行性
]

JUDGE_PERSPECTIVES = [
    {
        "id": "strategist",
        "name": "策略视角",
        "system_prompt": (
            "你是一名资深电商营销策略师，有10年美妆品牌操盘经验。"
            "你关注营销方案的整体策略逻辑：目标人群是否精准、核心信息是否有差异化、"
            "渠道组合是否合理、创意方向是否有记忆点。"
            "你评判的标准是：这个方案在战略层面是否比另一个更优。"
        ),
    },
    {
        "id": "consumer",
        "name": "用户视角",
        "system_prompt": (
            "你是一名消费者洞察专家，擅长从用户心理角度分析营销方案。"
            "你关注：目标用户看到这个方案后的第一反应是什么？会不会产生购买冲动？"
            "信息是否清晰？有没有认知门槛？促销机制是否有吸引力？"
            "你评判的标准是：哪个方案更能打动目标消费者。"
        ),
    },
    {
        "id": "brand_guardian",
        "name": "品牌视角",
        "system_prompt": (
            "你是 Moody Lenses 的品牌守护者。"
            "Moody 的定位是功能+美学，不打价格战。"
            "moodyPlus 是专业功能线，对标 Acuvue Define，强调临床级透氧率。"
            "colored lenses 是美妆线，强调自然好看。"
            "你关注：方案是否符合品牌调性？会不会损害品牌价值？"
            "有没有过度促销或低价暗示？创意方向是否与品牌形象一致？"
            "你评判的标准是：哪个方案对品牌长期价值更有利。"
        ),
    },
]

DEVIL_ADVOCATE_PERSPECTIVE = {
    "id": "devil_advocate",
    "name": "品牌怀疑者",
    "system_prompt": (
        "你是一个对所有营销方案持怀疑态度的品牌批评者。"
        "你的职责是挑战每一个看似正面的结论，找出方案中的潜在风险、过度承诺和未经验证的假设。"
        "你不相信任何'创新'声称，不相信'精准触达'，不相信'品牌溢价'。"
        "你评判的标准是：哪个方案更可能失败、浪费预算、或者损害品牌。"
        "投票给你认为'更不糟糕'的那个，但始终保持怀疑。"
    ),
}

JUDGE_USER_PROMPT = """请比较以下两个营销方案，判断哪个更优。

## 方案 A: {name_a}
- 产品线：{pl_a}
- 目标受众：{audience_a}
- 核心信息：{message_a}
- 渠道：{channels_a}
- 创意方向：{creative_a}
{extra_a}

## 方案 B: {name_b}
- 产品线：{pl_b}
- 目标受众：{audience_b}
- 核心信息：{message_b}
- 渠道：{channels_b}
- 创意方向：{creative_b}
{extra_b}

请从以下 5 个维度逐一对比，然后给出总体判断。

维度：
1. reach_potential — 触达潜力（哪个能触达更多目标用户）
2. conversion_potential — 转化潜力（哪个更可能驱动购买）
3. brand_alignment — 品牌一致性（哪个更符合 Moody 品牌调性）
4. risk_level — 风险水平（哪个风险更低，低风险方胜出）
5. feasibility — 可执行性（哪个更容易落地执行）

请用 JSON 格式输出：
{{
  "dimensions": {{
    "reach_potential": "A" 或 "B" 或 "tie",
    "conversion_potential": "A" 或 "B" 或 "tie",
    "brand_alignment": "A" 或 "B" 或 "tie",
    "risk_level": "A" 或 "B" 或 "tie",
    "feasibility": "A" 或 "B" 或 "tie"
  }},
  "winner": "A" 或 "B" 或 "tie",
  "reasoning": "2-3句话说明你的总体判断理由"
}}"""


def _pl_label(pl: ProductLine) -> str:
    return "彩色美瞳" if pl == ProductLine.COLORED else "moodyPlus 硅水凝胶"


def _extra_block(c: Campaign) -> str:
    parts = []
    if c.budget_range:
        parts.append(f"- 预算：{c.budget_range}")
    if c.promo_mechanic:
        parts.append(f"- 促销机制：{c.promo_mechanic}")
    if c.kv_description:
        parts.append(f"- 主视觉：{c.kv_description}")
    return "\n".join(parts)


def _build_image_parts(campaign: Campaign, label: str) -> list:
    """为一个 campaign 的图片构建 OpenAI Vision content parts"""
    parts = []
    image_paths = getattr(campaign, 'image_paths', None) or []
    for img_url in image_paths[:5]:
        resolved = resolve_image_path(img_url)
        if not resolved:
            continue
        img_part = image_to_base64_part(resolved)
        if img_part:
            parts.append(img_part)
    return parts


VISUAL_INSTRUCTION = (
    "\n\n如果提供了素材图，请同时参考视觉效果判断触达、转化、品牌调性、风险和可执行性；"
    "若图文冲突，请明确指出，并以实际视觉呈现为重要依据。"
)


class PairwiseJudge:
    """方案两两对决评审引擎"""

    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or LLMClient()

    def judge_pair(
        self, a: Campaign, b: Campaign, judge: Dict[str, Any]
    ) -> Dict[str, Any]:
        """单个 judge 评审一对方案，有图片时自动走多模态"""
        user_text = JUDGE_USER_PROMPT.format(
            name_a=a.name, pl_a=_pl_label(a.product_line),
            audience_a=a.target_audience, message_a=a.core_message,
            channels_a=", ".join(a.channels), creative_a=a.creative_direction,
            extra_a=_extra_block(a),
            name_b=b.name, pl_b=_pl_label(b.product_line),
            audience_b=b.target_audience, message_b=b.core_message,
            channels_b=", ".join(b.channels), creative_b=b.creative_direction,
            extra_b=_extra_block(b),
        )

        a_imgs = _build_image_parts(a, "A")
        b_imgs = _build_image_parts(b, "B")
        has_images = bool(a_imgs or b_imgs)

        system_msg = {"role": "system", "content": judge["system_prompt"]}

        if has_images:
            content_parts: list = [{"type": "text", "text": user_text + VISUAL_INSTRUCTION}]
            if a_imgs:
                content_parts.append({"type": "text", "text": f"--- 方案 A 素材图 ({len(a_imgs)} 张) ---"})
                content_parts.extend(a_imgs)
            if b_imgs:
                content_parts.append({"type": "text", "text": f"--- 方案 B 素材图 ({len(b_imgs)} 张) ---"})
                content_parts.extend(b_imgs)
            user_msg = {"role": "user", "content": content_parts}
            result = self.llm.chat_multimodal_json(
                messages=[system_msg, user_msg],
                temperature=Config.JUDGE_TEMPERATURE,
            )
        else:
            user_msg = {"role": "user", "content": user_text}
            result = self.llm.chat_json(
                messages=[system_msg, user_msg],
                temperature=Config.JUDGE_TEMPERATURE,
                max_tokens=1024,
            )

        return {
            "judge_id": judge["id"],
            "judge_name": judge["name"],
            "winner": result.get("winner", "tie"),
            "dimensions": result.get("dimensions", {}),
            "reasoning": result.get("reasoning", ""),
            "dissent": judge["id"] == "devil_advocate",
        }

    @staticmethod
    def _flip_vote(vote: Dict[str, Any]) -> Dict[str, Any]:
        """Flip a swapped-order vote back to original A/B labels.

        When judge evaluates (B, A) instead of (A, B), the labels are reversed:
        judge's "A" = original B, judge's "B" = original A.
        """
        flip_map = {"A": "B", "B": "A", "tie": "tie"}
        flipped_dims = {}
        for dim, val in vote.get("dimensions", {}).items():
            flipped_dims[dim] = flip_map.get(val, val)
        return {
            **vote,
            "winner": flip_map.get(vote.get("winner", "tie"), vote.get("winner", "tie")),
            "dimensions": flipped_dims,
        }

    def evaluate_pair(self, a: Campaign, b: Campaign) -> PairwiseResult:
        """3 个 judge 对一对方案投票，正反序各一轮，多数票表决。

        Position-swap debiasing: each judge evaluates (A,B) then (B,A).
        The swapped results are flipped back to original labels and used to
        detect position bias (position_swap_consistent flag).
        Final winner is determined from the normal-order round only.
        """
        votes = []
        swap_votes = []

        for judge in JUDGE_PERSPECTIVES:
            # Normal order: A vs B
            try:
                vote = self._safe_judge(a, b, judge)
                votes.append(vote)
            except Exception as e:
                logger.error(f"Judge {judge['id']} 评审 {a.id} vs {b.id} 失败: {e}")

            # Swapped order: B vs A
            try:
                swap_vote_raw = self._safe_judge(b, a, judge)
                swap_vote = self._flip_vote(swap_vote_raw)
                swap_votes.append(swap_vote)
            except Exception as e:
                logger.error(f"Judge {judge['id']} 反序评审 {b.id} vs {a.id} 失败: {e}")

        # Normal-order majority
        a_wins_normal = sum(1 for v in votes if v["winner"] == "A")
        b_wins_normal = sum(1 for v in votes if v["winner"] == "B")

        if a_wins_normal > b_wins_normal:
            winner_id = a.id
            normal_majority = "A"
        elif b_wins_normal > a_wins_normal:
            winner_id = b.id
            normal_majority = "B"
        else:
            winner_id = None
            normal_majority = "tie"

        # Swap-order majority (after flipping back to original labels)
        a_wins_swap = sum(1 for v in swap_votes if v["winner"] == "A")
        b_wins_swap = sum(1 for v in swap_votes if v["winner"] == "B")

        if a_wins_swap > b_wins_swap:
            swap_majority = "A"
        elif b_wins_swap > a_wins_swap:
            swap_majority = "B"
        else:
            swap_majority = "tie"

        position_swap_consistent = (normal_majority == swap_majority)

        # 合并各维度结果 (from normal-order votes only)
        merged_dims = {}
        for dim in DIMENSIONS:
            dim_votes = [v["dimensions"].get(dim, "tie") for v in votes]
            a_count = dim_votes.count("A")
            b_count = dim_votes.count("B")
            if a_count > b_count:
                merged_dims[dim] = a.id
            elif b_count > a_count:
                merged_dims[dim] = b.id
            else:
                merged_dims[dim] = "tie"

        return PairwiseResult(
            campaign_a_id=a.id,
            campaign_b_id=b.id,
            winner_id=winner_id,
            votes=votes,
            dimensions=merged_dims,
            position_swap_consistent=position_swap_consistent,
            swap_votes=swap_votes,
        )

    def evaluate_all(self, campaigns: List[Campaign], max_workers: int = 4) -> Tuple[List[PairwiseResult], Dict[str, float]]:
        """
        所有方案两两对决。
        返回: (pairwise_results, bt_scores)
        bt_scores: campaign_id → Bradley-Terry 强度值
        """
        pairs = list(combinations(campaigns, 2))
        logger.info(f"开始 Pairwise 对决: {len(campaigns)} 个方案, {len(pairs)} 对")

        results: List[PairwiseResult] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(self.evaluate_pair, a, b): (a.id, b.id)
                for a, b in pairs
            }
            for future in as_completed(future_map):
                aid, bid = future_map[future]
                try:
                    result = future.result()
                    results.append(result)
                    w = result.winner_id or "tie"
                    logger.info(f"  {aid} vs {bid}: winner={w}")
                except Exception as e:
                    logger.error(f"  {aid} vs {bid} 失败: {e}")

        # Bradley-Terry 排序
        bt_scores = self._bradley_terry(campaigns, results)
        return results, bt_scores

    @retry_with_backoff(max_retries=2, initial_delay=1.0)
    def _safe_judge(self, a: Campaign, b: Campaign, judge: Dict[str, Any]) -> Dict[str, Any]:
        return self.judge_pair(a, b, judge)

    @staticmethod
    def _bradley_terry(
        campaigns: List[Campaign],
        results: List[PairwiseResult],
        iterations: int = 20,
    ) -> Dict[str, float]:
        """
        Bradley-Terry 模型计算全局排序强度。
        迭代更新每个方案的强度参数 p_i，使得 P(i beats j) = p_i / (p_i + p_j)。
        """
        ids = [c.id for c in campaigns]
        n = len(ids)
        # 胜负矩阵
        wins = {i: {j: 0 for j in ids} for i in ids}
        for r in results:
            if r.winner_id == r.campaign_a_id:
                wins[r.campaign_a_id][r.campaign_b_id] += 1
            elif r.winner_id == r.campaign_b_id:
                wins[r.campaign_b_id][r.campaign_a_id] += 1
            else:
                # tie = 各加 0.5
                wins[r.campaign_a_id][r.campaign_b_id] += 0.5
                wins[r.campaign_b_id][r.campaign_a_id] += 0.5

        # 初始化强度
        strength = {i: 1.0 for i in ids}

        for _ in range(iterations):
            new_strength = {}
            for i in ids:
                numerator = sum(wins[i][j] for j in ids if j != i)
                denominator = sum(
                    (wins[i][j] + wins[j][i]) / (strength[i] + strength[j])
                    for j in ids if j != i
                ) if n > 1 else 1.0
                new_strength[i] = numerator / denominator if denominator > 0 else 1.0
            # 归一化
            total = sum(new_strength.values())
            strength = {i: v / total * n for i, v in new_strength.items()}

        return strength


class MultiJudgeEnsemble(PairwiseJudge):
    """Position-alternating multi-judge ensemble.

    Judges at even indices evaluate (A, B); odd indices evaluate (B, A) then flip.
    All normalized votes collected in PairwiseResult.votes.
    """

    def __init__(self, llm_client: LLMClient = None, num_judges: int = None):
        super().__init__(llm_client=llm_client)
        # Include devil's advocate as 4th perspective alongside JUDGE_PERSPECTIVES
        self._perspectives = JUDGE_PERSPECTIVES + [DEVIL_ADVOCATE_PERSPECTIVE]
        # Default: repeat all perspectives twice (8 judges) for balanced normal + swapped
        self._num_judges = num_judges or (len(self._perspectives) * 2 - 1)  # 7 default

    def evaluate_pair(self, a: Campaign, b: Campaign) -> PairwiseResult:
        """Alternate (A,B) and (B,A) across judge slots. All votes normalized to A/B labels."""
        perspectives = (self._perspectives * ((self._num_judges // len(self._perspectives)) + 1))
        perspectives = perspectives[:self._num_judges]

        all_votes = []
        for idx, judge in enumerate(perspectives):
            if idx % 2 == 0:
                # Normal order: A vs B
                try:
                    vote = self._safe_judge(a, b, judge)
                    vote["position"] = "normal"
                    all_votes.append(vote)
                except Exception as e:
                    logger.error(f"MultiJudge[{idx}] normal {a.id} vs {b.id}: {e}")
            else:
                # Swapped order: B vs A, then flip labels back to A/B
                try:
                    raw = self._safe_judge(b, a, judge)
                    vote = self._flip_vote(raw)
                    vote["position"] = "swapped"
                    all_votes.append(vote)
                except Exception as e:
                    logger.error(f"MultiJudge[{idx}] swapped {b.id} vs {a.id}: {e}")

        # Majority across all normalized votes
        a_wins = sum(1 for v in all_votes if v["winner"] == "A")
        b_wins = sum(1 for v in all_votes if v["winner"] == "B")

        if a_wins > b_wins:
            winner_id = a.id
        elif b_wins > a_wins:
            winner_id = b.id
        else:
            winner_id = None

        # Dimension consensus across all votes
        merged_dims = {}
        for dim in DIMENSIONS:
            dim_votes = [v["dimensions"].get(dim, "tie") for v in all_votes]
            a_count = dim_votes.count("A")
            b_count = dim_votes.count("B")
            merged_dims[dim] = (
                a.id if a_count > b_count else (b.id if b_count > a_count else "tie")
            )

        # position_swap_consistent: check if normal sub-majority matches swapped sub-majority
        normal_votes = [v for v in all_votes if v.get("position") == "normal"]
        swap_votes_list = [v for v in all_votes if v.get("position") == "swapped"]
        normal_a = sum(1 for v in normal_votes if v["winner"] == "A")
        normal_b = sum(1 for v in normal_votes if v["winner"] == "B")
        swap_a = sum(1 for v in swap_votes_list if v["winner"] == "A")
        swap_b = sum(1 for v in swap_votes_list if v["winner"] == "B")
        normal_majority = "A" if normal_a > normal_b else ("B" if normal_b > normal_a else "tie")
        swap_majority = "A" if swap_a > swap_b else ("B" if swap_b > swap_a else "tie")
        position_swap_consistent = (normal_majority == swap_majority)

        return PairwiseResult(
            campaign_a_id=a.id,
            campaign_b_id=b.id,
            winner_id=winner_id,
            votes=all_votes,
            dimensions=merged_dims,
            position_swap_consistent=position_swap_consistent,
            swap_votes=swap_votes_list,
        )
