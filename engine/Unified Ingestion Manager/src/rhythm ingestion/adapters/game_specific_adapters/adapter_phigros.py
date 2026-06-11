#!/usr/bin/env python3
"""adapter_phigros.py

UMI Phase 3 adapter for Phigros.

This adapter is geometry-native (Bucket B): charts are defined as judge lines with
explicit note objects (time, positionX, holdTime, etc.). It performs deterministic
normalization into CanonicalChartPayload.

Scope:
- Implements BaseAdapter (accepts_file/load/to_canonical_row)
- Provides optional to_canonical_payload() aligned with ADAPTER_V2_SPEC
- No IO besides reading the source chart file
- No registry lookups
- No gameplay inference

Important note on timing:
- Phigros chart JSON encodes note timing as a numeric 'time' value.
- This adapter preserves the original timing in extra['time_raw'] and uses
  time_beats=float(time_raw) as a stable, monotonic timeline unit. If you later
  confirm the exact beat scaling, you can apply a deterministic conversion without
  changing downstream interfaces.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base_adapter import BaseAdapter


@dataclass
class PhigrosIngestRaw:
    chart_path: Path
    chart_id: str


def _infer_chart_id(path: Path) -> str:
    # Keep stable ID; callers can override via metadata later.
    return path.stem


def _load_chart_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def _map_note_type_to_kind(note_type: Any, hold_time: float) -> str:
    """Conservative mapping from phigros numeric type to canonical kind.

    We avoid asserting semantic meanings we cannot prove from the file alone.
    Rules:
    - If hold_time > 0 -> treat as hold_path (long note)
    - Otherwise treat as tap-like note (tap)

    The original note_type is always preserved in extra['raw_type'].
    """
    try:
        ht = float(hold_time or 0.0)
    except Exception:
        ht = 0.0
    if ht > 0.0:
        return "hold_path"
    return "tap"


def build_canonical_payload_phigros(source_ref: str) -> Dict[str, Any]:
    """Convert a Phigros chart JSON into CanonicalChartPayload."""

    path = Path(source_ref)
    data = _load_chart_json(path)

    fmt = data.get("formatVersion")
    offset = data.get("offset")
    judge_lines = data.get("judgeLineList") or []

    note_events: List[Dict[str, Any]] = []

    # Flatten all notes from each judge line.
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

                # time_beats as stable timeline unit; preserve raw time for later conversion.
                try:
                    time_beats = float(t_raw)
                except Exception:
                    # If time is missing/invalid, skip (validator will catch empty list if all skipped)
                    continue

                # Phigros uses continuous x; canonical expects lane int.
                # We keep a coarse lane bucket for compatibility while preserving x in extra.
                # Bucket rule: round(x) into int lane index with offset to keep lanes positive.
                lane_bucket = 1
                try:
                    lane_bucket = int(round(float(pos_x))) + 8  # shift to keep positive
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

                # For hold_path, carry a duration proxy
                if kind == "hold_path" and ht > 0.0:
                    extra["rect_height"] = ht
                    extra["shape"] = "hold"

                note_events.append(
                    {
                        "time_beats": time_beats,
                        "lane": lane_bucket,
                        "kind": kind,
                        "extra": extra,
                    }
                )

    # Sort for stability
    note_events.sort(key=lambda e: (float(e.get("time_beats", 0.0)), int(e.get("lane", 0)), str(e.get("kind", ""))))

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
    }
    if offset is not None:
        chart_meta["offset"] = offset
    chart_meta["judge_line_count"] = len(judge_lines) if isinstance(judge_lines, list) else 0

    adapter_metadata: Dict[str, Any] = {
        "adapter_id": "adapter_phigros",
        "adapter_version": "1.0.0",
        "source_format": "phigros_json",
        "source_path": str(path),
        "notes": "Phigros adapter reading formatVersion/offset/judgeLineList and flattening notesAbove/notesBelow.",
    }

    diagnostics: Dict[str, Any] = {
        "note_events_count": len(note_events),
        "judge_line_count": chart_meta.get("judge_line_count"),
        "format_version": fmt,
    }

    internal_metadata: Dict[str, Any] = {
        "adapter_id": adapter_metadata.get("adapter_id"),
        "adapter_version": adapter_metadata.get("adapter_version"),
        "sections_source": None,
    }

    payload: Dict[str, Any] = {
        "game_id": "phigros",
        "chart_id": str(path),
        "difficulty": "UNKNOWN",
        "note_events": note_events,
        "chart_meta": chart_meta,
        "adapter_metadata": adapter_metadata,
        "diagnostics": diagnostics,
        "internal_metadata": internal_metadata,
        # sections optional; computed downstream if desired
    }

    return payload


class PhigrosAdapter(BaseAdapter):
    game_id = "phigros"

    def accepts_file(self, path: Path) -> bool:
        return path.suffix.lower() in {".json"}

    def load(self, path: Path) -> PhigrosIngestRaw:
        return PhigrosIngestRaw(chart_path=path, chart_id=_infer_chart_id(path))

    def to_canonical_payload(self, source_ref: str) -> Dict[str, Any]:
        return build_canonical_payload_phigros(source_ref)

    def to_canonical_row(self, raw: PhigrosIngestRaw) -> Dict[str, Any]:
        payload = self.to_canonical_payload(str(raw.chart_path))
        note_events = payload.get("note_events") or []

        # Conservative chart combo proxy: count each note object once.
        note_total_chart = len(note_events) if isinstance(note_events, list) else 0

        chart_meta = payload.get("chart_meta") or {}

        return {
            "game": self.game_id,
            "song_id": raw.chart_id,
            "difficulty_label": payload.get("difficulty") or "UNKNOWN",
            "note_total_chart": int(note_total_chart),
            "duration_ms": None,
            "bpm": chart_meta.get("bpm"),
            "chart_path": str(raw.chart_path),
        }

    def capabilities(self) -> dict:
        return {
            "note_model": "spatial",
            "supports_sections": False,
            "supports_variable_bpm": True,
            "emits_canonical_payload": True,
            "source_format": "phigros_json",
        }


__all__ = [
    "PhigrosAdapter",
    "PhigrosIngestRaw",
    "build_canonical_payload_phigros",
]
