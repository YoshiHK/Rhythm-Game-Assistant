"""
section_metrics_dataclasses.py

Dataclass definitions for SectionMetrics (Stage 2–4.1).

This module defines the canonical, game-agnostic data structures used to
represent per-section structural metrics derived from a chart.

Responsibilities:
- Define SectionMetrics as a stable data contract
- Support serialization (to_dict / from_dict)
- Provide lightweight validation consistent with schema expectations

This module MUST NOT:
- perform section slicing
- detect pattern tags
- infer severity or difficulty
- depend on adapters, validators, or tips logic
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LaneUsage:
    """
    Distribution of note counts across lanes for a section.
    Keys are lane indices (as strings for JSON safety).
    """
    counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return dict(self.counts)


@dataclass
class SectionMetrics:
    """
    Canonical per-section structural metrics.

    This structure is consumed by:
    - pattern tag detection
    - severity / score calibration
    - dominance and coverage calculations
    """

    # --- Section identity ---
    section_index: int
    start_time_beats: float
    end_time_beats: float

    # --- Core counts ---
    note_count: int = 0
    tap_count: int = 0
    hold_count: int = 0
    flick_count: int = 0

    # --- Density / coverage ---
    duration_beats: float = 0.0
    note_density: float = 0.0          # notes per beat
    section_coverage: float = 0.0      # [0,1], relative contribution to chart

    # --- Lane / spatial stats ---
    lane_usage: Optional[LaneUsage] = None

    # --- Optional diagnostics / extensions ---
    extra: Optional[Dict[str, object]] = None

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """
        Convert this SectionMetrics instance into a JSON-serializable dict.
        """
        out = {
            "section_index": self.section_index,
            "start_time_beats": self.start_time_beats,
            "end_time_beats": self.end_time_beats,
            "note_count": self.note_count,
            "tap_count": self.tap_count,
            "hold_count": self.hold_count,
            "flick_count": self.flick_count,
            "duration_beats": self.duration_beats,
            "note_density": self.note_density,
            "section_coverage": self.section_coverage,
        }

        if self.lane_usage is not None:
            out["lane_usage"] = self.lane_usage.to_dict()

        if self.extra:
            out["extra"] = dict(self.extra)

        return out

    @staticmethod
    def from_dict(data: dict) -> "SectionMetrics":
        """
        Create a SectionMetrics instance from a dict (e.g., loaded JSON).
        """
        lane_usage = None
        if isinstance(data.get("lane_usage"), dict):
            lane_usage = LaneUsage(counts=dict(data["lane_usage"]))

        return SectionMetrics(
            section_index=int(data["section_index"]),
            start_time_beats=float(data["start_time_beats"]),
            end_time_beats=float(data["end_time_beats"]),
            note_count=int(data.get("note_count", 0)),
            tap_count=int(data.get("tap_count", 0)),
            hold_count=int(data.get("hold_count", 0)),
            flick_count=int(data.get("flick_count", 0)),
            duration_beats=float(data.get("duration_beats", 0.0)),
            note_density=float(data.get("note_density", 0.0)),
            section_coverage=float(data.get("section_coverage", 0.0)),
            lane_usage=lane_usage,
            extra=dict(data["extra"]) if isinstance(data.get("extra"), dict) else None,
        )

    # ------------------------------------------------------------------
    # Lightweight validation (non-exhaustive)
    # ------------------------------------------------------------------

    def validate_basic(self) -> None:
        """
        Perform basic sanity checks consistent with schema constraints.
        This is intentionally lightweight and non-exhaustive.
        """
        if self.section_index < 0:
            raise ValueError("section_index must be >= 0")

        if self.end_time_beats < self.start_time_beats:
            raise ValueError("end_time_beats must be >= start_time_beats")

        if self.note_count < 0:
            raise ValueError("note_count must be >= 0")

        if any(x < 0 for x in (self.tap_count, self.hold_count, self.flick_count)):
            raise ValueError("note subtype counts must be >= 0")

        if self.duration_beats < 0:
            raise ValueError("duration_beats must be >= 0")

        if self.note_density < 0:
            raise ValueError("note_density must be >= 0")

        if not (0.0 <= self.section_coverage <= 1.0):
            raise ValueError("section_coverage must be in [0,1]")

        if self.lane_usage:
            for k, v in self.lane_usage.counts.items():
                if int(v) < 0:
                    raise ValueError("lane_usage counts must be >= 0")


__all__ = [
    "LaneUsage",
    "SectionMetrics",
]
