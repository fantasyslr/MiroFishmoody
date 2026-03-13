"""
Market-Making Judge — 做市商-交易员迭代对决机制

替代传统的 3-judge 多数投票，通过做市商出价 → 交易员攻击 →
做市商更新的迭代循环来收敛概率判断。

启用方式：环境变量 USE_MARKET_JUDGE=true
"""

import json
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger
from ..models.evaluation import PairwiseResult
from ..config import Config

logger = get_logger('ranker.services.market_judge')

MAX_ROUNDS = 4
CONVERGENCE_THRESHOLD = 0.05

MARKET_MAKER_SYSTEM = """你是一个做市商（Market Maker），负责对两个 campaign 方案进行概率定价。
你需要基于方案的整体质量、受众契合度、执行可行性等维度，给出方案 A 胜出的概率。

Moody Lenses 背景：独立美妆隐形眼镜品牌，两条产品线 colored_lenses 和 moodyPlus。

输出严格 JSON 格式：
{"probability_a": 0.6, "reasoning": "你的判断理由"}

probability_a 表示方案 A 胜出的概率（0-1），方案 B 胜出概率 = 1 - probability_a。"""

TRADER_SYSTEM = """你是一个交易员（Trader），你的目标是找到做市商判断中的盲点和偏差。
你需要针对做市商给出的概率进行质疑和攻击，找出被低估或高估的因素。

Moody Lenses 背景：独立美妆隐形眼镜品牌，两条产品线 colored_lenses 和 moodyPlus。

输出严格 JSON 格式：
{"challenge": "你的攻击论据", "suggested_probability_a": 0.45, "reasoning": "为什么你认为概率应该调整"}"""

UPDATE_SYSTEM = """你是做市商（Market Maker），之前你给出了一个概率判断，现在交易员提出了质疑。
请认真考虑交易员的论据，然后更新你的概率判断。如果交易员说得有道理就调整，说得没道理就坚持。

输出严格 JSON 格式：
{"updated_probability_a": 0.55, "reasoning": "你更新判断的理由", "accepted_challenge": true}

accepted_challenge 表示你是否认可交易员的部分或全部论据。"""


class MarketJudge:
    """Market-Making 式的方案对决"""

    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or LLMClient()

    def _format_campaign(self, campaign) -> str:
        parts = [
            f"方案名称：{campaign.name}",
            f"产品线：{campaign.product_line.value}",
            f"目标受众：{campaign.target_audience}",
            f"核心信息：{campaign.core_message}",
        ]
        if campaign.channels:
            parts.append(f"渠道：{', '.join(campaign.channels)}")
        if campaign.creative_direction:
            parts.append(f"创意方向：{campaign.creative_direction}")
        return "\n".join(parts)

    def evaluate_pair(self, a, b) -> PairwiseResult:
        """做市商-交易员迭代对决"""
        campaign_text = f"=== 方案 A ===\n{self._format_campaign(a)}\n\n=== 方案 B ===\n{self._format_campaign(b)}"

        # Round 1: Market maker initial pricing
        mm_result = {}
        try:
            mm_result = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": MARKET_MAKER_SYSTEM},
                    {"role": "user", "content": f"请对以下两个方案进行概率定价：\n\n{campaign_text}"},
                ],
                temperature=0.4,
            )
            prob_a = float(mm_result.get("probability_a", 0.5))
            prob_a = max(0.05, min(0.95, prob_a))
        except Exception as e:
            logger.warning(f"做市商初始定价失败: {e}")
            prob_a = 0.5

        history = [{"round": 0, "probability_a": prob_a, "reasoning": mm_result.get("reasoning", "")}]

        # Iterative rounds
        for round_num in range(1, MAX_ROUNDS + 1):
            # Trader challenge
            higher_label = "A" if prob_a > 0.5 else "B"
            try:
                trader_result = self.llm.chat_json(
                    messages=[
                        {"role": "system", "content": TRADER_SYSTEM},
                        {"role": "user", "content": (
                            f"当前做市商认为方案 A 胜出概率为 {prob_a:.2f}（方案 B 为 {1-prob_a:.2f}）。\n"
                            f"做市商更看好方案 {higher_label}。\n"
                            f"请针对方案 {higher_label} 提出最有力的反对论据。\n\n{campaign_text}"
                        )},
                    ],
                    temperature=0.5,
                )
                challenge = trader_result.get("challenge", "")
                suggested = float(trader_result.get("suggested_probability_a", prob_a))
            except Exception as e:
                logger.warning(f"交易员攻击失败 (round {round_num}): {e}")
                break

            # Market maker update
            try:
                update_result = self.llm.chat_json(
                    messages=[
                        {"role": "system", "content": UPDATE_SYSTEM},
                        {"role": "user", "content": (
                            f"你之前给的概率是 A={prob_a:.2f}。\n"
                            f"交易员的质疑：{challenge}\n"
                            f"交易员建议的概率：A={suggested:.2f}\n\n"
                            f"请考虑后更新你的判断。\n\n{campaign_text}"
                        )},
                    ],
                    temperature=0.3,
                )
                new_prob = float(update_result.get("updated_probability_a", prob_a))
                new_prob = max(0.05, min(0.95, new_prob))
            except Exception as e:
                logger.warning(f"做市商更新失败 (round {round_num}): {e}")
                break

            history.append({
                "round": round_num,
                "challenge": challenge,
                "probability_a": new_prob,
                "accepted": update_result.get("accepted_challenge", False),
                "reasoning": update_result.get("reasoning", ""),
            })

            # Check convergence
            if abs(new_prob - prob_a) < CONVERGENCE_THRESHOLD:
                logger.info(f"Market judge converged at round {round_num}: {new_prob:.3f}")
                prob_a = new_prob
                break

            prob_a = new_prob

        # Build PairwiseResult
        if prob_a > 0.55:
            winner_id = a.id
        elif prob_a < 0.45:
            winner_id = b.id
        else:
            winner_id = None  # too close to call

        votes = [{
            "judge_id": "market_maker",
            "winner": winner_id or "tie",
            "reasoning": f"Final probability A={prob_a:.3f}, B={1-prob_a:.3f}. Converged in {len(history)} rounds.",
            "market_history": history,
        }]

        return PairwiseResult(
            campaign_a_id=a.id,
            campaign_b_id=b.id,
            winner_id=winner_id,
            votes=votes,
            dimensions={},
        )

    def evaluate_all(self, campaigns):
        """Evaluate all pairs, return (pairwise_results, bt_scores)"""
        from .pairwise_judge import PairwiseJudge

        pairwise_results = []
        for i in range(len(campaigns)):
            for j in range(i + 1, len(campaigns)):
                result = self.evaluate_pair(campaigns[i], campaigns[j])
                pairwise_results.append(result)

        # Compute BT scores using the same static method from PairwiseJudge
        bt_scores = PairwiseJudge._bradley_terry(
            campaigns, pairwise_results
        )

        return pairwise_results, bt_scores
