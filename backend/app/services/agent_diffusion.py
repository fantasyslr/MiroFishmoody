"""
Agent Diffusion Layer — Brandiction v1

轻量级消费者 agent 仿真：通过社会扩散模拟预测认知维度变化。
不是暴力全连接，而是稀疏图 + 短轮次 + 只决定不确定维度。

设计原则（"巧力不是大力"）：
  - 6-8 个核心 archetype，每类复制 3-5 个（参数扰动）→ 24-36 agents
  - 5-8 轮扩散，稀疏传播图
  - agents 只影响不确定维度：social_proof / skepticism / competitor_pressure
  - science_credibility / comfort_trust / price_sensitivity 由规则 + 历史数据驱动
  - archetype 初始化参数来自真实用户画像

核心流程：
  1. 给定 intervention plan + 当前 BrandState
  2. 初始化 agent 群体（archetype × clones）
  3. 计算 intervention 对每个 agent 的直接曝光影响
  4. 多轮社会扩散（稀疏邻居图）
  5. 聚合 agent 群体的认知变化 → delta on social_proof / skepticism / competitor_pressure
"""

import math
import random
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from ..models.brand_state import PERCEPTION_DIMENSIONS


# ------------------------------------------------------------------
# Agent 可影响的维度（不确定维度）
# ------------------------------------------------------------------

AGENT_DIMENSIONS = ["social_proof", "skepticism", "competitor_pressure"]

# 规则驱动维度 — agents 不碰这些
RULE_DIMENSIONS = ["science_credibility", "comfort_trust", "aesthetic_affinity", "price_sensitivity"]


# ------------------------------------------------------------------
# Consumer Archetypes
# ------------------------------------------------------------------

@dataclass
class ConsumerArchetype:
    """消费者原型 — 定义一类人群的认知倾向"""
    archetype_id: str
    name: str
    # 对各渠道族的敏感度（0-1，影响曝光后态度变化幅度）
    channel_sensitivity: Dict[str, float] = field(default_factory=dict)
    # 各维度的基线倾向（影响扩散时的态度锚定）
    base_tendency: Dict[str, float] = field(default_factory=dict)
    # 社交影响力权重（影响扩散时对邻居的影响力）
    influence_weight: float = 1.0
    # 抗性（越高越不容易被邻居影响）
    resistance: float = 0.5
    # 克隆数量
    clone_count: int = 4


