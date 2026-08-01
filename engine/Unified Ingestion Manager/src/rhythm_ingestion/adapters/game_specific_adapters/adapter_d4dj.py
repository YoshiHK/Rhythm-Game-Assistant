#!/usr/bin/env python3
from __future__ import annotations

"""
adapter_d4dj.py (FULL REPLACEMENT - v2 normalized)

UMI Phase 3 adapter for d4dj Groovy Mix.

Grounding
---------
Observed chart text structure:
- whitespace-delimited plain text
- named sections such as:
  MusicName, SoflanDataList, BarLineList, NoteDataList
- NoteDataList entries are key/value sequences including:
  LaneId, Type, Time, NextId, Direction, EffectType, EffectParameter

Scope
-----
- structural normalization only
- no gameplay inference
- no validator imports
- no registry lookups
- no persistence
- preserve original chart tokens in extra
"""

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

GAME_ID = "d4dj"
_ADAPTER_ID = "adapter_d4dj"
_ADAPTER_VERSION = "2.0.0"
_SECTION_VERSION = canonical_sections_version(GAME_ID, "adapter_d4dj", "v2")

# Canonical kinds currently emitted by this adapter
# (chosen to stay within canonical payload schema)
_CANONICAL_KINDS = {
    "tap",
    "flick_arrow",
    "hold_body_or_start",
    "hold_path",
}


# ---------------------------------------------------------------------
# Raw ingestion structure
# ---------------------------------------------------------------------

@dataclass
class D4DJIngestRaw:
    chart_path: Path
    chart_id: str


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _infer_chart_id(path: Path) -> str:
    return path.stem


def _infer_title(path: Path) -> str:
    return path.stem.strip() or path.name


