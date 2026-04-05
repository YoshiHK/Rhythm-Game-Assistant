"""base_validator_v2.py

Validator v2 base helpers for UMI Phase 3.

Supported games (source of truth):
- The authoritative list of supported games is defined in **games.json**.
- This module MUST NOT hardcode the supported game list.
- Validators should set `game_id` to a value present in games.json.
- Enable/disable decisions belong to games.json + loader/wiring.

Why this file exists (additive, non-breaking):
- base_validator.py defines a legacy exception-based validation contract.
- VALIDATOR_V2_SPEC defines the v2 ValidationResult dict contract.
- common_validator_utils provides standard builders and safe helpers.

Usage model:
- New/migrated validators inherit BaseValidatorV2 and implement validate_v2(...).
- Legacy validators may implement validate_legacy(...); exceptions are wrapped.
"""

from __future__ import annotations

from abc import ABC
from typing import Any, Dict, List, Optional, Tuple

from .common_validator_utils import build_validation_fail, build_validation_ok, safe_int

ValidationResult = Dict[str, Any]


class BaseValidatorV2(ABC):
    """Validator v2 base that always returns a ValidationResult dict."""

    game_id: Optional[str] = None

    def validate(self, canonical_payload: Dict[str, Any], **context: Any) -> ValidationResult:
        # Preferred v2 path
        if hasattr(self, "validate_v2") and callable(getattr(self, "validate_v2")):
            return getattr(self, "validate_v2")(canonical_payload, **context)

        # Legacy exception-based path
        if hasattr(self, "validate_legacy") and callable(getattr(self, "validate_legacy")):
            try:
                getattr(self, "validate_legacy")(
                    raw_chart=context.get("raw_chart"),
                    canonical_payload=canonical_payload,
                    canonical_row=context.get("canonical_row") or {},
                )
            except Exception as e:
                return build_validation_fail(errors=[str(e)], warnings=[], degraded_mode=False)
            return build_validation_ok(warnings=[], degraded_mode=False)

        return build_validation_fail(
            errors=["Validator does not implement validate_v2() or validate_legacy()."],
            warnings=[],
            degraded_mode=False,
        )

    def capabilities(self) -> dict:
        return {}

    def explain_failure(self, result: dict) -> str:
        return ""

    # ------------------------------------------------------------------
    # Shared structural helpers
    # ------------------------------------------------------------------
    @staticmethod
    def require_dict(payload: Any, *, name: str = "canonical_payload") -> Tuple[Optional[Dict[str, Any]], List[str]]:
        errors: List[str] = []
        if not isinstance(payload, dict):
            errors.append(f"{name} must be a dict.")
            return None, errors
        return payload, errors

    @staticmethod
    def require_list(value: Any, *, field: str) -> Tuple[Optional[List[Any]], List[str]]:
        errors: List[str] = []
        if not isinstance(value, list):
            errors.append(f"{field} must be a list.")
            return None, errors
        return value, errors

    @staticmethod
    def non_decreasing_int(values: List[Any], *, field: str) -> List[str]:
        errors: List[str] = []
        last: Optional[int] = None
        for item in values:
            if not isinstance(item, dict):
                continue
            iv = safe_int(item.get(field), default=None)
            if iv is None:
                continue
            if last is not None and iv < last:
                errors.append(f"{field} is not non-decreasing.")
                break
            last = iv
        return errors


__all__ = ["BaseValidatorV2", "ValidationResult"]