# 8 个核心 archetype — 基于 Moody 目标用户画像
CONSUMER_ARCHETYPES: List[ConsumerArchetype] = [
    ConsumerArchetype(
        archetype_id="trend_seeker",
        name="潮流追随者",
        channel_sensitivity={"short_video": 0.9, "social_seed": 0.8, "influencer": 0.9, "marketplace": 0.3},
        base_tendency={"social_proof": 0.7, "skepticism": 0.3, "competitor_pressure": 0.5},
        influence_weight=1.2,
        resistance=0.3,
        clone_count=5,
    ),
    ConsumerArchetype(
        archetype_id="careful_researcher",
        name="谨慎研究者",
        channel_sensitivity={"longform_content": 0.9, "search": 0.8, "social_seed": 0.4, "short_video": 0.3},
        base_tendency={"social_proof": 0.4, "skepticism": 0.7, "competitor_pressure": 0.6},
        influence_weight=0.8,
        resistance=0.7,
        clone_count=4,
    ),
    ConsumerArchetype(
        archetype_id="price_hunter",
        name="价格敏感型",
        channel_sensitivity={"marketplace": 0.9, "crm": 0.6, "short_video": 0.4, "influencer": 0.3},
        base_tendency={"social_proof": 0.5, "skepticism": 0.5, "competitor_pressure": 0.8},
        influence_weight=0.7,
        resistance=0.5,
        clone_count=4,
    ),
    ConsumerArchetype(
        archetype_id="brand_loyalist",
        name="品牌忠诚者",
        channel_sensitivity={"crm": 0.9, "dtc_site": 0.7, "longform_content": 0.5, "offline": 0.6},
        base_tendency={"social_proof": 0.6, "skepticism": 0.2, "competitor_pressure": 0.2},
        influence_weight=1.0,
        resistance=0.8,
        clone_count=3,
    ),
    ConsumerArchetype(
        archetype_id="social_follower",
        name="社交跟风者",
        channel_sensitivity={"social_seed": 0.9, "influencer": 0.8, "short_video": 0.7, "crm": 0.2},
        base_tendency={"social_proof": 0.8, "skepticism": 0.2, "competitor_pressure": 0.4},
        influence_weight=0.6,
        resistance=0.2,
        clone_count=5,
    ),
    ConsumerArchetype(
        archetype_id="health_conscious",
        name="健康关注者",
        channel_sensitivity={"longform_content": 0.8, "offline": 0.9, "search": 0.7, "short_video": 0.3},
        base_tendency={"social_proof": 0.4, "skepticism": 0.6, "competitor_pressure": 0.5},
        influence_weight=0.9,
        resistance=0.6,
        clone_count=4,
    ),
    ConsumerArchetype(
        archetype_id="aesthetic_maven",
        name="颜值党",
        channel_sensitivity={"social_seed": 0.9, "short_video": 0.8, "influencer": 0.7, "offline": 0.5},
        base_tendency={"social_proof": 0.7, "skepticism": 0.3, "competitor_pressure": 0.4},
        influence_weight=1.1,
        resistance=0.4,
        clone_count=4,
    ),
    ConsumerArchetype(
        archetype_id="pragmatist",
        name="实用主义者",
        channel_sensitivity={"marketplace": 0.7, "search": 0.6, "offline": 0.8, "longform_content": 0.5},
        base_tendency={"social_proof": 0.5, "skepticism": 0.5, "competitor_pressure": 0.6},
        influence_weight=0.8,
        resistance=0.6,
        clone_count=3,
    ),
]


# ------------------------------------------------------------------
# Agent Instance
# ------------------------------------------------------------------

@dataclass
class AgentInstance:
    """一个具体的消费者 agent（archetype clone + 参数扰动）"""
    agent_id: str
    archetype_id: str
    # 当前认知状态（只有 AGENT_DIMENSIONS）
    state: Dict[str, float] = field(default_factory=dict)
    # 渠道敏感度（含扰动）
    channel_sensitivity: Dict[str, float] = field(default_factory=dict)
    influence_weight: float = 1.0
    resistance: float = 0.5
    # 邻居 agent_id 列表
    neighbors: List[str] = field(default_factory=list)


# ------------------------------------------------------------------
# Diffusion Engine
# ------------------------------------------------------------------

