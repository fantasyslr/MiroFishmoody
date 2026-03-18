"""
Task 1 TDD — BriefType enum (19-01)
RED: these tests must fail before implementation
"""
import pytest
from app.models.campaign import BriefType


def test_brand_value():
    assert BriefType("brand") == BriefType.BRAND


def test_seeding_value():
    assert BriefType("seeding") == BriefType.SEEDING


def test_conversion_value():
    assert BriefType("conversion") == BriefType.CONVERSION


def test_unknown_raises():
    with pytest.raises(ValueError):
        BriefType("unknown")


def test_is_str_enum():
    assert isinstance(BriefType.BRAND, str)
    assert BriefType.BRAND.value == "brand"
    assert BriefType.SEEDING.value == "seeding"
    assert BriefType.CONVERSION.value == "conversion"


def test_product_line_still_exists():
    """ProductLine 未被删除"""
    from app.models.campaign import ProductLine
    assert ProductLine.COLORED.value == "colored_lenses"