def _safe_int(x: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        if x is None:
            return default
        return int(float(x))
    except Exception:
        return default


def _safe_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _lane_from_lane_id(lane_id: int) -> int:
    # Chart uses 0-based lane id; canonical row/payload expect positive-int style lanes.
    return int(lane_id) + 1


# ---------------------------------------------------------------------
# Raw parser
# ---------------------------------------------------------------------

def _parse_chart_tokens(text: str) -> Dict[str, Any]:
    """
    Parse a d4dj text chart into structured blocks.

    Returns:
      {
        "music_name": Optional[str],
        "soflan": list[{time, time_scale, left_right}],
        "bar_lines": list[float],
        "bar_line_meta": Optional[int],
        "notes": list[dict],
      }
    """
    tokens = text.split()
    i = 0
    music_name: Optional[str] = None
    soflan: List[Dict[str, Any]] = []
    bar_lines: List[float] = []
    bar_line_meta: Optional[int] = None
    notes: List[Dict[str, Any]] = []

    def peek(offset: int = 0) -> Optional[str]:
        j = i + offset
        if 0 <= j < len(tokens):
            return tokens[j]
        return None

    while i < len(tokens):
        t = tokens[i]

        if t == "MusicName":
            music_name = peek(1)
            i += 2
            continue

        if t == "SoflanDataList":
            i += 1
            while i < len(tokens):
                if tokens[i] in ("BarLineList", "NoteDataList"):
                    break
                if tokens[i] != "Time":
                    i += 1
                    continue

                time_v = _safe_float(peek(1), None)
                ts = None
                lr = None

                if peek(2) == "TimeScale":
                    ts = _safe_float(peek(3), None)
                if peek(4) == "LeftRight":
                    lr = _safe_int(peek(5), None)

                if time_v is not None:
                    soflan.append(
                        {
                            "time": float(time_v),
                            "time_scale": ts,
                            "left_right": lr,
                        }
                    )
                i += 6
            continue

        if t == "BarLineList":
            i += 1

            if i < len(tokens):
                first_int = _safe_int(tokens[i], None)
                second_float = _safe_float(peek(1), None)
                if first_int is not None and second_float is not None:
                    bar_line_meta = int(first_int)
                    i += 1

            while i < len(tokens):
                if tokens[i] == "NoteDataList":
                    break
                v = _safe_float(tokens[i], None)
                if v is not None:
                    bar_lines.append(float(v))
                i += 1
            continue

        if t == "NoteDataList":
            i += 1
            while i < len(tokens):
                if tokens[i] != "LaneId":
                    i += 1
                    continue

                lane_id = _safe_int(peek(1), None)
                if peek(2) != "Type":
                    i += 1
                    continue

                note_type = peek(3)

                if peek(4) != "Time":
                    i += 1
                    continue
                time_v = _safe_float(peek(5), None)

                if peek(6) != "NextId":
                    i += 1
                    continue
                next_id = _safe_int(peek(7), 0) or 0

                if peek(8) != "Direction":
                    i += 1
                    continue
                direction = _safe_int(peek(9), 0) or 0

                if peek(10) != "EffectType":
                    i += 1
                    continue
                effect_type = _safe_int(peek(11), 0) or 0

                if peek(12) != "EffectParameter":
                    i += 1
                    continue
                effect_param = _safe_float(peek(13), 0.0) or 0.0

                if lane_id is None or note_type is None or time_v is None:
                    i += 14
                    continue

                notes.append(
                    {
                        "lane_id": int(lane_id),
                        "type": str(note_type),
                        "time": float(time_v),
                        "next_id": int(next_id),
                        "direction": int(direction),
                        "effect_type": int(effect_type),
                        "effect_parameter": float(effect_param),
                    }
                )
                i += 14
            continue

        i += 1

    return {
        "music_name": music_name,
        "soflan": soflan,
        "bar_lines": bar_lines,
        "bar_line_meta": bar_line_meta,
        "notes": notes,
    }


# ---------------------------------------------------------------------
# Canonical kind mapping
# ---------------------------------------------------------------------

def _kind_for_type(note_type: str) -> str:
    """
    Conservative canonical mapping.

    Mapping policy:
    - Tap1 / Tap2 -> tap
    - ScratchLeft / ScratchRight -> flick_arrow
    - Slide -> hold_path
    - LongStart / StopStart -> hold_body_or_start
    - other / fallback -> tap

    Original note type is always preserved in extra['raw_type'].
    """
    if note_type in ("Tap1", "Tap2"):
        return "tap"
    if note_type in ("ScratchLeft", "ScratchRight"):
        return "flick_arrow"
    if note_type == "Slide":
        return "hold_path"
    if note_type in ("LongStart", "StopStart"):
        return "hold_body_or_start"
    return "tap"


# ---------------------------------------------------------------------
# Payload builder
# ---------------------------------------------------------------------

def build_canonical_payload_d4dj(source_ref: str) -> Dict[str, Any]:
    path = Path(source_ref)
    text = path.read_text(encoding="utf-8", errors="ignore")

    parsed = _parse_chart_tokens(text)
    notes = parsed["notes"]

    indexed: List[Dict[str, Any]] = list(notes)
    consumed_end_indices: set[int] = set()

    note_events: List[Dict[str, Any]] = []

    def note_at(idx: int) -> Optional[Dict[str, Any]]:
        if 0 <= idx < len(indexed):
            return indexed[idx]
        return None

    for idx, n in enumerate(indexed):
        ntype = str(n.get("type") or "")
        t = _safe_float(n.get("time"), None)
        if t is None:
            continue

        lane_id_raw = _safe_int(n.get("lane_id"), None)
        if lane_id_raw is None:
            continue

        next_id = int(n.get("next_id") or 0)

        # Pair long-note starts with end when possible
        if ntype in ("LongStart", "StopStart"):
            end = note_at(next_id)
            duration = None
            if isinstance(end, dict):
                end_type = str(end.get("type") or "")
                end_time = _safe_float(end.get("time"), None)
                if end_time is not None and end_time >= t and end_type in ("LongEnd", "StopEnd"):
                    duration = float(end_time - t)
                    consumed_end_indices.add(next_id)

            extra: Dict[str, Any] = {
                "raw_type": ntype,
                "time_raw": n.get("time"),
                "lane_id_raw": lane_id_raw,
                "next_id": next_id,
                "direction": int(n.get("direction") or 0),
                "effect_type": int(n.get("effect_type") or 0),
                "effect_parameter": float(n.get("effect_parameter") or 0.0),
            }

            if duration is not None:
                extra["duration_seconds"] = duration
                extra["rect_height"] = duration
                extra["shape"] = "hold"
                extra["end_index"] = next_id
                if isinstance(end, dict):
                    extra["end_time_raw"] = end.get("time")
                    extra["end_type"] = end.get("type")
            else:
                extra["duration_seconds"] = 0.0

            note_events.append(
                {
                    "time_beats": float(t),  # kept in source time unit intentionally
                    "lane": _lane_from_lane_id(lane_id_raw),
                    "kind": "hold_body_or_start",
                    "extra": extra,
                }
            )
            continue

        # Skip consumed end markers
        if idx in consumed_end_indices and ntype in ("LongEnd", "StopEnd"):
            continue

        kind = _kind_for_type(ntype)

        extra: Dict[str, Any] = {
            "raw_type": ntype,
            "time_raw": n.get("time"),
            "lane_id_raw": lane_id_raw,
            "next_id": next_id,
            "direction": int(n.get("direction") or 0),
            "effect_type": int(n.get("effect_type") or 0),
            "effect_parameter": float(n.get("effect_parameter") or 0.0),
        }

        if ntype in ("ScratchLeft", "ScratchRight"):
            extra["scratch_side"] = "left" if ntype.endswith("Left") else "right"

        if ntype == "Slide":
            extra["shape"] = "slide"

        note_events.append(
            {
                "time_beats": float(t),
                "lane": _lane_from_lane_id(lane_id_raw),
                "kind": kind,
                "extra": extra,
            }
        )

    # Stable sort
    note_events.sort(
        key=lambda ev: (
            float(ev.get("time_beats", 0.0)),
            int(ev.get("lane", 0)),
            str(ev.get("kind", "")),
        )
    )

    max_time = 0.0
    for ev in note_events:
        tb = ev.get("time_beats")
        if isinstance(tb, (int, float)):
            max_time = max(max_time, float(tb))

    chart_meta: Dict[str, Any] = {
        "bpm": None,
        "max_time_beats": max_time,
        "time_unit": "seconds",
    }

    if parsed.get("music_name"):
        chart_meta["music_name"] = parsed.get("music_name")
    if parsed.get("bar_line_meta") is not None:
        chart_meta["bar_line_meta"] = parsed.get("bar_line_meta")
    if parsed.get("bar_lines"):
        chart_meta["bar_lines"] = parsed.get("bar_lines")
    if parsed.get("soflan"):
        chart_meta["soflan_events"] = parsed.get("soflan")

    adapter_metadata: Dict[str, Any] = {
        "adapter_id": _ADAPTER_ID,
        "adapter_version": _ADAPTER_VERSION,
        "source_format": "d4dj_txt",
        "source_path": str(path),
        "notes": "d4dj adapter parsing plain-text chart with SoflanDataList/BarLineList/NoteDataList.",
    }

    diagnostics: Dict[str, Any] = {
        "note_events_count": len(note_events),
        "soflan_events_count": len(parsed.get("soflan") or []),
        "bar_lines_count": len(parsed.get("bar_lines") or []),
    }

    internal_metadata: Dict[str, Any] = build_internal_metadata(
        adapter_id=_ADAPTER_ID,
        adapter_version=_ADAPTER_VERSION,
        sections_source=None,
        notes="structural-only; no gameplay inference",
    )

    payload: Dict[str, Any] = {
        "game_id": GAME_ID,
        "chart_id": str(path.resolve()),
        "title": parsed.get("music_name") or _infer_title(path),
        "difficulty": "UNKNOWN",

        "note_events": note_events,
        "chart_meta": chart_meta,
        "adapter_metadata": adapter_metadata,
        "diagnostics": diagnostics,
        "internal_metadata": internal_metadata,

        # compatibility alias
        "song_id": _infer_chart_id(path),
    }

    return payload


# ---------------------------------------------------------------------
# Adapter class
# ---------------------------------------------------------------------

class D4DJAdapter(BaseAdapterV2):
    game_id = GAME_ID
    adapter_id = _ADAPTER_ID
    adapter_version = _ADAPTER_VERSION

    def accepts_file(self, path: Any) -> bool:
        p = Path(path)
        allowed = with_baseline_fallback_extensions(
            [".txt"],
            include_baseline=False,
        )
        return p.suffix.casefold() in allowed

    def load(self, path: Any) -> D4DJIngestRaw:
        p = Path(path)
        return D4DJIngestRaw(chart_path=p, chart_id=_infer_chart_id(p))

    def to_canonical_payload(self, source_ref: str) -> Dict[str, Any]:
        payload = build_canonical_payload_d4dj(source_ref)
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
                sections_source="d4dj-text",
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
        if isinstance(raw, D4DJIngestRaw):
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
            "note_model": "lane_based",
            "supports_sections": False,
            "supports_variable_bpm": True,
            "supports_soflan": True,
            "emits_canonical_payload": True,
            "source_format": "d4dj_txt",
            "canonical_kinds": list(_CANONICAL_KINDS),
        }


__all__ = [
    "D4DJAdapter",
    "D4DJIngestRaw",
    "build_canonical_payload_d4dj",
]