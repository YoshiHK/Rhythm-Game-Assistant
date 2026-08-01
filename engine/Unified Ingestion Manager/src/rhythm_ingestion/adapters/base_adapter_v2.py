#!/usr/bin/env python3
from __future__ import annotations

"""
base_adapter_v2.py

UMI Phase 3 Base Adapter (v2 contract)

Responsibilities:
- Define adapter interface
- Enforce canonical payload minimal contract
- Provide safe finalize step
- NO gameplay semantics
- NO DB writes
- NO validation logic
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------
# Base Adapter
# ---------------------------------------------------------------------

class BaseAdapterV2(ABC):
    """
    Base class for all Phase 3 adapters.
    """

    # must be overridden
    game_id: str = "unknown"
    adapter_id: str = "base_adapter_v2"
    adapter_version: str = "0.0.0"

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------
    @abstractmethod
    def accepts_file(self, path: str) -> bool:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Load raw data
    # ------------------------------------------------------------------
    @abstractmethod
    def load(self, path: str) -> Any:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Canonical payload
    # ------------------------------------------------------------------
    @abstractmethod
    def to_canonical_payload(self, path: str) -> Dict[str, Any]:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Canonical row
    # ------------------------------------------------------------------
    @abstractmethod
    def to_canonical_row(self, raw) -> Dict[str, Any]:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Capabilities (optional override)
    # ------------------------------------------------------------------
    def capabilities(self) -> Dict[str, Any]:
        return {
            "note_model": "unknown",
            "supports_sections": False,
            "supports_variable_bpm": False,
        }

    # ------------------------------------------------------------------
    # FINALIZE PAYLOAD (CRITICAL CONTRACT)
    # ------------------------------------------------------------------
    def finalize_payload_v2(
        self,
        payload: Dict[str, Any],
        *,
        source_path: str,
        default_chart_id: Optional[str] = None,
        default_difficulty: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Enforce minimal canonical payload contract.

        This method MUST:
        - guarantee required keys exist
        - normalize types (list / dict)
        - NEVER remove existing information
        - NEVER inject gameplay semantics
        """

        if not isinstance(payload, dict):
            raise ValueError("payload must be dict")

        # --------------------------------------------------
        # Required top-level fields
        # --------------------------------------------------
        payload.setdefault("game_id", self.game_id)
        payload.setdefault("chart_id", default_chart_id or source_path)
        payload.setdefault("title", None)
        payload.setdefault("difficulty", default_difficulty or "UNKNOWN")

        # --------------------------------------------------
        # note_events
        # --------------------------------------------------
        note_events = payload.get("note_events")
        if not isinstance(note_events, list):
            payload["note_events"] = []

        # ensure each event is dict
        sanitized_events = []
        for ev in payload["note_events"]:
            if isinstance(ev, dict):
                sanitized_events.append(ev)
        payload["note_events"] = sanitized_events

        # --------------------------------------------------
        # chart_meta
        # --------------------------------------------------
        chart_meta = payload.get("chart_meta")
        if not isinstance(chart_meta, dict):
            chart_meta = {}

        chart_meta.setdefault("bpm", None)
        chart_meta.setdefault("max_time_beats", 0.0)

        payload["chart_meta"] = chart_meta

        # --------------------------------------------------
        # adapter_metadata
        # --------------------------------------------------
        adapter_meta = payload.get("adapter_metadata")
        if not isinstance(adapter_meta, dict):
            adapter_meta = {}

        adapter_meta.setdefault("adapter_id", self.adapter_id)
        adapter_meta.setdefault("adapter_version", self.adapter_version)
        adapter_meta.setdefault("source_path", source_path)

        payload["adapter_metadata"] = adapter_meta

        # --------------------------------------------------
        # diagnostics
        # --------------------------------------------------
        diagnostics = payload.get("diagnostics")
        if not isinstance(diagnostics, dict):
            diagnostics = {}

        diagnostics.setdefault("note_event_count", len(payload["note_events"]))
        diagnostics.setdefault("has_events", bool(payload["note_events"]))

        payload["diagnostics"] = diagnostics

        # --------------------------------------------------
        # internal_metadata placeholder (if missing)
        # --------------------------------------------------
        if "internal_metadata" not in payload:
            payload["internal_metadata"] = {
                "adapter_id": self.adapter_id,
                "adapter_version": self.adapter_version,
            }

        return payload

    # ------------------------------------------------------------------
    # SAFE ENTRYPOINT (optional helper)
    # ------------------------------------------------------------------
    def build_canonical(self, path: str) -> Dict[str, Any]:
        """
        Convenience method:

        file → payload → canonical row
        """

        payload = self.to_canonical_payload(path)
        row = self.to_canonical_row(payload)

        return {
            "payload": payload,
            "row": row,
        }


__all__ = ["BaseAdapterV2"]