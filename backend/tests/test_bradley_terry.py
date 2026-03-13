"""
Bradley-Terry 排序算法测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.campaign import Campaign, ProductLine
from app.models.evaluation import PairwiseResult
from app.services.pairwise_judge import PairwiseJudge


def make_campaign(id: str) -> Campaign:
    return Campaign(
        id=id, name=id, product_line=ProductLine.COLORED,
        target_audience="t", core_message="t",
        channels=[], creative_direction="t",
    )


def test_clear_winner():
    """A beats everyone, should have highest BT score"""
    campaigns = [make_campaign(x) for x in ["a", "b", "c", "d"]]

    results = [
        PairwiseResult("a", "b", "a", [], {}),
        PairwiseResult("a", "c", "a", [], {}),
        PairwiseResult("a", "d", "a", [], {}),
        PairwiseResult("b", "c", "b", [], {}),
        PairwiseResult("b", "d", "b", [], {}),
        PairwiseResult("c", "d", "c", [], {}),
    ]

    bt = PairwiseJudge._bradley_terry(campaigns, results)

    # a > b > c > d
    assert bt["a"] > bt["b"] > bt["c"] > bt["d"]
    print(f"BT scores: {bt}")
    print("Clear winner test passed!")


def test_all_ties():
    """All ties should produce roughly equal scores"""
    campaigns = [make_campaign(x) for x in ["a", "b", "c"]]

    results = [
        PairwiseResult("a", "b", None, [], {}),
        PairwiseResult("a", "c", None, [], {}),
        PairwiseResult("b", "c", None, [], {}),
    ]

    bt = PairwiseJudge._bradley_terry(campaigns, results)

    # All should be roughly equal
    vals = list(bt.values())
    assert max(vals) - min(vals) < 0.01
    print(f"BT scores: {bt}")
    print("All ties test passed!")


if __name__ == "__main__":
    test_clear_winner()
    test_all_ties()
