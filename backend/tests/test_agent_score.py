"""
AgentScore dataclass 测试 — Phase 15-02

Task 1 RED: 验证 AgentScore dataclass 字段、默认值和行为
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


class TestAgentScoreDataclass:
    """AgentScore 基础字段和默认值测试"""

    def test_import(self):
        """AgentScore 可正常 import"""
        from app.models.agent_score import AgentScore
        assert AgentScore is not None

    def test_required_fields(self):
        """创建 AgentScore 时必须提供 agent_type, campaign_id, score"""
        from app.models.agent_score import AgentScore
        s = AgentScore(agent_type="test_agent", campaign_id="c1", score=0.75)
        assert s.agent_type == "test_agent"
        assert s.campaign_id == "c1"
        assert s.score == 0.75

    def test_default_weight(self):
        """weight 默认值为 1.0"""
        from app.models.agent_score import AgentScore
        s = AgentScore(agent_type="test", campaign_id="c1", score=0.5)
        assert s.weight == 1.0

    def test_default_metadata_empty_dict(self):
        """metadata 默认值为空 dict，且各实例独立"""
        from app.models.agent_score import AgentScore
        s1 = AgentScore(agent_type="a", campaign_id="c1", score=0.3)
        s2 = AgentScore(agent_type="b", campaign_id="c2", score=0.7)
        assert s1.metadata == {}
        assert s2.metadata == {}
        # 各实例独立，不共享 metadata
        s1.metadata["key"] = "value"
        assert s2.metadata == {}

    def test_custom_weight(self):
        """weight 可自定义"""
        from app.models.agent_score import AgentScore
        s = AgentScore(agent_type="devil_advocate", campaign_id="c1", score=0.4, weight=2.0)
        assert s.weight == 2.0

    def test_custom_metadata(self):
        """metadata 可存储任意 key-value"""
        from app.models.agent_score import AgentScore
        s = AgentScore(
            agent_type="image_analyzer",
            campaign_id="c1",
            score=0.9,
            metadata={"visual_score": 0.85, "suspect": False}
        )
        assert s.metadata["visual_score"] == 0.85
        assert s.metadata["suspect"] is False

    def test_is_dataclass(self):
        """AgentScore 是 dataclass"""
        import dataclasses
        from app.models.agent_score import AgentScore
        assert dataclasses.is_dataclass(AgentScore)

    def test_five_fields(self):
        """AgentScore 有且仅有 5 个字段"""
        from app.models.agent_score import AgentScore
        fields = AgentScore.__dataclass_fields__
        expected = {"agent_type", "campaign_id", "score", "weight", "metadata"}
        assert set(fields.keys()) == expected

    def test_score_zero_to_one_range(self):
        """score 可以是 0-1 范围内的任意值"""
        from app.models.agent_score import AgentScore
        s_min = AgentScore(agent_type="t", campaign_id="c", score=0.0)
        s_max = AgentScore(agent_type="t", campaign_id="c", score=1.0)
        assert s_min.score == 0.0
        assert s_max.score == 1.0
