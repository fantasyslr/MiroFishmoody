"""
AgentScore — 统一 agent 输出 schema

所有新 agent 类型（MultiJudge、DevilsAdvocate、ConsensusAgent 等）
输出此 dataclass，CampaignScorer 自动纳入聚合，无需手工 wiring。

字段：
  agent_type  — agent 类型标识字符串，如 "image_analyzer"、"devil_advocate"
  campaign_id — 对应 campaign ID
  score       — 归一化到 0-1 的贡献分，由 agent 负责归一化
  weight      — 聚合权重，默认 1.0，CampaignScorer 可按 agent_type 覆盖
  metadata    — 扩展字段，存 agent 特有信息（suspect、dissent、visual_score 等）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class AgentScore:
    """单个 agent 对单个 campaign 的评分贡献"""
    agent_type: str
    campaign_id: str
    score: float              # 归一化到 0-1
    weight: float = 1.0       # 聚合时的权重
    metadata: Dict[str, Any] = field(default_factory=dict)
