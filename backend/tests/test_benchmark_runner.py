"""
Benchmark Runner 单元测试

验证：
1. MockLLMClient 不调用真实 API
2. calculate_accuracy 命中率计算逻辑
3. fixture 文件加载格式正确
"""

import os
import glob
import json
import sys

import pytest

# 确保 backend 目录在 path 中（conftest.py 设置了 env vars）
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


# ------------------------------------------------------------------ #
#  Test 1: MockLLMClient 不调用真实 API
# ------------------------------------------------------------------ #

def test_mock_llm_does_not_call_real_api():
    """MockLLMClient 在无 LLM_API_KEY 环境变量下可实例化，不调用网络。"""
    env_backup = os.environ.pop("LLM_API_KEY", None)
    try:
        from benchmark.mock_llm_client import MockLLMClient
        m = MockLLMClient()
        result = m.chat_json([{"role": "user", "content": "test"}])
        assert isinstance(result, dict)
    finally:
        if env_backup is not None:
            os.environ["LLM_API_KEY"] = env_backup


def test_mock_llm_panel_response():
    """MockLLMClient 对 audience panel prompt 返回含 score + dimension_scores 的 dict。"""
    from benchmark.mock_llm_client import MockLLMClient
    m = MockLLMClient()
    result = m.chat_json([{
        "role": "user",
        "content": (
            "请评审营销方案，输出 score, strengths, objections, reasoning, "
            "dimension_scores (thumb_stop, clarity, trust, conversion_readiness, claim_risk)"
        ),
    }])
    assert "score" in result, f"Missing 'score' in: {result}"
    assert "dimension_scores" in result, f"Missing 'dimension_scores' in: {result}"
    assert "thumb_stop" in result["dimension_scores"], f"Missing thumb_stop: {result}"


def test_mock_llm_pairwise_response():
    """MockLLMClient 对 pairwise prompt 返回含 winner='A' 的 dict。"""
    from benchmark.mock_llm_client import MockLLMClient
    m = MockLLMClient()
    result = m.chat_json([{
        "role": "user",
        "content": (
            "请比较以下两个方案，判断哪个更优。\n"
            "维度：reach_potential, conversion_potential, brand_alignment, "
            "risk_level, feasibility\n"
            "输出 winner, dimensions, reasoning"
        ),
    }])
    assert "winner" in result, f"Missing 'winner' in: {result}"
    assert result["winner"] in ("A", "B", "tie"), (
        f"winner must be A/B/tie, got: {result['winner']}"
    )


def test_mock_llm_summary_response():
    """MockLLMClient 对 summary prompt 返回含 summary + assumptions + confidence_notes 的 dict。"""
    from benchmark.mock_llm_client import MockLLMClient
    m = MockLLMClient()
    result = m.chat_json([{
        "role": "user",
        "content": (
            "你是营销策略顾问。请生成评审总结报告。\n"
            "输出 JSON: summary, assumptions, confidence_notes"
        ),
    }])
    assert "summary" in result, f"Missing 'summary' in: {result}"
    assert "assumptions" in result, f"Missing 'assumptions' in: {result}"
    assert "confidence_notes" in result, f"Missing 'confidence_notes' in: {result}"
    assert len(result["summary"]) >= 20, (
        f"summary too short ({len(result['summary'])} chars): {result['summary']}"
    )


# ------------------------------------------------------------------ #
#  Test 2: calculate_accuracy 命中率计算逻辑
# ------------------------------------------------------------------ #

def test_hit_rate_calculation():
    """calculate_accuracy 正确计算各 brief_type 命中率。"""
    from benchmark.run import calculate_accuracy

    hits = {"brand": 3, "seeding": 2, "conversion": 3}
    totals = {"brand": 4, "seeding": 4, "conversion": 3}
    result = calculate_accuracy(hits, totals)

    assert result["brand"] == pytest.approx(0.75, abs=0.01)
    assert result["seeding"] == pytest.approx(0.50, abs=0.01)
    assert result["conversion"] == pytest.approx(1.00, abs=0.01)


def test_hit_rate_zero_total():
    """calculate_accuracy 对 total=0 的 brief_type 返回 0.0 而不是 ZeroDivisionError。"""
    from benchmark.run import calculate_accuracy

    hits = {}
    totals = {"brand": 0}
    result = calculate_accuracy(hits, totals)
    assert result["brand"] == 0.0


def test_hit_rate_all_miss():
    """calculate_accuracy 对 0 命中返回 0.0。"""
    from benchmark.run import calculate_accuracy

    hits = {}
    totals = {"brand": 4, "seeding": 4}
    result = calculate_accuracy(hits, totals)
    assert result["brand"] == pytest.approx(0.0, abs=0.01)
    assert result["seeding"] == pytest.approx(0.0, abs=0.01)


# ------------------------------------------------------------------ #
#  Test 3: fixture 文件格式正确
# ------------------------------------------------------------------ #

def test_fixture_loading():
    """所有 benchmark fixture 文件包含必需字段且 brief_type 合法。"""
    fixture_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "tests", "fixtures", "benchmark", "*.json",
    )
    files = glob.glob(fixture_dir)
    assert len(files) >= 10, f"Expected >=10 fixtures, got {len(files)}"

    for f in files:
        data = json.load(open(f, encoding="utf-8"))
        assert "brief_type" in data, f"Missing brief_type in {f}"
        assert data["brief_type"] in ("brand", "seeding", "conversion"), (
            f"Invalid brief_type '{data['brief_type']}' in {f}"
        )
        assert "expected_winner_id" in data, f"Missing expected_winner_id in {f}"
        assert "campaigns" in data and len(data["campaigns"]) >= 2, (
            f"Expected >=2 campaigns in {f}"
        )
        campaign_ids = {c["id"] for c in data["campaigns"]}
        assert data["expected_winner_id"] in campaign_ids, (
            f"expected_winner_id '{data['expected_winner_id']}' not in campaigns: {campaign_ids}"
        )


def test_fixture_count():
    """确认有 11 个 fixture 文件（brand×4, seeding×4, conversion×3）。"""
    fixture_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "tests", "fixtures", "benchmark", "*.json",
    )
    files = glob.glob(fixture_dir)
    assert len(files) == 11, f"Expected 11 fixtures, got {len(files)}: {files}"
