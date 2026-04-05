#!/usr/bin/env python3
"""adapter_D4DJ.py

UMI Phase 3 adapter for D4DJ Groovy Mix.

Grounding (from an observed chart text file):
- The chart file is a whitespace-delimited plain text document.
- It contains named sections such as: MusicName, SoflanDataList, BarLineList, NoteDataList.
- NoteDataList entries are key/value sequences including:
  LaneId, Type, Time, NextId, Direction, EffectType, EffectParameter.

Scope (Phase 3 / ADAPTER_V2_SPEC):
- Structural normalization only.
- No gameplay semantics inference.
- Preserve original fields in extra.

Canonical payload ordering follows the project ordering convention.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base_adapter import BaseAdapter


@dataclass
class D4DJIngestRaw:
    chart_path: Path
    chart_id: str


def _infer_chart_id(path: Path) -> str:
    return path.stem


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
    # Chart uses 0-based lane id; canonical requires positive int.
    return int(lane_id) + 1


def _parse_chart_tokens(text: str) -> Dict[str, Any]:
    """Parse a D4DJ chart txt into structured blocks.

    Returns keys:
      - music_name: Optional[str]
      - soflan: list[{time, time_scale, left_right}]
      - bar_lines: list[float]
      - bar_line_meta: Optional[int] (first numeric token after BarLineList if it is int-like)
      - notes: list[dict] with fields found in NoteDataList
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
            # Parse repeating groups: Time <f> TimeScale <f> LeftRight <i>
            while i < len(tokens):
                if tokens[i] in ("BarLineList", "NoteDataList"):
                    break
                if tokens[i] != "Time":
                    i += 1
                    continue
                time_v = _safe_float(peek(1), None)
                # expect TimeScale next
                ts = None
                lr = None
                if peek(2) == "TimeScale":
                    ts = _safe_float(peek(3), None)
                if peek(4) == "LeftRight":
                    lr = _safe_int(peek(5), None)
                if time_v is not None:
                    soflan.append({
                        "time": float(time_v),
                        "time_scale": ts,
                        "left_right": lr,
                    })
                i += 6
            continue

        if t == "BarLineList":
            i += 1
            # BarLineList appears followed by a numeric meta token then many times
            # We treat the first token as meta if it parses cleanly as int and the next parses as float.
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
            # Parse repeating key/value sequence.
            # Expected fields in each entry: LaneId <i> Type <s> Time <f> NextId <i> Direction <i> EffectType <i> EffectParameter <f>
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

                notes.append({
                    "lane_id": int(lane_id),
                    "type": str(note_type),
                    "time": float(time_v),
                    "next_id": int(next_id),
                    "direction": int(direction),
                    "effect_type": int(effect_type),
                    "effect_parameter": float(effect_param),
                })
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


def _kind_for_type(note_type: str) -> str:
    # Conservative mapping. Preserve original type in extra['raw_type'] always.
    if note_type in ("Tap1", "Tap2"):
        return "tap"
    if note_type in ("ScratchLeft", "ScratchRight"):
        return "scratch"
    if note_type == "Slide":
        return "slide"
    if note_type in ("LongStart", "StopStart"):
        return "hold_path"
    # End markers are usually consumed when pairing; if present, keep as tap-like marker.
    return "tap"


def build_canonical_payload_D4DJ(source_ref: str) -> Dict[str, Any]:
    path = Path(source_ref)
    text = path.read_text(encoding="utf-8", errors="ignore")

    parsed = _parse_chart_tokens(text)
    notes = parsed["notes"]

    # Index records to allow NextId pairing (NextId appears to reference note index).
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

        # Pair LongStart->LongEnd and StopStart->StopEnd into one hold_path event.
        if ntype in ("LongStart", "StopStart"):
            end = note_at(next_id)
            duration = None
            if isinstance(end, dict):
                end_type = str(end.get("type") or "")
                end_time = _safe_float(end.get("time"), None)
                if end_time is not None and end_time >= t and end_type in ("LongEnd", "StopEnd"):
                    duration = float(end_time - t)
                    consumed_end_indices.add(next_id)

            kind = "hold_path"
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
                # duration missing; keep as structural hold start marker
                extra["duration_seconds"] = 0.0

            note_events.append({
                "time_beats": float(t),  # time unit is seconds; preserved in chart_meta
                "lane": _lane_from_lane_id(lane_id_raw),
                "kind": kind,
                "extra": extra,
            })
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

        note_events.append({
            "time_beats": float(t),
            "lane": _lane_from_lane_id(lane_id_raw),
            "kind": kind,
            "extra": extra,
        })

    # Stable sort
    note_events.sort(key=lambda ev: (float(ev.get("time_beats", 0.0)), int(ev.get("lane", 0)), str(ev.get("kind", ""))))

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
        "adapter_id": "adapter_D4DJ",
        "adapter_version": "1.0.0",
        "source_format": "d4dj_txt",
        "source_path": str(path),
        "notes": "D4DJ adapter parsing plain-text chart with SoflanDataList/BarLineList/NoteDataList.",
    }

    diagnostics: Dict[str, Any] = {
        "note_events_count": len(note_events),
        "soflan_events_count": len(parsed.get("soflan") or []),
        "bar_lines_count": len(parsed.get("bar_lines") or []),
    }

    internal_metadata: Dict[str, Any] = {
        "adapter_id": adapter_metadata.get("adapter_id"),
        "adapter_version": adapter_metadata.get("adapter_version"),
        "sections_source": None,
    }

    payload: Dict[str, Any] = {
        "game_id": "D4DJ",
        "chart_id": str(path),
        "difficulty": "UNKNOWN",

        "note_events": note_events,
        "chart_meta": chart_meta,
        "adapter_metadata": adapter_metadata,
        "diagnostics": diagnostics,
        "internal_metadata": internal_metadata,
    }

    return payload


class D4DJAdapter(BaseAdapter):
    game_id = "D4DJ"

    def accepts_file(self, path: Path) -> bool:
        return path.suffix.lower() in {".txt"}

    def load(self, path: Path) -> D4DJIngestRaw:
        return D4DJIngestRaw(chart_path=path, chart_id=_infer_chart_id(path))

    def to_canonical_payload(self, source_ref: str) -> Dict[str, Any]:
        return build_canonical_payload_D4DJ(source_ref)

    def to_canonical_row(self, raw: D4DJIngestRaw) -> Dict[str, Any]:
        payload = self.to_canonical_payload(str(raw.chart_path))
        note_events = payload.get("note_events") or []
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
            "note_model": "lane_based",
            "supports_sections": False,
            "supports_variable_bpm": False,
            "emits_canonical_payload": True,
            "source_format": "d4dj_txt",
        }


__all__ = [
    "D4DJAdapter",
    "D4DJIngestRaw",
    "build_canonical_payload_D4DJ",
]
