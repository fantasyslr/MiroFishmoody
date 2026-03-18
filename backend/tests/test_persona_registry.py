"""
PersonaRegistry unit tests — schema validation, loading, lookup.
"""

import json
import os

import pytest

from app.services.persona_registry import PersonaRegistry


EXPECTED_IDS = ["daily_wearer", "acuvue_switcher", "beauty_first", "price_conscious", "eye_health"]


class TestLoadDefaultPresets:
    def test_load_default_presets(self):
        registry = PersonaRegistry()
        personas = registry.get_personas()
        assert len(personas) == 5
        ids = [p["id"] for p in personas]
        assert sorted(ids) == sorted(EXPECTED_IDS)

    def test_returns_copy(self):
        registry = PersonaRegistry()
        a = registry.get_personas()
        b = registry.get_personas()
        assert a is not b


class TestPersonaSchemaValid:
    def test_persona_schema_valid(self):
        registry = PersonaRegistry()
        for persona in registry.get_personas():
            for field in ["id", "name", "description", "evaluation_focus"]:
                assert field in persona, f"Missing field: {field}"
                assert isinstance(persona[field], str), f"{field} should be str"
                assert persona[field].strip(), f"{field} should not be empty"


class TestSchemaRejectInvalid:
    def _write_preset(self, tmp_path, personas):
        path = tmp_path / "test_preset.json"
        path.write_text(json.dumps(personas), encoding="utf-8")
        return str(path)

    def _valid_persona(self, **overrides):
        base = {
            "id": "test_id",
            "name": "Test Name",
            "description": "Test description",
            "evaluation_focus": "Test focus",
        }
        base.update(overrides)
        return base

    def test_schema_reject_missing_id(self, tmp_path):
        persona = self._valid_persona()
        del persona["id"]
        path = self._write_preset(tmp_path, [persona])
        with pytest.raises(ValueError, match="id"):
            PersonaRegistry(preset_path=path)

    def test_schema_reject_missing_name(self, tmp_path):
        persona = self._valid_persona()
        del persona["name"]
        path = self._write_preset(tmp_path, [persona])
        with pytest.raises(ValueError, match="name"):
            PersonaRegistry(preset_path=path)

    def test_schema_reject_missing_description(self, tmp_path):
        persona = self._valid_persona()
        del persona["description"]
        path = self._write_preset(tmp_path, [persona])
        with pytest.raises(ValueError, match="description"):
            PersonaRegistry(preset_path=path)

    def test_schema_reject_missing_evaluation_focus(self, tmp_path):
        persona = self._valid_persona()
        del persona["evaluation_focus"]
        path = self._write_preset(tmp_path, [persona])
        with pytest.raises(ValueError, match="evaluation_focus"):
            PersonaRegistry(preset_path=path)

    def test_schema_reject_empty_string(self, tmp_path):
        persona = self._valid_persona(name="")
        path = self._write_preset(tmp_path, [persona])
        with pytest.raises(ValueError):
            PersonaRegistry(preset_path=path)


class TestGetPersonaById:
    def test_get_persona_by_id(self):
        registry = PersonaRegistry()
        persona = registry.get_persona("daily_wearer")
        assert persona["id"] == "daily_wearer"
        assert "日抛" in persona["name"]

    def test_get_persona_by_id_not_found(self):
        registry = PersonaRegistry()
        with pytest.raises(KeyError):
            registry.get_persona("nonexistent")


class TestPresetFileNotFound:
    def test_preset_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            PersonaRegistry(preset_path="/tmp/nonexistent_preset_12345.json")


# --- Phase 03: Category-aware persona loading ---

CONFIG_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "app", "config", "personas")
)


