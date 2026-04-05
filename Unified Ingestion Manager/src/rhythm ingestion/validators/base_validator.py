"""base_validator.py

Base validator interface for canonical chart/song validation.

Supported games (source of truth):
- The authoritative list of supported games is defined in **games.json**.
- This module MUST NOT hardcode the supported game list.
- Each concrete validator MUST set `game_id` to a value that matches a games.json entry.
- Enable/disable decisions belong to games.json + loader/wiring, not to validators.

Each rhythm game should provide a concrete validator that:
- Extends BaseValidator
- Sets a `game_id` string (e.g. "proseka", "arcaea", "bandori")
- Implements validate(...) with game-specific structural checks

Validator responsibilities (per chart):
1. Validate the song-level canonical row
2. Validate the per-chart canonical payload (structural only)

Phase note:
- This class defines the legacy contract only.
- Concrete validators decide strictness and failure behavior.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from rhythm_ingestion.pipeline.pattern_tags.pattern_tags_taxonomy import PatternTagsTaxonomy


class BaseValidator(ABC):
    """Abstract base class for all UMI Phase-3 validators (legacy interface)."""

    game_id: Optional[str] = None

    @abstractmethod
    def validate(
        self,
        *,
        raw_chart: Any,
        canonical_payload: Dict[str, Any],
        canonical_row: Dict[str, Any],
    ) -> None:
        """Validate a single chart ingestion result (legacy, exception-based)."""
        raise NotImplementedError

    def capabilities(self) -> dict:
        """OPTIONAL: informational only."""
        return {}

    def explain_failure(self, result: dict) -> str:
        """OPTIONAL: human-readable explanation for QA / UI."""
        return ""

    # ------------------------------------------------------------------
    # Shared Phase-3 helper: pattern tag validation (unchanged)
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_pattern_tags(
        canonical_payload: Dict[str, Any],
        errors: List[str],
        *,
        strict: bool,
        payload_key: str = "detected_tags",
    ) -> None:
        tags = canonical_payload.get(payload_key)
        if tags is None:
            return
        if not isinstance(tags, list):
            errors.append(f"canonical_payload['{payload_key}'] must be a list when present.")
            return
        normalized: List[str] = []
        for t in tags:
            if not isinstance(t, str):
                errors.append(f"canonical_payload['{payload_key}'] entries must be str, got {type(t).__name__}.")
                continue
            normalized.append(PatternTagsTaxonomy.normalize_tag(t))
        canonical_payload[payload_key] = normalized
        unknown = PatternTagsTaxonomy.validate_tags(normalized)
        if unknown:
            diagnostics = canonical_payload.get("diagnostics")
            if not isinstance(diagnostics, dict):
                diagnostics = {}
                canonical_payload["diagnostics"] = diagnostics
            tag_parity = diagnostics.setdefault("tag_parity", {})
            tag_parity["unknown_tags"] = unknown
            if strict:
                errors.append(f"Unknown pattern tags found: {unknown}")
