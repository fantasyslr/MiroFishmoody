"""
Brandiction 数据模型

历史 Intervention、Outcome、Signal、竞品事件、证据。
所有字段允许稀疏 — 用户不需要一次给全量完美数据。
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any


@dataclass
class HistoricalIntervention:
    """一次历史营销干预（campaign / 投放 / 活动）"""
    intervention_id: str
    run_id: str                          # 批次 ID，允许把多个 intervention 归为同一轮
    product_line: str = "moodyplus"      # moodyplus | colored_lenses
    date_start: Optional[str] = None     # ISO date
    date_end: Optional[str] = None
    theme: Optional[str] = None          # 主打认知路径，如 science_credibility / comfort_beauty
    message_arc: Optional[str] = None    # 核心信息弧
    channel_mix: Optional[List[str]] = None
    budget: Optional[float] = None
    spend: Optional[float] = None
    audience_segment: Optional[str] = None
    market: str = "cn"                   # cn | us | jp | sea | eu | kr
    # --- V3 DTC data spine ---
    campaign_id: Optional[str] = None    # 投放计划 ID（Meta/Google campaign）
    creative_id: Optional[str] = None    # 素材 ID
    landing_page: Optional[str] = None   # 落地页 URL / 路径
    platform: Optional[str] = None       # 投放平台（douyin / redbook / meta / google）
    channel_family: Optional[str] = None # 渠道大类（paid_social / paid_search / kol_seed …）
    objective: Optional[str] = None      # 投放目标（awareness / traffic / conversion）
    season_tag: Optional[str] = None     # 时间标签（618 / double11 / cny / regular）
    notes: Optional[str] = None          # 人工备注
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "HistoricalIntervention":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        extra = {k: v for k, v in d.items() if k not in known}
        kwargs = {k: v for k, v in d.items() if k in known}
        if extra:
            kwargs.setdefault("extra", {}).update(extra)
        return cls(**kwargs)


@dataclass
class HistoricalOutcomeWindow:
    """一次 intervention 对应的真实结果窗口"""
    outcome_id: str
    intervention_id: str
    window_label: Optional[str] = None   # 例如 "week1-6", "month1"
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    impressions: Optional[int] = None
    clicks: Optional[int] = None
    ctr: Optional[float] = None
    cvr: Optional[float] = None
    revenue: Optional[float] = None
    roas: Optional[float] = None
    brand_lift: Optional[float] = None   # 品牌认知 lift
    search_trend_delta: Optional[float] = None
    comment_sentiment: Optional[float] = None  # -1..1
    comment_summary: Optional[str] = None
    # --- V3 DTC funnel metrics ---
    sessions: Optional[int] = None
    pdp_views: Optional[int] = None      # 商品详情页浏览
    add_to_cart: Optional[int] = None
    checkout_started: Optional[int] = None
    purchases: Optional[int] = None
    new_customers: Optional[int] = None
    returning_customers: Optional[int] = None
    aov: Optional[float] = None          # 客单价
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "HistoricalOutcomeWindow":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        extra = {k: v for k, v in d.items() if k not in known}
        kwargs = {k: v for k, v in d.items() if k in known}
        if extra:
            kwargs.setdefault("extra", {}).update(extra)
        return cls(**kwargs)


@dataclass
class BrandSignalSnapshot:
    """某个时间点的品牌信号快照（评论语料、搜索词、人工标注等）"""
    signal_id: str
    date: str                            # ISO date
    product_line: str = "moodyplus"
    audience_segment: str = "general"    # general | young_female | ...
    market: str = "cn"                   # cn | us | jp | sea | eu | kr
    signal_type: str = ""                # search_trend | review_corpus | manual_label | llm_extract
    dimension: Optional[str] = None      # science_credibility | comfort_trust | ...
    value: Optional[float] = None        # 归一化值 0..1
    raw_text: Optional[str] = None       # 原始语料 / 搜索词
    source: Optional[str] = None         # 数据来源描述
    # --- V3 信号溯源 ---
    source_type: Optional[str] = None    # dtc_site | meta_ads | google_ads | influencer | manual
    source_id: Optional[str] = None      # 关联的外部 ID（如 campaign_id, order_id）
    raw_text_ref: Optional[str] = None   # 大文本外部引用路径（避免 DB 膨胀）
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BrandSignalSnapshot":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        extra = {k: v for k, v in d.items() if k not in known}
        kwargs = {k: v for k, v in d.items() if k in known}
        if extra:
            kwargs.setdefault("extra", {}).update(extra)
        return cls(**kwargs)


@dataclass
class CompetitorEvent:
    """竞品事件记录"""
    event_id: str
    date: str
    competitor: str                      # 例如 acuvue, bausch, ...
    market: str = "cn"                   # cn | us | jp | sea | eu | kr
    event_type: Optional[str] = None     # price_cut | new_launch | campaign | ...
    description: Optional[str] = None
    impact_estimate: Optional[str] = None  # high / medium / low
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CompetitorEvent":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        extra = {k: v for k, v in d.items() if k not in known}
        kwargs = {k: v for k, v in d.items() if k in known}
        if extra:
            kwargs.setdefault("extra", {}).update(extra)
        return cls(**kwargs)


@dataclass
class EvidenceArtifact:
    """附件证据（截图、评论导出、搜索报告等）"""
    artifact_id: str
    intervention_id: Optional[str] = None
    signal_id: Optional[str] = None
    artifact_type: str = ""              # screenshot | csv | report | comment_export
    file_path: Optional[str] = None
    description: Optional[str] = None
    uploaded_at: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EvidenceArtifact":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        extra = {k: v for k, v in d.items() if k not in known}
        kwargs = {k: v for k, v in d.items() if k in known}
        if extra:
            kwargs.setdefault("extra", {}).update(extra)
        return cls(**kwargs)
