"""
Campaign 数据模型
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field


class ProductLine(str, Enum):
    """产品线"""
    COLORED = "colored_lenses"
    MOODYPLUS = "moodyplus"


@dataclass
class Campaign:
    """单个 campaign 方案"""
    id: str
    name: str
    product_line: ProductLine
    target_audience: str
    core_message: str
    channels: List[str]
    creative_direction: str
    budget_range: Optional[str] = None
    kv_description: Optional[str] = None
    promo_mechanic: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "product_line": self.product_line.value,
            "target_audience": self.target_audience,
            "core_message": self.core_message,
            "channels": self.channels,
            "creative_direction": self.creative_direction,
            "budget_range": self.budget_range,
            "kv_description": self.kv_description,
            "promo_mechanic": self.promo_mechanic,
            "extra": self.extra,
        }


@dataclass
class CampaignSet:
    """一组待评审的 campaign 方案"""
    set_id: str
    campaigns: List[Campaign]
    context: str = ""
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "set_id": self.set_id,
            "campaigns": [c.to_dict() for c in self.campaigns],
            "context": self.context,
            "created_at": self.created_at,
        }
