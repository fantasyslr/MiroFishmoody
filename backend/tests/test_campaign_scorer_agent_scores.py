"""
CampaignScorer agent_scores 参数测试 — Phase 15-02

Task 2 RED: 验证 agent_scores 混入逻辑和向后兼容性
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from app.models.campaign import Campaign, ProductLine
from app.models.evaluation import PanelScore, PairwiseResult
from app.models.agent_score import AgentScore
from app.services.campaign_scorer import CampaignScorer


def make_campaign(id: str, name: str):
    return Campaign(
        id=id, name=name, product_line=ProductLine.COLORED,
        target_audience="test", core_message="test",
        channels=["meta"], creative_direction="test",
    )


def make_panel(persona_id, campaign_id, score, n_objections=1):
    return PanelScore(
        persona_id=persona_id, persona_name=f"P_{persona_id}",
        campaign_id=campaign_id, score=score,
        objections=[f"obj_{i}" for i in range(n_objections)],
        strengths=["str_1"], reasoning="ok",
    )


def make_basic_setup():
    """返回两个 campaign 的基本测试环境"""
    campaigns = [make_campaign("a", "A"), make_campaign("b", "B")]
    panel = [
        make_panel("p1", "a", 8, 1),
        make_panel("p1", "b", 6, 1),
    ]
    pairwise = [PairwiseResult("a", "b", "a", [], {})]
    bt = {"a": 2.0, "b": 1.0}
    return campaigns, panel, pairwise, bt


class TestAgentScoresBackwardCompat:
    """向后兼容性测试 — 不传 agent_scores 时行为不变"""

    def test_no_agent_scores_returns_tuple(self):
        """不传 agent_scores 时正常返回 (rankings, scoreboard)"""
        campaigns, panel, pairwise, bt = make_basic_setup()
        scorer = CampaignScorer()
        result = scorer.score(campaigns, panel, pairwise, bt)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_none_agent_scores_same_as_no_arg(self):
        """agent_scores=None 与不传等价"""
        campaigns, panel, pairwise, bt = make_basic_setup()
        scorer = CampaignScorer()
        r1 = scorer.score(campaigns, panel, pairwise, bt)
        r2 = scorer.score(campaigns, panel, pairwise, bt, agent_scores=None)
        # rankings 排序和 composite_score 应相同
        assert r1[0][0].campaign_id == r2[0][0].campaign_id
        assert r1[0][0].composite_score == r2[0][0].composite_score

    def test_empty_agent_scores_same_as_no_arg(self):
        """agent_scores=[] 与不传等价"""
        campaigns, panel, pairwise, bt = make_basic_setup()
        scorer = CampaignScorer()
        r1 = scorer.score(campaigns, panel, pairwise, bt)
        r2 = scorer.score(campaigns, panel, pairwise, bt, agent_scores=[])
        assert r1[0][0].campaign_id == r2[0][0].campaign_id
        assert r1[0][0].composite_score == r2[0][0].composite_score


class TestAgentScoresMixIn:
    """agent_scores 混入逻辑测试"""

    def test_agent_score_changes_score(self):
        """传入 agent_scores 时，分数与不传时不同"""
        campaigns, panel, pairwise, bt = make_basic_setup()
        scorer = CampaignScorer()

        r_no_agent = scorer.score(campaigns, panel, pairwise, bt)
        # 给 campaign "a" 一个极低的 agent_score（拖低其得分）
        agent_scores = [AgentScore(agent_type="test", campaign_id="a", score=0.0, weight=1.0)]
        r_with_agent = scorer.score(campaigns, panel, pairwise, bt, agent_scores=agent_scores)

        a_no_agent = next(r for r in r_no_agent[0] if r.campaign_id == "a")
        a_with_agent = next(r for r in r_with_agent[0] if r.campaign_id == "a")
        # score 应该降低（composite_score = overall_score * 10）
        assert a_with_agent.composite_score < a_no_agent.composite_score

    def test_campaign_without_agent_score_unchanged(self):
        """没有 agent_scores 的 campaign 分数不变"""
        campaigns, panel, pairwise, bt = make_basic_setup()
        scorer = CampaignScorer()

        r_no_agent = scorer.score(campaigns, panel, pairwise, bt)
        # 只给 campaign "a" agent_score，campaign "b" 不应受影响
        agent_scores = [AgentScore(agent_type="test", campaign_id="a", score=1.0, weight=1.0)]
        r_with_agent = scorer.score(campaigns, panel, pairwise, bt, agent_scores=agent_scores)

        b_no_agent = next(r for r in r_no_agent[0] if r.campaign_id == "b")
        b_with_agent = next(r for r in r_with_agent[0] if r.campaign_id == "b")
        assert b_with_agent.composite_score == b_no_agent.composite_score

    def test_high_agent_score_boosts_campaign(self):
        """高 agent_score 能提升 campaign 得分"""
        campaigns, panel, pairwise, bt = make_basic_setup()
        scorer = CampaignScorer()

        r_no_agent = scorer.score(campaigns, panel, pairwise, bt)
        # 给 campaign "b"（原本分低）一个满分 agent_score
        agent_scores = [AgentScore(agent_type="boost", campaign_id="b", score=1.0, weight=1.0)]
        r_with_agent = scorer.score(campaigns, panel, pairwise, bt, agent_scores=agent_scores)

        b_no_agent = next(r for r in r_no_agent[0] if r.campaign_id == "b")
        b_with_agent = next(r for r in r_with_agent[0] if r.campaign_id == "b")
        assert b_with_agent.composite_score > b_no_agent.composite_score

    def test_weighted_average_multiple_agents(self):
        """多个 agent_scores 按 weight 加权平均"""
        campaigns, panel, pairwise, bt = make_basic_setup()
        scorer = CampaignScorer()

        r_no_agent = scorer.score(campaigns, panel, pairwise, bt)
        a_original = next(r for r in r_no_agent[0] if r.campaign_id == "a")
        original_score = a_original.composite_score / 10  # 还原到 0-1

        # 两个 agent: score=1.0 weight=1, score=0.0 weight=1 → 加权均值=0.5
        agent_scores = [
            AgentScore(agent_type="agent1", campaign_id="a", score=1.0, weight=1.0),
            AgentScore(agent_type="agent2", campaign_id="a", score=0.0, weight=1.0),
        ]
        r_with_agent = scorer.score(campaigns, panel, pairwise, bt, agent_scores=agent_scores)
        a_with_agent = next(r for r in r_with_agent[0] if r.campaign_id == "a")
        new_score = a_with_agent.composite_score / 10

        # AGENT_SCORE_WEIGHT 默认 0.1
        # expected = original * 0.9 + 0.5 * 0.1
        import app.services.campaign_scorer as cs_mod
        asw = cs_mod.AGENT_SCORE_WEIGHT
        expected = original_score * (1 - asw) + 0.5 * asw
        assert abs(new_score - expected) < 1e-9

    def test_unequal_weights(self):
        """不同 weight 的 agent_scores 按加权均值计算"""
        campaigns, panel, pairwise, bt = make_basic_setup()
        scorer = CampaignScorer()

        r_no_agent = scorer.score(campaigns, panel, pairwise, bt)
        a_original = next(r for r in r_no_agent[0] if r.campaign_id == "a")
        original_score = a_original.composite_score / 10

        # score=0.8 weight=2, score=0.2 weight=1 → 加权均值 = (0.8*2 + 0.2*1) / 3 = 1.8/3 = 0.6
        agent_scores = [
            AgentScore(agent_type="heavy", campaign_id="a", score=0.8, weight=2.0),
            AgentScore(agent_type="light", campaign_id="a", score=0.2, weight=1.0),
        ]
        r_with_agent = scorer.score(campaigns, panel, pairwise, bt, agent_scores=agent_scores)
        a_with_agent = next(r for r in r_with_agent[0] if r.campaign_id == "a")
        new_score = a_with_agent.composite_score / 10

        import app.services.campaign_scorer as cs_mod
        asw = cs_mod.AGENT_SCORE_WEIGHT
        expected_contrib = (0.8 * 2 + 0.2 * 1) / (2 + 1)
        expected = original_score * (1 - asw) + expected_contrib * asw
        assert abs(new_score - expected) < 1e-9


class TestCampaignScorerImports:
    """import 和常量测试"""

    def test_import_agent_score_in_campaign_scorer(self):
        """campaign_scorer 中有 AgentScore import"""
        import inspect
        import app.services.campaign_scorer as cs_mod
        source = inspect.getsource(cs_mod)
        assert "from ..models.agent_score import AgentScore" in source

    def test_agent_score_weight_constant_exists(self):
        """AGENT_SCORE_WEIGHT 常量存在"""
        import app.services.campaign_scorer as cs_mod
        assert hasattr(cs_mod, "AGENT_SCORE_WEIGHT")
        assert isinstance(cs_mod.AGENT_SCORE_WEIGHT, float)

    def test_agent_score_weight_default(self):
        """AGENT_SCORE_WEIGHT 默认为 0.1（无 env var 时）"""
        import app.services.campaign_scorer as cs_mod
        # 未设置 env var 时默认 0.1
        # 注意: 如果环境变量已设置，此测试允许跳过
        if "AGENT_SCORE_WEIGHT" not in os.environ:
            assert cs_mod.AGENT_SCORE_WEIGHT == 0.1

    def test_optional_parameter_in_signature(self):
        """score() 方法签名包含 agent_scores 可选参数"""
        import inspect
        sig = inspect.signature(CampaignScorer.score)
        assert "agent_scores" in sig.parameters
        param = sig.parameters["agent_scores"]
        assert param.default is None
