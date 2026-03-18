"""
Task 2 TDD — brief_weights.py (19-01)
RED: these tests must fail before implementation
"""
import pytest
from app.services.brief_weights import (
    BRIEF_DIMENSION_WEIGHTS,
    WEIGHT_PROFILE_VERSIONS,
    BRIEF_TYPE_VALUES,
)

EXPECTED_BRIEF_TYPES = {"brand", "seeding", "conversion"}

# DIMENSION_KEYS from scoreboard.py + emotional_resonance (new reserved dim)
EXPECTED_DIMS = {
    "thumb_stop",
    "clarity",
    "trust",
    "conversion_readiness",
    "claim_risk",
    "emotional_resonance",
}


@pytest.mark.parametrize("brief_type", list(EXPECTED_BRIEF_TYPES))
def test_weights_exist_for_all_brief_types(brief_type):
    assert brief_type in BRIEF_DIMENSION_WEIGHTS


@pytest.mark.parametrize("brief_type", list(EXPECTED_BRIEF_TYPES))
def test_weights_sum_to_one(brief_type):
    total = sum(BRIEF_DIMENSION_WEIGHTS[brief_type].values())
    assert abs(total - 1.0) < 1e-9, f"{brief_type} weights sum={total}"


@pytest.mark.parametrize("brief_type", list(EXPECTED_BRIEF_TYPES))
def test_dimension_keys_match(brief_type):
    keys = set(BRIEF_DIMENSION_WEIGHTS[brief_type].keys())
    assert keys == EXPECTED_DIMS, f"{brief_type} dims mismatch: {keys}"


def test_weight_profile_versions():
    assert WEIGHT_PROFILE_VERSIONS["brand"] == "brand-v1"
    assert WEIGHT_PROFILE_VERSIONS["seeding"] == "seeding-v1"
    assert WEIGHT_PROFILE_VERSIONS["conversion"] == "conversion-v1"


def test_brief_type_values_frozenset():
    assert isinstance(BRIEF_TYPE_VALUES, frozenset)
    assert BRIEF_TYPE_VALUES == EXPECTED_BRIEF_TYPES


def test_brief_type_values_covers_all():
    assert "brand" in BRIEF_TYPE_VALUES
    assert "seeding" in BRIEF_TYPE_VALUES
    assert "conversion" in BRIEF_TYPE_VALUES
