#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Dict, List

from ..base_validator import BaseValidator
from ..common_validator_utils import (
    build_validation_ok,
    build_validation_fail,
)


class BandoriValidator(BaseValidator):
    game_id = "bandori"

    _ALLOWED_DIFFICULTIES = {
        "EASY",
        "NORMAL",
        "HARD",
        "EXPERT",
        "SPECIAL",
    }

    def validate(self, payload: Dict[str, Any]) -> dict:
        errors: List[str] = []
        warnings: List[str] = []

        if not isinstance(payload, dict):
            return build_validation_fail(
                errors=["payload must be a dict"],
                warnings=[],
                degraded_mode=False,
            )

        required_fields = ["game", "chart_id", "title", "difficulty"]

        for field_name in required_fields:
            value = payload.get(field_name)
            if value is None:
                errors.append(f"missing required field: {field_name}")
            elif isinstance(value, str) and not value.strip():
                errors.append(f"empty required field: {field_name}")

        if payload.get("game") != self.game_id:
            errors.append(f"game must be '{self.game_id}'")

        difficulty = payload.get("difficulty")
        if difficulty is not None and difficulty not in self._ALLOWED_DIFFICULTIES:
            errors.append(
                f"invalid difficulty: {difficulty} "
                f"(expected one of {sorted(self._ALLOWED_DIFFICULTIES)})"
            )

        if "source_file" not in payload:
            warnings.append("source_file missing (allowed in degraded mode)")

        if errors:
            return build_validation_fail(
                errors=errors,
                warnings=warnings,
                degraded_mode=False,
            )

        return build_validation_ok(
            warnings=warnings,
            degraded_mode=False,
        )