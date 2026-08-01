#!/usr/bin/env python3
from __future__ import annotations

"""
adapter_phigros.py (FULL REPLACEMENT - v2 normalized)

UMI Phase 3 adapter for Phigros.

This adapter is geometry-native: charts are defined as judge lines with
explicit note objects (time, positionX, holdTime, etc.). It performs
deterministic normalization into CanonicalChartPayload.

Scope:
- Implements BaseAdapterV2
- Provides to_canonical_payload() aligned with adapter v2 contract
- Provides to_canonical_row() aligned with canonical_row contract
- No registry lookups
- No gameplay inference
- No Phase 4 / tips logic

Timing note:
- Phigros chart JSON encodes note timing as numeric 'time'
- This adapter preserves original timing in extra['time_raw']
- time_beats uses float(time_raw) as a stable, monotonic timeline unit
- If exact beat scaling is confirmed later, conversion can be updated
  without changing downstream interfaces
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..base_adapter_v2 import BaseAdapterV2
from ..common_adapter_utils import (
    build_internal_metadata,
    canonical_sections_version,
    build_standard_diagnostics,
    attach_if_missing,
    with_baseline_fallback_extensions,
)

# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

GAME_ID = "phigros"
_ADAPTER_ID = "adapter_phigros"
_ADAPTER_VERSION = "2.0.0"
_SECTION_VERSION = canonical_sections_version(GAME_ID, "adapter_phigros", "v2")

# Phigros adapter emits a conservative subset:
# - tap
# - hold_path
_CANONICAL_KINDS = {
    "tap",
    "hold_path",
}

_ALLOWED_EXTS = with_baseline_fallback_extensions([".json"], include_baseline=False)


# ---------------------------------------------------------------------
# Raw ingestion model
# ---------------------------------------------------------------------

@dataclass
class PhigrosIngestRaw:
    chart_path: Path
    chart_id: str


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _infer_chart_id(path: Path) -> str:
    # Stable ID; may be refined later if song metadata becomes available.
    return path.stem


def _infer_title(path: Path) -> str:
    return path.stem.strip() or path.name


def _load_chart_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def _safe_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _map_note_type_to_kind(note_type: Any, hold_time: float) -> str:
    """
    Conservative mapping from Phigros numeric type to canonical kind.

    Rules:
    - If hold_time > 0 -> hold_path
    - Otherwise -> tap

    Original note_type is preserved in extra['raw_type'].
    """
    try:
        ht = float(hold_time or 0.0)
    except Exception:
        ht = 0.0

    if ht > 0.0:
        return "hold_path"
    return "tap"


# ---------------------------------------------------------------------
# Canonical payload builder
# ---------------------------------------------------------------------

def build_canonical_payload_phigros(source_ref: str) -> Dict[str, Any]:
    """
    Convert a Phigros chart JSON into CanonicalChartPayload.
    """
    path = Path(source_ref)
    data = _load_chart_json(path)

    fmt = data.get("formatVersion")
    offset = data.get("offset")
    judge_lines = data.get("judgeLineList") or []

    note_events: List[Dict[str, Any]] = []

    # Flatten notes from each judge line
    for jl_idx, jl in enumerate(judge_lines):
        if not isinstance(jl, dict):
            continue

        jl_bpm = jl.get("bpm")

        for side_key in ("notesAbove", "notesBelow"):
            notes = jl.get(side_key) or []
            if not isinstance(notes, list):
                continue

            for n in notes:
                if not isinstance(n, dict):
                    continue

                n_type = n.get("type")
                t_raw = n.get("time")
                pos_x = n.get("positionX")
                hold_time = n.get("holdTime")
                speed = n.get("speed")
                floor_pos = n.get("floorPosition")

                # Stable timeline
                try:
                    time_beats = float(t_raw)
                except Exception:
                    continue

                # Coarse positive bucket lane for compatibility
                lane_bucket = 1
                try:
                    lane_bucket = int(round(float(pos_x))) + 8
                except Exception:
                    lane_bucket = 1

                try:
                    ht = float(hold_time or 0.0)
                except Exception:
                    ht = 0.0

                kind = _map_note_type_to_kind(n_type, ht)

                extra: Dict[str, Any] = {
                    "raw_type": n_type,
                    "time_raw": t_raw,
                    "positionX": pos_x,
                    "holdTime": hold_time,
                    "speed": speed,
                    "floorPosition": floor_pos,
                    "judge_line_index": jl_idx,
                    "note_side": side_key,
                }

                if jl_bpm is not None:
                    extra["judge_line_bpm"] = jl_bpm

                if kind == "hold_path" and ht > 0.0:
                    extra["rect_height"] = ht
                    extra["shape"] = "hold"
                    extra["duration_proxy"] = ht

                note_events.append(
                    {
                        "time_beats": time_beats,
                        "lane": lane_bucket,
                        "kind": kind,
                        "extra": extra,
                    }
                )

    # Stable ordering
    note_events.sort(
        key=lambda e: (
            float(e.get("time_beats", 0.0)),
            int(e.get("lane", 0)),
            str(e.get("kind", "")),
        )
    )

    # chart_meta
    max_time = 0.0
    for ev in note_events:
        tb = ev.get("time_beats")
        if isinstance(tb, (int, float)):
            max_time = max(max_time, float(tb))

    base_bpm: Optional[float] = None
    if isinstance(judge_lines, list) and judge_lines:
        first = judge_lines[0]
        if isinstance(first, dict) and isinstance(first.get("bpm"), (int, float)):
            base_bpm = float(first.get("bpm"))

    chart_meta: Dict[str, Any] = {
        "bpm": base_bpm or 0.0,
        "max_time_beats": max_time,
        "format_version": fmt,
        "judge_line_count": len(judge_lines) if isinstance(judge_lines, list) else 0,
    }

    if offset is not None:
        chart_meta["offset"] = offset

    adapter_metadata: Dict[str, Any] = {
        "adapter_id": _ADAPTER_ID,
        "adapter_version": _ADAPTER_VERSION,
        "source_format": "phigros_json",
        "source_path": str(path),
        "notes": "Phigros adapter flattens judgeLineList notesAbove/notesBelow into canonical note_events.",
    }

    diagnostics: Dict[str, Any] = {
        "note_events_count": len(note_events),
        "judge_line_count": chart_meta.get("judge_line_count"),
        "format_version": fmt,
    }

    internal_metadata: Dict[str, Any] = build_internal_metadata(
        adapter_id=_ADAPTER_ID,
        adapter_version=_ADAPTER_VERSION,
        sections_source=None,
        notes="structural-only; geometry-native phigros adapter",
    )

    payload: Dict[str, Any] = {
        "game_id": GAME_ID,
        "chart_id": str(path.resolve()),
        "title": _infer_title(path),
        "difficulty": "UNKNOWN",

        "note_events": note_events,
        "chart_meta": chart_meta,
        "adapter_metadata": adapter_metadata,
        "diagnostics": diagnostics,
        "internal_metadata": internal_metadata,

        # compatibility aliases
        "song_id": _infer_chart_id(path),
    }

    return payload


# ---------------------------------------------------------------------
# Adapter implementation
# ---------------------------------------------------------------------

class PhigrosAdapter(BaseAdapterV2):
    game_id = GAME_ID
    adapter_id = _ADAPTER_ID
    adapter_version = _ADAPTER_VERSION

    def accepts_file(self, path: Any) -> bool:
        p = Path(path)
        return p.suffix.casefold() in _ALLOWED_EXTS

    def load(self, path: Any) -> PhigrosIngestRaw:
        p = Path(path)
        return PhigrosIngestRaw(chart_path=p, chart_id=_infer_chart_id(p))

    def to_canonical_payload(self, source_ref: str) -> Dict[str, Any]:
        payload = build_canonical_payload_phigros(source_ref)
        if not isinstance(payload, dict):
            payload = {}

        diagnostics = payload.get("diagnostics")
        if not isinstance(diagnostics, dict):
            diagnostics = {}

        diagnostics.setdefault("game_id", self.game_id)
        diagnostics.setdefault("adapter_id", self.adapter_id)
        diagnostics.setdefault("adapter_version", self.adapter_version)
        diagnostics.setdefault("source_path", str(source_ref))

        try:
            diag = build_standard_diagnostics(payload.get("sections"))
            for k, v in diag.items():
                diagnostics.setdefault(k, v)
        except Exception:
            pass

        payload["diagnostics"] = diagnostics

        internal_meta = payload.get("internal_metadata")
        if not isinstance(internal_meta, dict):
            internal_meta = {}

        try:
            meta = build_internal_metadata(
                adapter_id=self.adapter_id,
                adapter_version=self.adapter_version,
                sections_source="phigros-json",
            )
            for k, v in meta.items():
                internal_meta.setdefault(k, v)
        except Exception:
            pass

        try:
            internal_meta.setdefault(
                "canonical_sections_version",
                _SECTION_VERSION,
            )
        except Exception:
            pass

        payload["internal_metadata"] = internal_meta

        # CRITICAL: enforce v2 payload contract
        payload = self.finalize_payload_v2(
            payload,
            source_path=str(source_ref),
            default_chart_id=payload.get("chart_id") or str(Path(source_ref).resolve()),
            default_difficulty=payload.get("difficulty") or "UNKNOWN",
        )

        return payload

    def to_canonical_row(self, raw: Any) -> Dict[str, Any]:
        if isinstance(raw, PhigrosIngestRaw):
            payload = self.to_canonical_payload(str(raw.chart_path))
            chart_path = str(raw.chart_path)
            song_id = raw.chart_id
        elif isinstance(raw, dict):
            payload = raw
            chart_path = str(raw.get("chart_id") or raw.get("source_path") or "")
            song_id = payload.get("song_id")
        else:
            chart_path = str(raw)
            payload = self.to_canonical_payload(chart_path)
            song_id = _infer_chart_id(Path(chart_path))

        if not isinstance(payload, dict):
            payload = {}

        note_events = payload.get("note_events")
        if not isinstance(note_events, list):
            note_events = []

        chart_meta = payload.get("chart_meta")
        if not isinstance(chart_meta, dict):
            chart_meta = {}

        difficulty = payload.get("difficulty") or "UNKNOWN"
        title = payload.get("title") or _infer_title(Path(chart_path)) if chart_path else None

        return {
            "game": self.game_id,
            "game_id": self.game_id,
            "song_id": song_id,
            "name": title,
            "title": title,
            "tier": difficulty,
            "level": None,
            "difficulty_code": None,
            "difficulty_label": difficulty,
            "note_total_chart": int(len(note_events)),
            "note_total_db": None,
            "note_delta": None,
            "duration_ms": chart_meta.get("max_time_ms"),
            "bpm": chart_meta.get("bpm"),
            "rating_raw": None,
            "chart_path": chart_path,
        }

    def capabilities(self) -> dict:
        return {
            "note_model": "spatial",
            "supports_sections": False,
            "supports_variable_bpm": True,
            "emits_canonical_payload": True,
            "source_format": "phigros_json",
            "canonical_kinds": list(_CANONICAL_KINDS),
        }


__all__ = [
    "PhigrosAdapter",
    "PhigrosIngestRaw",
    "build_canonical_payload_phigros",
]