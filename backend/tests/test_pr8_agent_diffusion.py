"""
PR8: Agent Diffusion Layer 测试

测试范围：
  1. ConsumerArchetype 结构完整性
  2. AgentDiffusionEngine 初始化 + 参数扰动
  3. 稀疏图构建
  4. 直接曝光效果
  5. 社会扩散收敛
  6. 聚合 + archetype breakdown
  7. resolve_channel_families 解析
  8. predict_with_diffusion 端到端
  9. 确定性（seed 固定 → 结果一致）
  10. 不确定维度 vs 规则维度的分离
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.agent_diffusion import (
    CONSUMER_ARCHETYPES,
    AGENT_DIMENSIONS,
    RULE_DIMENSIONS,
    AgentDiffusionEngine,
    AgentInstance,
    ConsumerArchetype,
    resolve_channel_families,
    compute_budget_exposure_strength,
)
from app.services.brand_state_engine import (
    BrandStateEngine,
    PERCEPTION_DIMENSIONS,
    PLATFORM_REGISTRY,
    CHANNEL_FAMILIES,
)
from app.models.brand_state import PERCEPTION_DIMENSIONS as PD
from app.services.brandiction_store import BrandictionStore


def _fresh_engine():
    return BrandStateEngine(BrandictionStore())


# ------------------------------------------------------------------
# Archetype 结构测试
# ------------------------------------------------------------------

class TestConsumerArchetypes(unittest.TestCase):

    def test_archetype_count(self):
        """应有 8 个核心 archetype"""
        self.assertEqual(len(CONSUMER_ARCHETYPES), 8)

    def test_total_agents_in_range(self):
        """总 agent 数应在 24-36 范围"""
        total = sum(a.clone_count for a in CONSUMER_ARCHETYPES)
        self.assertGreaterEqual(total, 24)
        self.assertLessEqual(total, 40)

    def test_each_archetype_has_id_and_name(self):
        for a in CONSUMER_ARCHETYPES:
            self.assertTrue(a.archetype_id)
            self.assertTrue(a.name)

    def test_base_tendency_only_agent_dims(self):
        """base_tendency 只包含 AGENT_DIMENSIONS"""
        for a in CONSUMER_ARCHETYPES:
            for d in a.base_tendency:
                self.assertIn(d, AGENT_DIMENSIONS,
                              f"archetype {a.archetype_id} base_tendency 含非 agent 维度 '{d}'")

    def test_channel_sensitivity_valid_families(self):
        """channel_sensitivity 中的 key 应是有效的渠道家族"""
        for a in CONSUMER_ARCHETYPES:
            for ch in a.channel_sensitivity:
                self.assertIn(ch, CHANNEL_FAMILIES,
                              f"archetype {a.archetype_id} 引用了无效渠道家族 '{ch}'")

    def test_archetype_ids_unique(self):
        ids = [a.archetype_id for a in CONSUMER_ARCHETYPES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_expected_archetypes_present(self):
        ids = {a.archetype_id for a in CONSUMER_ARCHETYPES}
        expected = {"trend_seeker", "careful_researcher", "price_hunter",
                    "brand_loyalist", "social_follower", "health_conscious",
                    "aesthetic_maven", "pragmatist"}
        self.assertEqual(ids, expected)


# ------------------------------------------------------------------
# AgentDiffusionEngine 测试
# ------------------------------------------------------------------

class TestAgentInit(unittest.TestCase):

    def test_init_creates_correct_count(self):
        engine = AgentDiffusionEngine(seed=42)
        agents = engine._init_agents({"social_proof": 0.5, "skepticism": 0.3, "competitor_pressure": 0.3})
        expected = sum(a.clone_count for a in CONSUMER_ARCHETYPES)
        self.assertEqual(len(agents), expected)

    def test_init_agents_have_all_dims(self):
        engine = AgentDiffusionEngine(seed=42)
        agents = engine._init_agents({"social_proof": 0.5, "skepticism": 0.3, "competitor_pressure": 0.3})
        for a in agents:
            for d in AGENT_DIMENSIONS:
                self.assertIn(d, a.state)
                self.assertGreaterEqual(a.state[d], 0.0)
                self.assertLessEqual(a.state[d], 1.0)

    def test_init_jitter_creates_variation(self):
        """同一 archetype 的 clones 不应完全相同"""
        engine = AgentDiffusionEngine(seed=42)
        agents = engine._init_agents({"social_proof": 0.5, "skepticism": 0.3, "competitor_pressure": 0.3})
        # 取 trend_seeker 的多个 clone
        seekers = [a for a in agents if a.archetype_id == "trend_seeker"]
        self.assertGreater(len(seekers), 1)
        # social_proof 值不应全相同
        sp_values = [a.state["social_proof"] for a in seekers]
        self.assertGreater(len(set(round(v, 4) for v in sp_values)), 1)


class TestSparseGraph(unittest.TestCase):

    def test_all_agents_have_neighbors(self):
        engine = AgentDiffusionEngine(seed=42)
        agents = engine._init_agents({"social_proof": 0.5, "skepticism": 0.3, "competitor_pressure": 0.3})
        engine._build_sparse_graph(agents)
        for a in agents:
            self.assertGreater(len(a.neighbors), 0, f"agent {a.agent_id} 没有邻居")

    def test_neighbor_count_sparse(self):
        """每个 agent 应有 2-4 个邻居（稀疏图）"""
        engine = AgentDiffusionEngine(seed=42)
        agents = engine._init_agents({"social_proof": 0.5, "skepticism": 0.3, "competitor_pressure": 0.3})
        engine._build_sparse_graph(agents)
        for a in agents:
            self.assertGreaterEqual(len(a.neighbors), 1)
            self.assertLessEqual(len(a.neighbors), 5)

    def test_no_self_loops(self):
        engine = AgentDiffusionEngine(seed=42)
        agents = engine._init_agents({"social_proof": 0.5, "skepticism": 0.3, "competitor_pressure": 0.3})
        engine._build_sparse_graph(agents)
        for a in agents:
            self.assertNotIn(a.agent_id, a.neighbors)

    def test_cross_archetype_connections(self):
        """应有跨 archetype 的连接"""
        engine = AgentDiffusionEngine(seed=42)
        agents = engine._init_agents({"social_proof": 0.5, "skepticism": 0.3, "competitor_pressure": 0.3})
        engine._build_sparse_graph(agents)
        agent_map = {a.agent_id: a for a in agents}
        cross_count = 0
        for a in agents:
            for nid in a.neighbors:
                if agent_map[nid].archetype_id != a.archetype_id:
                    cross_count += 1
        self.assertGreater(cross_count, 0)


class TestExposure(unittest.TestCase):

    def test_exposure_increases_social_proof(self):
        """曝光后 social_proof 应上升"""
        engine = AgentDiffusionEngine(seed=42)
        current = {"social_proof": 0.5, "skepticism": 0.3, "competitor_pressure": 0.3}
        agents = engine._init_agents(current)
        sp_before = sum(a.state["social_proof"] for a in agents) / len(agents)
        engine._apply_exposure(agents, ["short_video", "social_seed"], 1.0)
        sp_after = sum(a.state["social_proof"] for a in agents) / len(agents)
        self.assertGreater(sp_after, sp_before)

    def test_exposure_decreases_skepticism(self):
        """曝光后 skepticism 应下降"""
        engine = AgentDiffusionEngine(seed=42)
        current = {"social_proof": 0.5, "skepticism": 0.5, "competitor_pressure": 0.3}
        agents = engine._init_agents(current)
        sk_before = sum(a.state["skepticism"] for a in agents) / len(agents)
        engine._apply_exposure(agents, ["longform_content"], 1.0)
        sk_after = sum(a.state["skepticism"] for a in agents) / len(agents)
        self.assertLess(sk_after, sk_before)

    def test_no_channels_no_change(self):
        """无渠道 → 无变化"""
        engine = AgentDiffusionEngine(seed=42)
        current = {"social_proof": 0.5, "skepticism": 0.3, "competitor_pressure": 0.3}
        agents = engine._init_agents(current)
        states_before = [dict(a.state) for a in agents]
        engine._apply_exposure(agents, [], 1.0)
        for i, a in enumerate(agents):
            for d in AGENT_DIMENSIONS:
                self.assertAlmostEqual(a.state[d], states_before[i][d])

    def test_high_sensitivity_archetype_more_affected(self):
        """对渠道敏感度高的 archetype 受曝光影响更大"""
        engine = AgentDiffusionEngine(seed=42)
        current = {"social_proof": 0.5, "skepticism": 0.3, "competitor_pressure": 0.3}
        agents = engine._init_agents(current)
        sp_before = {a.agent_id: a.state["social_proof"] for a in agents}
        engine._apply_exposure(agents, ["short_video"], 1.0)

        # trend_seeker 对 short_video 敏感度 0.9
        # careful_researcher 对 short_video 敏感度 0.3
        seekers = [a for a in agents if a.archetype_id == "trend_seeker"]
        researchers = [a for a in agents if a.archetype_id == "careful_researcher"]

        avg_seeker_delta = sum(a.state["social_proof"] - sp_before[a.agent_id] for a in seekers) / len(seekers)
        avg_researcher_delta = sum(a.state["social_proof"] - sp_before[a.agent_id] for a in researchers) / len(researchers)
        self.assertGreater(avg_seeker_delta, avg_researcher_delta)


class TestDiffusion(unittest.TestCase):

    def test_simulate_returns_expected_keys(self):
        engine = AgentDiffusionEngine(seed=42)
        result = engine.simulate(
            intervention_plan={"theme": "science", "channel_mix": ["bilibili"]},
            current_state={"social_proof": 0.5, "skepticism": 0.3, "competitor_pressure": 0.3},
            channel_families=["longform_content"],
            rounds=6,
        )
        self.assertIn("agent_delta", result)
        self.assertIn("agent_count", result)
        self.assertIn("rounds", result)
        self.assertIn("convergence_round", result)
        self.assertIn("archetype_breakdown", result)

    def test_agent_delta_only_agent_dims(self):
        """agent_delta 只包含 AGENT_DIMENSIONS"""
        engine = AgentDiffusionEngine(seed=42)
        result = engine.simulate(
            intervention_plan={"theme": "beauty"},
            current_state={"social_proof": 0.5, "skepticism": 0.3, "competitor_pressure": 0.3},
            channel_families=["social_seed"],
        )
        for d in result["agent_delta"]:
            self.assertIn(d, AGENT_DIMENSIONS)

    def test_convergence_happens(self):
        """6 轮应该能收敛"""
        engine = AgentDiffusionEngine(seed=42)
        result = engine.simulate(
            intervention_plan={"theme": "science"},
            current_state={"social_proof": 0.5, "skepticism": 0.3, "competitor_pressure": 0.3},
            channel_families=["longform_content"],
            rounds=8,
        )
        self.assertIsNotNone(result["convergence_round"])

    def test_archetype_breakdown_complete(self):
        engine = AgentDiffusionEngine(seed=42)
        result = engine.simulate(
            intervention_plan={"theme": "beauty"},
            current_state={"social_proof": 0.5, "skepticism": 0.3, "competitor_pressure": 0.3},
            channel_families=["social_seed"],
        )
        for arch in CONSUMER_ARCHETYPES:
            self.assertIn(arch.archetype_id, result["archetype_breakdown"])
            bd = result["archetype_breakdown"][arch.archetype_id]
            self.assertIn("count", bd)
            self.assertIn("avg_state", bd)
            self.assertIn("delta", bd)


class TestDeterminism(unittest.TestCase):
    """seed 固定 → 结果一致"""

    def test_same_seed_same_result(self):
        for _ in range(3):
            e1 = AgentDiffusionEngine(seed=123)
            e2 = AgentDiffusionEngine(seed=123)
            state = {"social_proof": 0.5, "skepticism": 0.3, "competitor_pressure": 0.3}
            r1 = e1.simulate({"theme": "science"}, state, ["longform_content"])
            r2 = e2.simulate({"theme": "science"}, state, ["longform_content"])
            for d in AGENT_DIMENSIONS:
                self.assertAlmostEqual(r1["agent_delta"][d], r2["agent_delta"][d])

    def test_different_seed_different_result(self):
        state = {"social_proof": 0.5, "skepticism": 0.3, "competitor_pressure": 0.3}
        r1 = AgentDiffusionEngine(seed=1).simulate({"theme": "science"}, state, ["longform_content"])
        r2 = AgentDiffusionEngine(seed=999).simulate({"theme": "science"}, state, ["longform_content"])
        # 至少一个维度应该不同
        diffs = [abs(r1["agent_delta"][d] - r2["agent_delta"][d]) for d in AGENT_DIMENSIONS]
        self.assertGreater(max(diffs), 0.0001)


# ------------------------------------------------------------------
# resolve_channel_families 测试
# ------------------------------------------------------------------

class TestResolveChannelFamilies(unittest.TestCase):

    def test_known_platforms(self):
        result = resolve_channel_families(["douyin", "bilibili"])
        self.assertIn("short_video", result)
        self.assertIn("longform_content", result)

    def test_unknown_platform_skipped(self):
        result = resolve_channel_families(["unknown_xyz"])
        self.assertEqual(len(result), 0)

    def test_direct_family_name(self):
        """直接传入家族名也能识别"""
        result = resolve_channel_families(["crm"])
        self.assertIn("crm", result)

    def test_dedup(self):
        """douyin + tiktok 都是 short_video，应去重"""
        result = resolve_channel_families(["douyin", "tiktok"])
        self.assertEqual(result.count("short_video"), 1)

    def test_empty_input(self):
        self.assertEqual(resolve_channel_families(None), [])
        self.assertEqual(resolve_channel_families([]), [])


class TestBudgetExposureStrength(unittest.TestCase):

    def test_baseline_is_1(self):
        self.assertAlmostEqual(compute_budget_exposure_strength(50000), 1.0)

    def test_higher_budget_higher_strength(self):
        self.assertGreater(compute_budget_exposure_strength(100000), 1.0)

    def test_lower_budget_lower_strength(self):
        self.assertLess(compute_budget_exposure_strength(10000), 1.0)

    def test_zero_budget(self):
        """budget=0 → 零曝光，不给半档"""
        self.assertAlmostEqual(compute_budget_exposure_strength(0), 0.0)

    def test_negative_budget(self):
        self.assertAlmostEqual(compute_budget_exposure_strength(-1000), 0.0)

    def test_none_budget(self):
        self.assertAlmostEqual(compute_budget_exposure_strength(None), 0.0)

    def test_clamped(self):
        self.assertLessEqual(compute_budget_exposure_strength(10000000), 2.0)
        self.assertGreaterEqual(compute_budget_exposure_strength(100), 0.1)


# ------------------------------------------------------------------
# predict_with_diffusion 端到端测试
# ------------------------------------------------------------------

class TestPredictWithDiffusion(unittest.TestCase):

    def setUp(self):
        self.engine = _fresh_engine()

    def test_returns_all_expected_keys(self):
        plan = {"theme": "science", "channel_mix": ["bilibili"], "budget": 50000}
        result = self.engine.predict_with_diffusion(plan, diffusion_seed=42)
        self.assertIn("delta", result)
        self.assertIn("diffusion", result)
        self.assertIn("confidence", result)
        self.assertIn("reasoning", result)
        self.assertIn("agent diffusion", result["reasoning"])

    def test_diffusion_key_structure(self):
        plan = {"theme": "beauty", "channel_mix": ["redbook"], "budget": 30000}
        result = self.engine.predict_with_diffusion(plan, diffusion_seed=42)
        diff = result["diffusion"]
        self.assertIn("agent_delta", diff)
        self.assertIn("rule_delta", diff)
        self.assertIn("agent_count", diff)
        self.assertIn("rounds", diff)
        self.assertIn("archetype_breakdown", diff)

    def test_rule_dims_unchanged_by_diffusion(self):
        """规则维度不应被 diffusion 修改"""
        plan = {"theme": "science", "channel_mix": ["bilibili"], "budget": 50000}
        result_plain = self.engine.predict_impact(plan)
        result_diff = self.engine.predict_with_diffusion(plan, diffusion_seed=42)
        for d in RULE_DIMENSIONS:
            self.assertAlmostEqual(
                result_plain["delta"][d],
                result_diff["delta"][d],
                places=4,
                msg=f"规则维度 {d} 被 diffusion 修改了",
            )

    def test_agent_dims_differ_from_plain(self):
        """不确定维度应与纯规则预测不同（diffusion 有非零贡献）"""
        plan = {"theme": "science", "channel_mix": ["bilibili"], "budget": 50000}
        result_plain = self.engine.predict_impact(plan)
        result_diff = self.engine.predict_with_diffusion(plan, diffusion_seed=42)
        # 至少一个 agent 维度应不同
        diffs = []
        for d in AGENT_DIMENSIONS:
            diffs.append(abs(result_diff["delta"][d] - result_plain["delta"][d]))
        self.assertGreater(max(diffs), 0.0001)

    def test_confidence_higher_with_diffusion(self):
        """diffusion 应提升 confidence"""
        plan = {"theme": "comfort", "channel_mix": ["wechat_crm"], "budget": 20000}
        result_plain = self.engine.predict_impact(plan)
        result_diff = self.engine.predict_with_diffusion(plan, diffusion_seed=42)
        self.assertGreater(result_diff["confidence"], result_plain["confidence"])

    def test_deterministic_with_seed(self):
        plan = {"theme": "beauty", "channel_mix": ["instagram"], "budget": 50000}
        r1 = self.engine.predict_with_diffusion(plan, diffusion_seed=99)
        r2 = self.engine.predict_with_diffusion(plan, diffusion_seed=99)
        for d in PERCEPTION_DIMENSIONS:
            self.assertAlmostEqual(r1["delta"][d], r2["delta"][d])

    def test_delta_clamped(self):
        """merged delta 应在 [-0.3, 0.3] 范围"""
        plan = {"theme": "science", "channel_mix": ["bilibili", "zhihu"], "budget": 200000}
        result = self.engine.predict_with_diffusion(plan, diffusion_seed=42)
        for d, v in result["delta"].items():
            self.assertGreaterEqual(v, -0.3)
            self.assertLessEqual(v, 0.3)


class TestDiffusionDirectionality(unittest.TestCase):
    """验证 diffusion 对不同渠道 / 主题的方向性"""

    def setUp(self):
        self.engine = _fresh_engine()

    def test_short_video_boosts_social_proof_more(self):
        """短视频渠道应该对 social_proof 的 agent 影响更大"""
        plan_sv = {"theme": "beauty", "channel_mix": ["douyin"], "budget": 50000}
        plan_lf = {"theme": "beauty", "channel_mix": ["zhihu"], "budget": 50000}
        r_sv = self.engine.predict_with_diffusion(plan_sv, diffusion_seed=42)
        r_lf = self.engine.predict_with_diffusion(plan_lf, diffusion_seed=42)
        # 短视频的 agent social_proof delta 应 > 长内容
        self.assertGreater(
            r_sv["diffusion"]["agent_delta"]["social_proof"],
            r_lf["diffusion"]["agent_delta"]["social_proof"],
        )

    def test_crm_reduces_skepticism_more(self):
        """CRM 渠道 agent 对 skepticism 的下降更大（私域信任高）"""
        plan_crm = {"theme": "comfort", "channel_mix": ["wechat_crm"], "budget": 50000}
        plan_mp = {"theme": "comfort", "channel_mix": ["tmall"], "budget": 50000}
        r_crm = self.engine.predict_with_diffusion(plan_crm, diffusion_seed=42)
        r_mp = self.engine.predict_with_diffusion(plan_mp, diffusion_seed=42)
        # CRM 的 skepticism 下降应 >= marketplace
        self.assertLessEqual(
            r_crm["diffusion"]["agent_delta"]["skepticism"],
            r_mp["diffusion"]["agent_delta"]["skepticism"],
        )


# ------------------------------------------------------------------
# PR8.1: 语义修复测试
# ------------------------------------------------------------------

class TestZeroExposureEarlyReturn(unittest.TestCase):
    """无有效曝光时 agent_delta 应全零"""

    def test_budget_zero_gives_zero_delta(self):
        """budget=0 → exposure_strength=0 → agent_delta 全零"""
        engine = _fresh_engine()
        plan = {"theme": "science", "channel_mix": ["bilibili"], "budget": 0}
        result = engine.predict_with_diffusion(plan, diffusion_seed=42)
        for d in AGENT_DIMENSIONS:
            self.assertAlmostEqual(
                result["diffusion"]["agent_delta"][d], 0.0,
                msg=f"budget=0 时 agent_delta[{d}] 应为 0",
            )

    def test_no_channels_gives_zero_delta(self):
        """无渠道 → 无家族 → agent_delta 全零"""
        engine = AgentDiffusionEngine(seed=42)
        state = {"social_proof": 0.5, "skepticism": 0.3, "competitor_pressure": 0.3}
        result = engine.simulate(
            intervention_plan={"theme": "science"},
            current_state=state,
            channel_families=[],
            exposure_strength=1.0,
        )
        for d in AGENT_DIMENSIONS:
            self.assertAlmostEqual(result["agent_delta"][d], 0.0)

    def test_zero_exposure_returns_zero_rounds(self):
        """零曝光应返回 rounds=0"""
        engine = AgentDiffusionEngine(seed=42)
        state = {"social_proof": 0.5, "skepticism": 0.3, "competitor_pressure": 0.3}
        result = engine.simulate(
            intervention_plan={"theme": "science"},
            current_state=state,
            channel_families=["longform_content"],
            exposure_strength=0.0,
        )
        self.assertEqual(result["rounds"], 0)
        self.assertEqual(result["convergence_round"], 0)

    def test_zero_exposure_confidence_not_boosted(self):
        """budget=0 → diffusion 没跑 → confidence 不该加 0.05"""
        engine = _fresh_engine()
        plan = {"theme": "science", "channel_mix": ["bilibili"], "budget": 0}
        result_plain = engine.predict_impact(plan)
        result_diff = engine.predict_with_diffusion(plan, diffusion_seed=42)
        # confidence should be identical — diffusion added zero information
        self.assertAlmostEqual(
            result_plain["confidence"],
            result_diff["confidence"],
            places=4,
            msg="budget=0 时 confidence 不该被 diffusion 提升",
        )


class TestPlatformAwareDiffusion(unittest.TestCase):
    """平台级差异化测试 — 同族不同平台应产生不同 diffusion 结果"""

    def test_weibo_vs_redbook_same_family_different_result(self):
        """weibo (skepticism=1.1) vs redbook (aesthetic=1.4) 同属 social_seed 但结果不同"""
        state = {"social_proof": 0.5, "skepticism": 0.4, "competitor_pressure": 0.3}
        e1 = AgentDiffusionEngine(seed=42)
        r_redbook = e1.simulate(
            intervention_plan={"theme": "beauty", "channel_mix": ["redbook"]},
            current_state=state,
            channel_families=["social_seed"],
            platforms=["redbook"],
        )
        e2 = AgentDiffusionEngine(seed=42)
        r_weibo = e2.simulate(
            intervention_plan={"theme": "beauty", "channel_mix": ["weibo"]},
            current_state=state,
            channel_families=["social_seed"],
            platforms=["weibo"],
        )
        # 至少一个维度应不同
        diffs = [abs(r_redbook["agent_delta"][d] - r_weibo["agent_delta"][d]) for d in AGENT_DIMENSIONS]
        self.assertGreater(max(diffs), 0.0001,
                           "同族 social_seed 但 redbook vs weibo 应产生不同 diffusion 结果")

    def test_weibo_higher_skepticism_than_redbook(self):
        """weibo (skepticism=1.1) 应比 redbook 在 skepticism 下降上更弱（因为 weibo 激发更多质疑）"""
        state = {"social_proof": 0.5, "skepticism": 0.5, "competitor_pressure": 0.3}
        e1 = AgentDiffusionEngine(seed=42)
        r_redbook = e1.simulate(
            {"theme": "beauty"}, state, ["social_seed"], platforms=["redbook"],
        )
        e2 = AgentDiffusionEngine(seed=42)
        r_weibo = e2.simulate(
            {"theme": "beauty"}, state, ["social_seed"], platforms=["weibo"],
        )
        # weibo skepticism delta 应 >= redbook 的（即下降更少 or 上升更多）
        self.assertGreaterEqual(
            r_weibo["agent_delta"]["skepticism"],
            r_redbook["agent_delta"]["skepticism"],
            "weibo 平台的 skepticism 下降应比 redbook 更弱",
        )

    def test_platform_none_same_as_family_only(self):
        """不传 platforms 时应退化为纯 family 行为"""
        state = {"social_proof": 0.5, "skepticism": 0.3, "competitor_pressure": 0.3}
        e1 = AgentDiffusionEngine(seed=42)
        r_no_plat = e1.simulate(
            {"theme": "science"}, state, ["longform_content"], platforms=None,
        )
        e2 = AgentDiffusionEngine(seed=42)
        r_with_plat = e2.simulate(
            {"theme": "science"}, state, ["longform_content"], platforms=[],
        )
        for d in AGENT_DIMENSIONS:
            self.assertAlmostEqual(r_no_plat["agent_delta"][d], r_with_plat["agent_delta"][d])

    def test_predict_with_diffusion_passes_platforms(self):
        """predict_with_diffusion 应将 channel_mix 作为 platforms 传入"""
        engine = _fresh_engine()
        plan_rb = {"theme": "beauty", "channel_mix": ["redbook"], "budget": 50000}
        plan_wb = {"theme": "beauty", "channel_mix": ["weibo"], "budget": 50000}
        r_rb = engine.predict_with_diffusion(plan_rb, diffusion_seed=42)
        r_wb = engine.predict_with_diffusion(plan_wb, diffusion_seed=42)
        # 同族不同平台 → diffusion agent_delta 应不同
        diffs = [abs(r_rb["diffusion"]["agent_delta"][d] - r_wb["diffusion"]["agent_delta"][d])
                 for d in AGENT_DIMENSIONS]
        self.assertGreater(max(diffs), 0.0001)


if __name__ == "__main__":
    unittest.main()
