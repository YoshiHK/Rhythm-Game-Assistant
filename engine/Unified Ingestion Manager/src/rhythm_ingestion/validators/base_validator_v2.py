#!/usr/bin/env python3
from __future__ import annotations

"""
base_validator_v2.py

Validator v2 base helpers for UMI Phase 3.

Supported games (source of truth):
- The authoritative list of supported games is defined in games.json.
- This module MUST NOT hardcode the supported game list.
- Validators should set `game_id` to a value present in games.json.
- Enable/disable decisions belong to games.json + loader/wiring.

Why this file exists (additive, non-breaking):
- base_validator.py defines a legacy exception-based validation contract.
- BaseValidatorV2 defines a dict-based ValidationResult contract and shared
  compatibility helpers for migrated validators.

Usage model:
- New/migrated validators inherit BaseValidatorV2 and implement validate_v2(...).
- Legacy validators may implement validate_legacy(...); exceptions are wrapped.
- Validators may also override validate(...) directly if necessary, but the
  recommended path is validate_v2(...).
"""

from abc import ABC
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .common_validator_utils import (
    build_validation_fail,
    build_validation_ok,
    safe_int,
)

ValidationResult = Dict[str, Any]


class BaseValidatorV2(ABC):
    """Validator v2 base that always returns a ValidationResult dict."""

    game_id: Optional[str] = None
    validator_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Public bridge entrypoint
    # ------------------------------------------------------------------
    def validate(self, payload: Optional[Dict[str, Any]] = None, **context: Any) -> ValidationResult:
        """
        Standard bridge entrypoint.

        Preferred:
            validate_v2(payload, **context)

        Legacy fallback:
            validate_legacy(raw_chart=..., canonical_payload=..., canonical_row=...)

        This method is intentionally additive and non-breaking.
        """
        # Preferred v2 path
        if hasattr(self, "validate_v2") and callable(getattr(self, "validate_v2")):
            return getattr(self, "validate_v2")(payload, **context)

        # Legacy exception-based path
        if hasattr(self, "validate_legacy") and callable(getattr(self, "validate_legacy")):
            canonical_payload, canonical_row, _ = self.coerce_payload_and_row(
                payload,
                canonical_payload=context.get("canonical_payload"),
                canonical_row=context.get("canonical_row"),
            )

            try:
                getattr(self, "validate_legacy")(
                    raw_chart=context.get("raw_chart"),
                    canonical_payload=canonical_payload,
                    canonical_row=canonical_row,
                )
            except Exception as e:
                return self.fail_result(
                    errors=[str(e)],
                    warnings=[],
                    degraded_mode=False,
                    diagnostics={"bridge_mode": "legacy_exception_wrapper"},
                )

            return self.ok_result(
                warnings=[],
                degraded_mode=False,
                diagnostics={"bridge_mode": "legacy_exception_wrapper"},
            )

        return self.fail_result(
            errors=["Validator does not implement validate_v2() or validate_legacy()."],
            warnings=[],
            degraded_mode=False,
            diagnostics={"bridge_mode": "missing_implementation"},
        )

    # ------------------------------------------------------------------
    # Result finalization
    # ------------------------------------------------------------------
    def _resolved_validator_id(self) -> str:
        if isinstance(self.validator_id, str) and self.validator_id.strip():
            return self.validator_id
        return self.__class__.__name__

    def build_result(
        self,
        *,
        ok: bool,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        degraded_mode: bool = False,
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        errors = list(errors or [])
        warnings = list(warnings or [])
        diagnostics = dict(diagnostics or {})

        if ok:
            result = build_validation_ok(
                warnings=warnings,
                degraded_mode=degraded_mode,
            )
        else:
            result = build_validation_fail(
                errors=errors,
                warnings=warnings,
                degraded_mode=degraded_mode,
            )

        result["game_id"] = self.game_id
        result["validator_id"] = self._resolved_validator_id()
        result["diagnostics"] = diagnostics
        return result

    def ok_result(
        self,
        *,
        warnings: Optional[List[str]] = None,
        degraded_mode: bool = False,
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        return self.build_result(
            ok=True,
            warnings=warnings,
            degraded_mode=degraded_mode,
            diagnostics=diagnostics,
        )

    def fail_result(
        self,
        *,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        degraded_mode: bool = False,
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        return self.build_result(
            ok=False,
            errors=errors,
            warnings=warnings,
            degraded_mode=degraded_mode,
            diagnostics=diagnostics,
        )

    def capabilities(self) -> dict:
        return {}

    def explain_failure(self, result: dict) -> str:
        return ""

    # ------------------------------------------------------------------
    # Shared input / structural helpers
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

    # ------------------------------------------------------------------
    # Shared compatibility helpers
    # ------------------------------------------------------------------
    @staticmethod
    def first_nonempty_str(*values: Any) -> Optional[str]:
        for v in values:
            if isinstance(v, str):
                s = v.strip()
                if s:
                    return s
        return None

    @staticmethod
    def normalize_upper_token(value: Any) -> Optional[str]:
        if not isinstance(value, str):
            return None
        s = value.strip()
        if not s:
            return None
        return s.upper()

    @staticmethod
    def infer_title_from_path(path_value: Any) -> Optional[str]:
        if not isinstance(path_value, str):
            return None
        try:
            p = Path(path_value)
            stem = p.stem.strip()
            return stem or None
        except Exception:
            return None

    def coerce_payload_and_row(
        self,
        payload: Optional[Dict[str, Any]] = None,
        *,
        canonical_payload: Optional[Dict[str, Any]] = None,
        canonical_row: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
        """
        Normalize accepted validator input shapes.

        Supported:
        A) validate(payload_only_dict)
        B) validate({"canonical_payload": ..., "canonical_row": ...})
        C) validate(canonical_payload=..., canonical_row=...)
        """
        if canonical_payload is None and canonical_row is None and isinstance(payload, dict):
            canonical_payload = payload.get("canonical_payload") or payload
            canonical_row = payload.get("canonical_row") or payload
            input_kind = "canonical_row" if ("canonical_payload" in payload or "canonical_row" in payload) else "canonical_payload"
        else:
            input_kind = "explicit"

        if not isinstance(canonical_payload, dict):
            canonical_payload = {}

        if not isinstance(canonical_row, dict):
            canonical_row = {}

        return canonical_payload, canonical_row, input_kind

    def resolve_identity_fields(
        self,
        canonical_payload: Dict[str, Any],
        canonical_row: Dict[str, Any],
        *,
        default_game_id: Optional[str] = None,
        default_chart_id: Optional[str] = None,
        default_title: Optional[str] = None,
        default_difficulty: Optional[str] = None,
    ) -> Dict[str, Optional[str]]:
        """
        Resolve a minimum shared identity bundle from aliases.

        Returned keys:
            game
            chart_id
            title
            difficulty
        """
        resolved_game = self.first_nonempty_str(
            canonical_payload.get("game"),
            canonical_payload.get("game_id"),
            canonical_row.get("game"),
            canonical_row.get("game_id"),
            default_game_id,
            self.game_id,
        )

        resolved_chart_id = self.first_nonempty_str(
            canonical_payload.get("chart_id"),
            canonical_row.get("chart_id"),
            canonical_row.get("song_id"),
            canonical_payload.get("song_id"),
            canonical_payload.get("id"),
            default_chart_id,
        )

        resolved_title = self.first_nonempty_str(
            canonical_payload.get("title"),
            canonical_row.get("title"),
            canonical_payload.get("name"),
            canonical_row.get("name"),
            canonical_payload.get("song_title"),
            canonical_row.get("song_title"),
            self.infer_title_from_path(canonical_payload.get("source_file")),
            self.infer_title_from_path(canonical_payload.get("chart_path")),
            self.infer_title_from_path(canonical_row.get("source_file")),
            self.infer_title_from_path(canonical_row.get("chart_path")),
            default_title,
        )

        resolved_difficulty = self.normalize_upper_token(
            self.first_nonempty_str(
                canonical_payload.get("difficulty"),
                canonical_row.get("difficulty"),
                canonical_payload.get("difficulty_label"),
                canonical_row.get("difficulty_label"),
                canonical_row.get("tier"),
                default_difficulty,
            )
        )

        return {
            "game": resolved_game,
            "chart_id": resolved_chart_id,
            "title": resolved_title,
            "difficulty": resolved_difficulty,
        }

    @staticmethod
    def warn_missing_optional(
        warnings: List[str],
        payload: Dict[str, Any],
        *,
        fields: List[str],
        prefix: str = "missing optional field:",
    ) -> None:
        for field in fields:
            if field not in payload:
                warnings.append(f"{prefix} {field}")

    @staticmethod
    def soft_count_parity(
        *,
        row_count: Optional[int],
        payload_count: Optional[int],
        warnings: List[str],
        label: str,
        absolute_floor: int = 50,
        relative_ratio: float = 0.2,
    ) -> None:
        if row_count is None or payload_count is None:
            return
        threshold = max(absolute_floor, int(relative_ratio * max(1, row_count)))
        if abs(payload_count - row_count) > threshold:
            warnings.append(
                f"{label} mismatch is large: row={row_count}, payload_count={payload_count}."
            )


__all__ = ["BaseValidatorV2", "ValidationResult"]