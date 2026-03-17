"""
PersonaRegistry — Config-driven persona loading with schema validation.

Loads personas from JSON preset files. Supports category-based loading:
- get_personas() → default.json (backward compatible)
- get_personas(category="moodyplus") → moodyplus.json
- get_personas(category="colored_lenses") → colored_lenses.json
"""

import json
import os
from typing import Dict, List, Any, Optional


class PersonaRegistry:
    """Registry that loads and validates persona definitions from JSON presets."""

    REQUIRED_FIELDS = ["id", "name", "description", "evaluation_focus"]

    CATEGORY_FILES = {
        "moodyplus": "moodyplus.json",
        "colored_lenses": "colored_lenses.json",
    }

    def __init__(self, preset_path: str = None, config_dir: str = None):
        if config_dir is not None:
            self._config_dir = os.path.normpath(config_dir)
        else:
            self._config_dir = os.path.normpath(
                os.path.join(os.path.dirname(__file__), "..", "config", "personas")
            )

        # Backward compatibility: if preset_path is explicitly given, use it as default
        if preset_path is not None:
            self._preset_path = os.path.normpath(preset_path)
        else:
            self._preset_path = os.path.join(self._config_dir, "default.json")

        self._personas: List[Dict[str, Any]] = []
        self._load_default()

    def _load_default(self) -> None:
        """Load and validate personas from the default preset file."""
        self._personas = self._load_file(self._preset_path)

    def _load_file(self, path: str) -> List[Dict[str, Any]]:
        """Load and validate personas from a JSON file."""
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"Persona preset file not found: {path}"
            )
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for persona in data:
            self._validate_persona(persona)
        return data

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

    def get_personas(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return personas, optionally filtered by category.

        Args:
            category: If None, returns default personas. If 'moodyplus' or
                      'colored_lenses', loads from the corresponding preset file.

        Returns:
            A list of persona dicts (copy).

        Raises:
            ValueError: If category is not recognized.
        """
        if category is None:
            return list(self._personas)

        if category not in self.CATEGORY_FILES:
            valid = ", ".join(sorted(self.CATEGORY_FILES.keys()))
            raise ValueError(
                f"Unknown category: {category}. Valid: {valid}"
            )

        file_path = os.path.join(self._config_dir, self.CATEGORY_FILES[category])
        return self._load_file(file_path)

    def get_persona(self, persona_id: str) -> Dict[str, Any]:
        """Return a single persona by id from the default set. Raises KeyError if not found."""
        for persona in self._personas:
            if persona["id"] == persona_id:
                return persona
        raise KeyError(f"Persona not found: {persona_id}")
