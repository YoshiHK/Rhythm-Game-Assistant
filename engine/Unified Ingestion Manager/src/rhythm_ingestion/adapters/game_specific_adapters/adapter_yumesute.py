#!/usr/bin/env python3
from __future__ import annotations

"""
adapter_yumesute.py (FULL REPLACEMENT - v2 normalized)

UMI Phase 3 adapter for Yumesute.

Responsibilities:
- Parse SUS charts → canonical payload
- Guarantee minimal payload contract
- Preserve raw structure in `extra`
- NO gameplay semantics inference

Aligned with:
- BaseAdapterV2
- canonical payload schema
- validator_v2 contract
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

from ..base_adapter_v2 import BaseAdapterV2
from ..common_adapter_utils import (
    attach_if_missing,
    build_internal_metadata,
)

# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

GAME_ID = "yumesute"
_SUS_EXTS = {".sus"}


# ---------------------------------------------------------------------
# Extractor wiring
# ---------------------------------------------------------------------

try:
    from .yumesute_sus_extract import extract_yumesute_note_events_from_sus  # type: ignore
except Exception:
    extract_yumesute_note_events_from_sus = None  # type: ignore


def _tick_to_beats(tick: int) -> float:
    return float(tick) / 480.0


def _safe_int(x: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        if x is None:
            return default
        return int(x)
    except Exception:
        return default


def _safe_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


# ---------------------------------------------------------------------
# Fallback extractor
# ---------------------------------------------------------------------

def _extract_local(sus_text: str, *, lane_offset: int = 2) -> Dict[str, Any]:

    try:
        import sus  # type: ignore
    except Exception as e:
        raise ImportError("Missing `sus` parser for fallback extraction") from e

    score = sus.loads(sus_text)

    note_events: List[Dict[str, Any]] = []

    for t in getattr(score, "taps", []):
        try:
            note_events.append({
                "kind": "tap",
                "time_beats": _tick_to_beats(int(t.tick)),
                "lane": int(t.lane) + lane_offset,
                "extra": {
                    "raw_type": "tap",
                    "tick": int(t.tick),
                }
            })
        except Exception:
            continue

    chart_meta: Dict[str, Any] = {
        "bpm": float(score.bpms[0][1]) if getattr(score, "bpms", None) else 0.0
    }

    return {
        "note_events": note_events,
        "chart_meta": chart_meta,
    }


def extract_yumesute_note_events(sus_text: str) -> Dict[str, Any]:
    if extract_yumesute_note_events_from_sus:
        return extract_yumesute_note_events_from_sus(sus_text)
    return _extract_local(sus_text)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _infer_song_and_diff(path: Path) -> Tuple[str, str]:
    stem = path.stem.strip()
    diff = "UNKNOWN"
    name = stem

    if "[" in stem and "]" in stem:
        l = stem.rfind("[")
        r = stem.rfind("]")
        if l < r:
            diff = stem[l + 1:r].strip() or "UNKNOWN"
            name = stem[:l].strip() or stem

    return name, diff.upper()


# ---------------------------------------------------------------------
# Adapter Class
# ---------------------------------------------------------------------

class YumesuteAdapter(BaseAdapterV2):
    game_id = GAME_ID
    adapter_id = "adapter_yumesute"
    adapter_version = "2.0.0"

    # --------------------------------------------------
    # Routing
    # --------------------------------------------------
    def accepts_file(self, path) -> bool:
        p = Path(path)
        return p.suffix.lower() in _SUS_EXTS

    # --------------------------------------------------
    # Load
    # --------------------------------------------------
    def load(self, path):
        p = Path(path)
        return p.read_text(encoding="utf-8", errors="ignore")

    # --------------------------------------------------
    # Canonical payload
    # --------------------------------------------------
    def to_canonical_payload(self, path: str) -> Dict[str, Any]:

        p = Path(path)
        text = self.load(p)

        extracted = extract_yumesute_note_events(text)

        note_events = list(extracted.get("note_events") or [])
        chart_meta = dict(extracted.get("chart_meta") or {})

        # --- ensure max_time_beats ---
        max_beats = 0.0
        for ev in note_events:
            try:
                max_beats = max(max_beats, float(ev.get("time_beats", 0.0)))
            except Exception:
                pass

        chart_meta["max_time_beats"] = max_beats

        # --- identity ---
        title, difficulty = _infer_song_and_diff(p)

        payload: Dict[str, Any] = {
            "game_id": GAME_ID,
            "chart_id": str(p),
            "title": title,
            "difficulty": difficulty,

            "note_events": note_events,
            "chart_meta": chart_meta,

            "adapter_metadata": {
                "adapter_id": self.adapter_id,
                "adapter_version": self.adapter_version,
                "source_format": "sus",
                "source_path": str(p),
            },

            "diagnostics": {
                "note_event_count": len(note_events),
            },
        }

        # --------------------------------------------------
        # Enforce minimal contract (CRITICAL)
        # --------------------------------------------------
        payload = self.finalize_payload_v2(
            payload,
            source_path=str(p),
            default_chart_id=payload["chart_id"],
            default_difficulty=payload["difficulty"],
        )

        # attach internal metadata
        internal = build_internal_metadata(
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
        )
        attach_if_missing(payload, "internal_metadata", internal)

        return payload

    # --------------------------------------------------
    # Canonical row
    # --------------------------------------------------
    def to_canonical_row(self, raw) -> Dict[str, Any]:

        if isinstance(raw, dict):
            payload = raw
        else:
            payload = self.to_canonical_payload(str(raw))

        note_events = payload.get("note_events") or []
        chart_meta = payload.get("chart_meta") or {}

        bpm = _safe_float(chart_meta.get("bpm"), None)
        max_beats = _safe_float(chart_meta.get("max_time_beats"), 0.0) or 0.0

        duration_ms = 0
        if bpm and bpm > 0:
            duration_ms = int((max_beats / bpm) * 60000)

        return {
            "game": GAME_ID,
            "game_id": GAME_ID,
            "song_id": payload.get("chart_id"),
            "name": payload.get("title"),
            "title": payload.get("title"),

            "tier": payload.get("difficulty"),
            "difficulty_label": payload.get("difficulty"),

            "note_total_chart": len(note_events),
            "duration_ms": duration_ms,
            "bpm": bpm,
        }

    # --------------------------------------------------
    # Capabilities
    # --------------------------------------------------
    def capabilities(self) -> Dict[str, Any]:
        return {
            "note_model": "lane_based",
            "supports_sections": True,
            "supports_variable_bpm": True,
            "supports_sus": True,
        }


__all__ = ["YumesuteAdapter"]