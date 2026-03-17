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