class TestCategoryLoading:
    """PersonaRegistry loads correct personas based on category parameter."""

    def test_get_personas_no_category_returns_default(self):
        """get_personas() without category returns default.json personas (backward compat)."""
        registry = PersonaRegistry()
        personas = registry.get_personas()
        assert len(personas) == 5
        ids = {p["id"] for p in personas}
        assert "daily_wearer" in ids
        assert "beauty_first" in ids

    def test_get_personas_moodyplus(self):
        """get_personas(category='moodyplus') returns moodyplus.json personas (expanded to 9)."""
        registry = PersonaRegistry()
        personas = registry.get_personas(category="moodyplus")
        assert len(personas) == 9
        ids = {p["id"] for p in personas}
        assert "daily_wearer" in ids
        assert "acuvue_switcher" in ids
        assert "eye_health" in ids
        assert "office_comfort" in ids
        assert "active_lifestyle" in ids
        assert "sensitive_eyes" in ids
        # Phase 16-01 additions
        assert "tech_perceiver" in ids
        assert "medical_compliance" in ids
        assert "daily_comfort_user" in ids

    def test_get_personas_colored_lenses(self):
        """get_personas(category='colored_lenses') returns colored_lenses.json personas (expanded to 8)."""
        registry = PersonaRegistry()
        personas = registry.get_personas(category="colored_lenses")
        assert len(personas) == 8
        ids = {p["id"] for p in personas}
        assert "beauty_first" in ids
        assert "price_conscious" in ids
        assert "makeup_influencer" in ids
        assert "cosplay_occasion" in ids
        assert "natural_enhancer" in ids
        # Phase 16-01 additions
        assert "beauty_blogger" in ids
        assert "visual_creator" in ids
        assert "subculture_fan" in ids

    def test_get_personas_invalid_category_raises(self):
        """get_personas(category='nonexistent') raises ValueError."""
        registry = PersonaRegistry()
        with pytest.raises(ValueError, match="Unknown category"):
            registry.get_personas(category="nonexistent")


