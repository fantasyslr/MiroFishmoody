"""Phase 13 BUG-05: _parse_evaluate_campaigns() 单元测试"""
import pytest
from app.api.campaign import _parse_evaluate_campaigns


def _make_data(campaigns, set_id="test-set-001"):
    return {"set_id": set_id, "campaigns": campaigns}


def test_parse_evaluate_campaigns_basic():
    data = _make_data([
        {"campaign_id": "uuid-aaa", "name": "方案A", "description": "核心卖点A"},
        {"campaign_id": "uuid-bbb", "name": "方案B", "description": "核心卖点B"},
    ])
    result = _parse_evaluate_campaigns(data)
    assert len(result.campaigns) == 2
    assert result.campaigns[0].id == "uuid-aaa"
    assert result.campaigns[0].core_message == "核心卖点A"
    assert result.campaigns[0].name == "方案A"


def test_parse_evaluate_campaigns_image_paths():
    paths = ["/api/campaign/image-file/set1/uuid-aaa__x__img.jpg"]
    data = _make_data([
        {"campaign_id": "uuid-aaa", "name": "方案A", "description": "测试", "image_paths": paths},
        {"campaign_id": "uuid-bbb", "name": "方案B", "description": "测试2", "image_paths": []},
    ])
    result = _parse_evaluate_campaigns(data)
    assert result.campaigns[0].image_paths == paths


def test_parse_evaluate_campaigns_id_mapping():
    """campaign_id 优先于 id 字段"""
    data = _make_data([
        {"campaign_id": "real-uuid", "id": "wrong-id", "name": "方案A", "description": "描述A"},
        {"campaign_id": "real-uuid-2", "name": "方案B", "description": "描述B"},
    ])
    result = _parse_evaluate_campaigns(data)
    assert result.campaigns[0].id == "real-uuid"


def test_parse_evaluate_campaigns_description_fallback():
    """description 缺失时 core_message 回退为 name，不抛异常"""
    data = _make_data([
        {"campaign_id": "uuid-aaa", "name": "方案A"},
        {"campaign_id": "uuid-bbb", "name": "方案B"},
    ])
    result = _parse_evaluate_campaigns(data)
    assert result.campaigns[0].core_message == "方案A"


def test_parse_evaluate_campaigns_min_campaigns():
    data = _make_data([{"campaign_id": "uuid-aaa", "name": "方案A", "description": "desc"}])
    with pytest.raises(ValueError, match="至少需要 2 个"):
        _parse_evaluate_campaigns(data)
