"""
PersonaRegistry — Config-driven persona loading with schema validation.

Loads personas from JSON preset files. Default preset contains 5 Moody Lenses
consumer personas previously hardcoded in audience_panel.py.
"""

import json
import os
from typing import Dict, List, Any


class PersonaRegistry:
    """Registry that loads and validates persona definitions from JSON presets."""

    REQUIRED_FIELDS = ["id", "name", "description", "evaluation_focus"]

    def __init__(self, preset_path: str = None):
        if preset_path is None:
            preset_path = os.path.join(
                os.path.dirname(__file__), "..", "config", "personas", "default.json"
            )
        self._preset_path = os.path.normpath(preset_path)
        self._personas: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        """Load and validate personas from JSON preset file."""
        if not os.path.exists(self._preset_path):
            raise FileNotFoundError(
                f"Persona preset file not found: {self._preset_path}"
            )
        with open(self._preset_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for persona in data:
            self._validate_persona(persona)
        self._personas = data

    def _validate_persona(self, persona: dict) -> None:
        """Validate that a persona dict has all required non-empty string fields."""
        for field in self.REQUIRED_FIELDS:
            if field not in persona:
                raise ValueError(
                    f"Persona missing required field: {field}"
                )
            value = persona[field]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Persona field '{field}' must be a non-empty string, got: {value!r}"
                )

    def get_personas(self) -> List[Dict[str, Any]]:
        """Return a copy of all loaded personas."""
        return list(self._personas)

    def get_persona(self, persona_id: str) -> Dict[str, Any]:
        """Return a single persona by id. Raises KeyError if not found."""
        for persona in self._personas:
            if persona["id"] == persona_id:
                return persona
        raise KeyError(f"Persona not found: {persona_id}")