class TestMoodyplusPreset:
    """moodyplus.json contains correct personas with valid schema."""

    def test_moodyplus_file_exists(self):
        path = os.path.join(CONFIG_DIR, "moodyplus.json")
        assert os.path.exists(path), f"moodyplus.json not found at {path}"

    def test_moodyplus_has_nine_personas(self):
        path = os.path.join(CONFIG_DIR, "moodyplus.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 9

    def test_moodyplus_contains_expected_ids(self):
        path = os.path.join(CONFIG_DIR, "moodyplus.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ids = {p["id"] for p in data}
        expected = {
            "daily_wearer", "acuvue_switcher", "eye_health",
            "office_comfort", "active_lifestyle", "sensitive_eyes",
            "tech_perceiver", "medical_compliance", "daily_comfort_user",
        }
        assert ids == expected

    def test_moodyplus_schema_validation(self):
        path = os.path.join(CONFIG_DIR, "moodyplus.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        required = ["id", "name", "description", "evaluation_focus"]
        for persona in data:
            for field in required:
                assert field in persona, f"Missing '{field}' in persona {persona.get('id', '?')}"
                assert isinstance(persona[field], str) and persona[field].strip(), \
                    f"Field '{field}' must be non-empty string in {persona.get('id', '?')}"


class TestColoredLensesPreset:
    """colored_lenses.json contains correct personas with valid schema."""

    def test_colored_lenses_file_exists(self):
        path = os.path.join(CONFIG_DIR, "colored_lenses.json")
        assert os.path.exists(path), f"colored_lenses.json not found at {path}"

    def test_colored_lenses_has_eight_personas(self):
        path = os.path.join(CONFIG_DIR, "colored_lenses.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 8

    def test_colored_lenses_contains_expected_ids(self):
        path = os.path.join(CONFIG_DIR, "colored_lenses.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ids = {p["id"] for p in data}
        expected = {
            "beauty_first", "price_conscious",
            "makeup_influencer", "cosplay_occasion", "natural_enhancer",
            "beauty_blogger", "visual_creator", "subculture_fan",
        }
        assert ids == expected

    def test_colored_lenses_schema_validation(self):
        path = os.path.join(CONFIG_DIR, "colored_lenses.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        required = ["id", "name", "description", "evaluation_focus"]
        for persona in data:
            for field in required:
                assert field in persona, f"Missing '{field}' in persona {persona.get('id', '?')}"
                assert isinstance(persona[field], str) and persona[field].strip(), \
                    f"Field '{field}' must be non-empty string in {persona.get('id', '?')}"


# ---------------------------------------------------------------------------
# Phase 16-01: Expanded persona pools (moodyplus 6→9, colored_lenses 5→8)
# ---------------------------------------------------------------------------

class TestMoodyPlusExpandedPool:
    """moodyplus.json must contain 9 personas after expansion."""

    def test_count_is_9(self):
        registry = PersonaRegistry()
        personas = registry.get_personas(category="moodyplus")
        assert len(personas) == 9, f"Expected 9 moodyplus personas, got {len(personas)}"

    def test_new_ids_present(self):
        registry = PersonaRegistry()
        personas = registry.get_personas(category="moodyplus")
        ids = {p["id"] for p in personas}
        new_ids = {"tech_perceiver", "medical_compliance", "daily_comfort_user"}
        assert new_ids.issubset(ids), f"Missing new moodyplus IDs: {new_ids - ids}"

    def test_existing_ids_still_present(self):
        registry = PersonaRegistry()
        personas = registry.get_personas(category="moodyplus")
        ids = {p["id"] for p in personas}
        original_ids = {
            "daily_wearer", "acuvue_switcher", "eye_health",
            "office_comfort", "active_lifestyle", "sensitive_eyes",
        }
        assert original_ids.issubset(ids), f"Lost original moodyplus IDs: {original_ids - ids}"

    def test_all_new_personas_valid_schema(self):
        path = os.path.join(CONFIG_DIR, "moodyplus.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        new_ids = {"tech_perceiver", "medical_compliance", "daily_comfort_user"}
        new_personas = [p for p in data if p["id"] in new_ids]
        assert len(new_personas) == 3, f"Expected 3 new moodyplus personas, found {len(new_personas)}"
        required = ["id", "name", "description", "evaluation_focus"]
        for p in new_personas:
            for field in required:
                assert field in p and isinstance(p[field], str) and p[field].strip(), \
                    f"New moodyplus persona {p.get('id')} field '{field}' invalid"


class TestColoredLensesExpandedPool:
    """colored_lenses.json must contain 8 personas after expansion."""

    def test_count_is_8(self):
        registry = PersonaRegistry()
        personas = registry.get_personas(category="colored_lenses")
        assert len(personas) == 8, f"Expected 8 colored_lenses personas, got {len(personas)}"

    def test_new_ids_present(self):
        registry = PersonaRegistry()
        personas = registry.get_personas(category="colored_lenses")
        ids = {p["id"] for p in personas}
        new_ids = {"beauty_blogger", "visual_creator", "subculture_fan"}
        assert new_ids.issubset(ids), f"Missing new colored_lenses IDs: {new_ids - ids}"

    def test_existing_ids_still_present(self):
        registry = PersonaRegistry()
        personas = registry.get_personas(category="colored_lenses")
        ids = {p["id"] for p in personas}
        original_ids = {
            "beauty_first", "price_conscious", "makeup_influencer",
            "cosplay_occasion", "natural_enhancer",
        }
        assert original_ids.issubset(ids), f"Lost original colored_lenses IDs: {original_ids - ids}"

    def test_all_new_personas_valid_schema(self):
        path = os.path.join(CONFIG_DIR, "colored_lenses.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        new_ids = {"beauty_blogger", "visual_creator", "subculture_fan"}
        new_personas = [p for p in data if p["id"] in new_ids]
        assert len(new_personas) == 3, f"Expected 3 new colored_lenses personas, found {len(new_personas)}"
        required = ["id", "name", "description", "evaluation_focus"]
        for p in new_personas:
            for field in required:
                assert field in p and isinstance(p[field], str) and p[field].strip(), \
                    f"New colored_lenses persona {p.get('id')} field '{field}' invalid"
