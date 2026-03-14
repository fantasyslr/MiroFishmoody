"""
BrandState — 品牌认知状态向量

表示某个时间点、某个人群对 Moody 品牌的认知结构。
不是静态标签，而是一组 0-1 连续值，随每次推广行为而变化。

核心维度（Phase A 最小集）：
  science_credibility  — 专业 / 眼健康可信度
  comfort_trust        — 舒适度信任
  aesthetic_affinity   — 好看 / 颜值吸引力
  price_sensitivity    — 价格敏感度（越高=越在意价格）
  social_proof         — 社会证明强度（种草 / 评论正向）
  skepticism           — 质疑 / 负面情绪
  competitor_pressure  — 竞品压力感知
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List


# 标准维度集合
PERCEPTION_DIMENSIONS = [
    "science_credibility",
    "comfort_trust",
    "aesthetic_affinity",
    "price_sensitivity",
    "social_proof",
    "skepticism",
    "competitor_pressure",
]


@dataclass
class PerceptionVector:
    """品牌认知向量 — 每个维度 0.0 ~ 1.0"""
    science_credibility: float = 0.5
    comfort_trust: float = 0.5
    aesthetic_affinity: float = 0.5
    price_sensitivity: float = 0.5
    social_proof: float = 0.5
    skepticism: float = 0.3
    competitor_pressure: float = 0.3

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PerceptionVector":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        kwargs = {k: float(v) for k, v in d.items() if k in known and v is not None}
        return cls(**kwargs)

    def delta(self, other: "PerceptionVector") -> Dict[str, float]:
        """计算两个状态间的差值"""
        d1, d2 = self.to_dict(), other.to_dict()
        return {k: round(d2[k] - d1[k], 4) for k in d1}

    def apply_delta(self, delta: Dict[str, float]) -> "PerceptionVector":
        """应用一个 delta，返回新状态（自动 clamp 到 0-1）"""
        d = self.to_dict()
        for k, v in delta.items():
            if k in d:
                d[k] = max(0.0, min(1.0, d[k] + v))
        return PerceptionVector.from_dict(d)


@dataclass
class BrandState:
    """某个时间点的品牌认知状态快照"""
    state_id: str
    as_of_date: str                              # ISO date
    product_line: str = "moodyplus"
    audience_segment: str = "general"
    market: str = "cn"                           # cn | us | jp | sea | eu | kr
    perception: PerceptionVector = field(default_factory=PerceptionVector)
    confidence: float = 0.5                      # 对这个状态估计的信心 0-1
    evidence_sources: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["perception"] = self.perception.to_dict()
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BrandState":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        extra = {k: v for k, v in d.items() if k not in known}
        kwargs = {k: v for k, v in d.items() if k in known}
        if "perception" in kwargs and isinstance(kwargs["perception"], dict):
            kwargs["perception"] = PerceptionVector.from_dict(kwargs["perception"])
        if extra:
            kwargs.setdefault("extra", {}).update(extra)
        return cls(**kwargs)


@dataclass
class StateTransition:
    """一次干预导致的状态转移记录"""
    transition_id: str
    intervention_id: str
    state_before_id: str
    state_after_id: str
    market: str = "cn"                              # cn | us | jp | sea | eu | kr
    delta: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.5
    method: str = "historical"                   # historical | simulated | manual
    notes: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StateTransition":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        extra = {k: v for k, v in d.items() if k not in known}
        kwargs = {k: v for k, v in d.items() if k in known}
        if extra:
            kwargs.setdefault("extra", {}).update(extra)
        return cls(**kwargs)