class AgentDiffusionEngine:
    """
    消费者 agent 扩散引擎。

    用法：
      engine = AgentDiffusionEngine(seed=42)
      result = engine.simulate(
          intervention_plan={"theme": "science", "channel_mix": ["bilibili"], "budget": 50000},
          current_state={"social_proof": 0.5, "skepticism": 0.3, "competitor_pressure": 0.3},
          channel_family="longform_content",   # 由 PLATFORM_REGISTRY 解析
          rounds=6,
      )
      # result["agent_delta"] = {"social_proof": +0.03, "skepticism": -0.02, "competitor_pressure": 0.0}
    """

    def __init__(
        self,
        archetypes: Optional[List[ConsumerArchetype]] = None,
        seed: Optional[int] = None,
    ):
        self.archetypes = archetypes or CONSUMER_ARCHETYPES
        self.rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def simulate(
        self,
        intervention_plan: Dict[str, Any],
        current_state: Dict[str, float],
        channel_families: List[str],
        rounds: int = 6,
        exposure_strength: float = 1.0,
        platforms: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        运行 agent diffusion 仿真。

        Args:
            intervention_plan: {"theme": ..., "channel_mix": [...], "budget": ...}
            current_state: 当前 perception 的 AGENT_DIMENSIONS 部分
            channel_families: 此 intervention 涉及的渠道家族列表
            rounds: 扩散轮次 (5-8)
            exposure_strength: 曝光强度乘数（可用预算缩放）
            platforms: 原始平台名列表（用于 platform-level 差异化）

        Returns:
            {
                "agent_delta": {"social_proof": float, "skepticism": float, "competitor_pressure": float},
                "agent_count": int,
                "rounds": int,
                "convergence_round": int or None,
                "archetype_breakdown": {...},
            }
        """
        # 无有效曝光 → agent_delta 全零，不白跑仿真
        if exposure_strength <= 0 or (not channel_families and not platforms):
            zero_delta = {d: 0.0 for d in AGENT_DIMENSIONS}
            return {
                "agent_delta": zero_delta,
                "agent_count": sum(a.clone_count for a in self.archetypes),
                "rounds": 0,
                "convergence_round": 0,
                "archetype_breakdown": {
                    a.archetype_id: {"count": a.clone_count, "avg_state": dict(current_state), "delta": dict(zero_delta)}
                    for a in self.archetypes
                },
            }

        # 1. 初始化 agent 群体
        agents = self._init_agents(current_state)

        # 2. 构建稀疏邻居图
        self._build_sparse_graph(agents)

        # 3. 计算直接曝光影响（platform-aware）
        self._apply_exposure(agents, channel_families, exposure_strength, platforms=platforms)

        # 4. 多轮社会扩散
        convergence_round = None
        history: List[Dict[str, float]] = []

        for r in range(rounds):
            avg_before = self._aggregate(agents)
            self._diffuse_round(agents)
            avg_after = self._aggregate(agents)
            history.append(avg_after)

            # 收敛检测：各维度变化 < 0.001
            max_change = max(abs(avg_after[d] - avg_before[d]) for d in AGENT_DIMENSIONS)
            if max_change < 0.001 and convergence_round is None:
                convergence_round = r

        # 5. 聚合最终 delta
        final_avg = self._aggregate(agents)
        agent_delta = {}
        for d in AGENT_DIMENSIONS:
            agent_delta[d] = round(final_avg[d] - current_state.get(d, 0.5), 4)

        # 6. 按 archetype 统计
        archetype_breakdown = self._archetype_breakdown(agents, current_state)

        return {
            "agent_delta": agent_delta,
            "agent_count": len(agents),
            "rounds": rounds,
            "convergence_round": convergence_round,
            "archetype_breakdown": archetype_breakdown,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _init_agents(self, current_state: Dict[str, float]) -> List[AgentInstance]:
        """从 archetypes 生成 agent 群体，带参数扰动"""
        agents = []
        for arch in self.archetypes:
            for i in range(arch.clone_count):
                agent_id = f"{arch.archetype_id}-{i}"

                # 状态：从 base_tendency 和 current_state 混合，加扰动
                state = {}
                for d in AGENT_DIMENSIONS:
                    base = arch.base_tendency.get(d, 0.5)
                    current = current_state.get(d, 0.5)
                    # 70% 当前状态 + 30% archetype 倾向 + 扰动
                    mixed = 0.7 * current + 0.3 * base
                    jitter = self.rng.gauss(0, 0.03)
                    state[d] = max(0.0, min(1.0, mixed + jitter))

                # 渠道敏感度扰动
                ch_sens = {}
                for ch, v in arch.channel_sensitivity.items():
                    jitter = self.rng.gauss(0, 0.05)
                    ch_sens[ch] = max(0.0, min(1.0, v + jitter))

                agents.append(AgentInstance(
                    agent_id=agent_id,
                    archetype_id=arch.archetype_id,
                    state=state,
                    channel_sensitivity=ch_sens,
                    influence_weight=arch.influence_weight + self.rng.gauss(0, 0.1),
                    resistance=max(0.1, min(0.95, arch.resistance + self.rng.gauss(0, 0.05))),
                ))
        return agents

    def _build_sparse_graph(self, agents: List[AgentInstance]):
        """
        构建稀疏邻居图：
        - 同 archetype 内部：每人连 1-2 个同类
        - 跨 archetype：每人连 1-2 个不同类
        总共每人 2-4 个邻居，远低于 all-to-all
        """
        by_archetype: Dict[str, List[AgentInstance]] = {}
        for a in agents:
            by_archetype.setdefault(a.archetype_id, []).append(a)

        agent_map = {a.agent_id: a for a in agents}
        all_ids = [a.agent_id for a in agents]

        for a in agents:
            neighbors = set()

            # 同类邻居：1-2 个
            same = [x for x in by_archetype[a.archetype_id] if x.agent_id != a.agent_id]
            if same:
                k = min(2, len(same))
                for n in self.rng.sample(same, k):
                    neighbors.add(n.agent_id)

            # 跨类邻居：1-2 个
            others = [x for x in agents if x.archetype_id != a.archetype_id]
            if others:
                k = min(2, len(others))
                for n in self.rng.sample(others, k):
                    neighbors.add(n.agent_id)

            a.neighbors = list(neighbors)

    def _apply_exposure(
        self,
        agents: List[AgentInstance],
        channel_families: List[str],
        strength: float,
        platforms: Optional[List[str]] = None,
    ):
        """
        计算 intervention 对每个 agent 的直接曝光影响。

        Platform-aware：当传入 platforms 时，使用 CHANNEL_EFFECTIVENESS（含平台级 override）
        计算各维度的差异化调节系数，而非把同族平台视为相同。
        例如 redbook(aesthetic_affinity=1.4) vs weibo(skepticism=1.1) 虽同属 social_seed，
        但对各维度的影响方向和幅度不同。
        """
        if not channel_families:
            return

        # 计算 platform-level 维度调节系数（默认 1.0 = 退化为纯 family 行为）
        dim_modifiers = {d: 1.0 for d in AGENT_DIMENSIONS}
        if platforms:
            from .brand_state_engine import CHANNEL_EFFECTIVENESS
            for d in AGENT_DIMENSIONS:
                vals = []
                for p in platforms:
                    eff = CHANNEL_EFFECTIVENESS.get(p.lower().strip())
                    if eff and d in eff:
                        vals.append(eff[d])
                if vals:
                    dim_modifiers[d] = sum(vals) / len(vals)

        for agent in agents:
            # 取所有渠道族的平均敏感度
            sensitivities = [agent.channel_sensitivity.get(cf, 0.3) for cf in channel_families]
            avg_sensitivity = sum(sensitivities) / len(sensitivities) if sensitivities else 0.3

            # 曝光效果：敏感度高 → social_proof 上升、skepticism 下降
            effect = avg_sensitivity * strength * 0.05  # 基线效果 5%

            # social_proof: 平台系数 > 1 → 更强的社交证明效果
            sp_mod = dim_modifiers["social_proof"]
            agent.state["social_proof"] = min(1.0, agent.state["social_proof"] + effect * sp_mod)

            # skepticism: 平台系数 > 1 → 平台本身引发更多质疑 → 曝光减少质疑的效果变弱
            sk_mod = dim_modifiers["skepticism"]
            agent.state["skepticism"] = max(
                0.0, agent.state["skepticism"] - effect * 0.5 / max(0.5, sk_mod),
            )

            # competitor_pressure: 平台系数无直接 override 时保持默认
            cp_mod = dim_modifiers["competitor_pressure"]
            agent.state["competitor_pressure"] = max(
                0.0, agent.state["competitor_pressure"] - effect * 0.3 / max(0.5, cp_mod),
            )

    def _diffuse_round(self, agents: List[AgentInstance]):
        """
        一轮社会扩散：每个 agent 根据邻居状态更新自己。
        更新规则：
          new_state[d] = state[d] + (1 - resistance) × avg_neighbor_influence
          avg_neighbor_influence = sum(neighbor.influence_weight × (neighbor.state[d] - state[d])) / N
        """
        agent_map = {a.agent_id: a for a in agents}

        # 先读取当前快照，再更新（同步更新，非异步）
        snapshots = {a.agent_id: dict(a.state) for a in agents}

        for agent in agents:
            if not agent.neighbors:
                continue

            for d in AGENT_DIMENSIONS:
                influence_sum = 0.0
                weight_sum = 0.0
                for nid in agent.neighbors:
                    neighbor = agent_map.get(nid)
                    if not neighbor:
                        continue
                    n_state = snapshots[nid]
                    diff = n_state[d] - snapshots[agent.agent_id][d]
                    influence_sum += neighbor.influence_weight * diff
                    weight_sum += abs(neighbor.influence_weight)

                if weight_sum > 0:
                    avg_influence = influence_sum / weight_sum
                    # 应用抗性：resistance 高 → 不容易被拉动
                    update = (1.0 - agent.resistance) * avg_influence * 0.3
                    agent.state[d] = max(0.0, min(1.0, agent.state[d] + update))

    def _aggregate(self, agents: List[AgentInstance]) -> Dict[str, float]:
        """加权聚合所有 agent 的状态（按 influence_weight 加权平均）"""
        sums = {d: 0.0 for d in AGENT_DIMENSIONS}
        weight_total = 0.0
        for a in agents:
            w = max(0.1, a.influence_weight)
            for d in AGENT_DIMENSIONS:
                sums[d] += a.state[d] * w
            weight_total += w
        if weight_total > 0:
            return {d: sums[d] / weight_total for d in AGENT_DIMENSIONS}
        return {d: 0.5 for d in AGENT_DIMENSIONS}

    def _archetype_breakdown(
        self, agents: List[AgentInstance], initial_state: Dict[str, float],
    ) -> Dict[str, Dict[str, Any]]:
        """按 archetype 汇总 delta"""
        groups: Dict[str, List[AgentInstance]] = {}
        for a in agents:
            groups.setdefault(a.archetype_id, []).append(a)

        result = {}
        for arch_id, group in groups.items():
            avg = {d: 0.0 for d in AGENT_DIMENSIONS}
            for a in group:
                for d in AGENT_DIMENSIONS:
                    avg[d] += a.state[d]
            for d in avg:
                avg[d] /= len(group)

            delta = {d: round(avg[d] - initial_state.get(d, 0.5), 4) for d in AGENT_DIMENSIONS}
            result[arch_id] = {
                "count": len(group),
                "avg_state": {d: round(avg[d], 4) for d in AGENT_DIMENSIONS},
                "delta": delta,
            }
        return result


# ------------------------------------------------------------------
# Integration helper
# ------------------------------------------------------------------

def resolve_channel_families(channel_mix: Optional[List[str]]) -> List[str]:
    """从 channel_mix 中的平台名解析出渠道家族列表（去重）"""
    from .brand_state_engine import PLATFORM_REGISTRY, CHANNEL_FAMILIES

    if not channel_mix:
        return []
    families = set()
    for ch in channel_mix:
        ch_lower = ch.lower().strip()
        entry = PLATFORM_REGISTRY.get(ch_lower)
        if entry:
            families.add(entry[0])
        else:
            # 未知平台：检查是否直接是家族名
            if ch_lower in CHANNEL_FAMILIES:
                families.add(ch_lower)
    return sorted(families)


def compute_budget_exposure_strength(budget: Optional[float]) -> float:
    """
    从预算计算曝光强度乘数（与 brand_state_engine 的 budget scaling 对齐）。
    budget=0 或负值 → 0.0（零曝光，不给半档）。
    """
    if not budget or budget <= 0:
        return 0.0
    baseline = 50000.0
    strength = math.log2(budget / baseline + 1)
    return max(0.1, min(2.0, strength))
