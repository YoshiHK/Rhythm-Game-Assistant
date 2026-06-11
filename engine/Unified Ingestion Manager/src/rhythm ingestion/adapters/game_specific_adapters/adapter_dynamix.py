#!/usr/bin/env python3
"""adapter_dynamix.py

UMI Phase 3 adapter for Dynamix.

Grounding (from in-repo tooling):
- <File>dynamix2dynamite.py</File> defines the XML shape written for a chart:
  - root <CMap>
  - meta tags: m_path, m_barPerMin, m_timeOffset, m_leftRegion, m_rightRegion, m_mapID
  - note blocks: m_notes (front), m_notesLeft, m_notesRight each containing an inner <m_notes>
    with repeated <CMapNoteAsset> children.
  - each CMapNoteAsset has: m_id, m_type, m_time, m_position, m_width, m_subId, status.
- <File>chart.py</File> defines the underlying 3-side model (LEFT/FRONT/RIGHT) and note types.

Scope (Phase 3 / ADAPTER_V2_SPEC):
- Structural normalization only.
- No tips generation, no gameplay semantics inference.
- Preserve raw fields in extra.

Time convention:
- The chart's native time axis is in BAR units (not seconds). We store it as time_beats.
- chart_meta includes time_unit='bars', bar_per_min, and time_offset.

Canonical payload ordering follows the project ordering convention.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base_adapter import BaseAdapter


# ----------------------------
# Raw structure
# ----------------------------

@dataclass
class DynamixIngestRaw:
    chart_path: Path
    chart_id: str
    difficulty: str


# ----------------------------
# Difficulty inference (aligned with dynamite.py)
# ----------------------------

_RE_CHART_NAME = re.compile(r"_(?P<diff>[BCNHMGTbcnhmgt])(?P<lv>_[0-9]+)?\.[Xx][Mm][Ll]$")


def _diff2name(letter: str) -> str:
    s = (letter or "").upper()
    if s in ("B", "C", "1"):
        return "CASUAL"
    if s in ("N", "2"):
        return "NORMAL"
    if s in ("H", "3"):
        return "HARD"
    if s in ("M", "4"):
        return "MEGA"
    if s in ("G", "5"):
        return "GIGA"
    if s in ("T", "6"):
        return "TERA"
    return "TUTORIAL"


def _infer_chart_id_and_difficulty(path: Path) -> Tuple[str, str]:
    stem = path.stem
    m = _RE_CHART_NAME.search(path.name)
    if m:
        diff = _diff2name(m.group("diff"))
        # chart_id uses stem to remain stable
        return stem, diff
    return stem, "UNKNOWN"


# ----------------------------
# Parsing helpers
# ----------------------------

_SIDE_LEFT = -1
_SIDE_FRONT = 0
_SIDE_RIGHT = 1

_REGION_TYPES = {"MULTI", "MIXER", "PAD"}

_NOTE_TYPES = {"NORMAL", "CHAIN", "HOLD", "SUB"}


def _safe_int(x: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        if x is None:
            return default
        return int(str(x).strip())
    except Exception:
        try:
            return int(float(x))
        except Exception:
            return default


def _safe_float(x: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if x is None:
            return default
        return float(str(x).strip())
    except Exception:
        return default


def _text(el: Optional[ET.Element]) -> Optional[str]:
    if el is None:
        return None
    if el.text is None:
        return None
    return el.text.strip()


def _find_child(parent: ET.Element, name: str) -> Optional[ET.Element]:
    for ch in list(parent):
        if ch.tag == name:
            return ch
    return None


def _findall_children(parent: ET.Element, name: str) -> List[ET.Element]:
    return [ch for ch in list(parent) if ch.tag == name]


def _lane_bucket(side: int, position: float) -> int:
    """Create a stable positive integer bucket from (side, position).

    Dynamix uses continuous horizontal positions; canonical lane must be int.
    We quantize position at 0.01 units and offset by side.
    """
    # quantize: 0.01 unit resolution
    q = int(round(float(position) * 100.0))
    # offset by side to avoid collisions
    # side: -1,0,1 -> base: 100000,200000,300000
    base = (side + 2) * 100000
    return int(base + q)


def _kind_for_note_type(ntype: str) -> str:
    # Structural mapping, grounded by chart.py naming and wave-1 docs:
    # - NORMAL corresponds to tap notes.
    # - CHAIN corresponds to the second note family (editor calls it Slide).
    # - HOLD start/end becomes hold_path.
    t = (ntype or "").upper()
    if t == "NORMAL":
        return "tap"
    if t == "CHAIN":
        return "slide"
    if t == "HOLD":
        return "hold_path"
    return "tap"


def parse_dynamix_xml(path: Path) -> Dict[str, Any]:
    """Parse a Dynamix chart xml file into meta + region note lists."""
    root = ET.parse(path).getroot()

    # Meta
    meta: Dict[str, Any] = {
        "path": _text(_find_child(root, "m_path")),
        "bar_per_min": _safe_float(_text(_find_child(root, "m_barPerMin")), None),
        "time_offset": _safe_float(_text(_find_child(root, "m_timeOffset")), None),
        "left_region": _text(_find_child(root, "m_leftRegion")),
        "right_region": _text(_find_child(root, "m_rightRegion")),
        "map_id": _text(_find_child(root, "m_mapID")),
    }

    def parse_region(tag: str) -> List[Dict[str, Any]]:
        outer = _find_child(root, tag)
        if outer is None:
            return []
        inner = _find_child(outer, "m_notes")
        if inner is None:
            return []
        out: List[Dict[str, Any]] = []
        for asset in _findall_children(inner, "CMapNoteAsset"):
            rid = _safe_int(_text(_find_child(asset, "m_id")), None)
            rtype = _text(_find_child(asset, "m_type"))
            rtime = _safe_float(_text(_find_child(asset, "m_time")), None)
            rpos = _safe_float(_text(_find_child(asset, "m_position")), None)
            rwidth = _safe_float(_text(_find_child(asset, "m_width")), None)
            rsub = _safe_int(_text(_find_child(asset, "m_subId")), None)
            rstatus = _text(_find_child(asset, "status"))
            if rid is None or rtype is None or rtime is None or rpos is None or rwidth is None:
                continue
            out.append({
                "id": int(rid),
                "type": str(rtype),
                "time": float(rtime),
                "position": float(rpos),
                "width": float(rwidth),
                "sub_id": int(rsub) if rsub is not None else -1,
                "status": rstatus,
            })
        return out

    bottom = parse_region("m_notes")
    left = parse_region("m_notesLeft")
    right = parse_region("m_notesRight")

    return {
        "meta": meta,
        "bottom": bottom,
        "left": left,
        "right": right,
    }


# ----------------------------
# Payload builder
# ----------------------------


def build_canonical_payload_dynamix(source_ref: str) -> Dict[str, Any]:
    path = Path(source_ref)
    parsed = parse_dynamix_xml(path)
    meta = parsed["meta"]

    # Collect all notes with side
    all_notes: List[Dict[str, Any]] = []
    for n in parsed["bottom"]:
        nn = dict(n)
        nn["side"] = _SIDE_FRONT
        all_notes.append(nn)
    for n in parsed["left"]:
        nn = dict(n)
        nn["side"] = _SIDE_LEFT
        all_notes.append(nn)
    for n in parsed["right"]:
        nn = dict(n)
        nn["side"] = _SIDE_RIGHT
        all_notes.append(nn)

    # Build id->note map for hold pairing
    by_id: Dict[int, Dict[str, Any]] = {int(n["id"]): n for n in all_notes if isinstance(n.get("id"), int)}

    consumed: set[int] = set()
    note_events: List[Dict[str, Any]] = []

    for n in all_notes:
        nid = int(n["id"])
        if nid in consumed:
            continue

        ntype = str(n.get("type") or "").upper()
        side = int(n.get("side") or 0)
        t = float(n.get("time"))
        pos = float(n.get("position"))
        width = float(n.get("width"))
        sub_id = int(n.get("sub_id") if n.get("sub_id") is not None else -1)

        # HOLD start pairs to SUB end via sub_id
        if ntype == "HOLD" and sub_id is not None and sub_id >= 0:
            end = by_id.get(int(sub_id))
            end_time = None
            if isinstance(end, dict) and str(end.get("type") or "").upper() == "SUB":
                end_time = _safe_float(end.get("time"), None)
            duration = None
            if end_time is not None and float(end_time) >= t:
                duration = float(end_time) - t
                consumed.add(int(sub_id))

            extra: Dict[str, Any] = {
                "raw_type": ntype,
                "id": nid,
                "sub_id": sub_id,
                "side": side,
                "position": pos,
                "width": width,
                "status": n.get("status"),
            }
            if end_time is not None:
                extra["end_time"] = float(end_time)
            if duration is not None:
                extra["duration_bars"] = duration
                extra["rect_height"] = duration
                extra["shape"] = "hold"
            else:
                extra["duration_bars"] = 0.0

            note_events.append({
                "time_beats": t,
                "lane": _lane_bucket(side, pos),
                "kind": "hold_path",
                "extra": extra,
            })
            continue

        # Skip SUB end notes if not consumed by pairing
        if ntype == "SUB":
            # keep as a structural marker (rare); map to tap
            kind = "tap"
        else:
            kind = _kind_for_note_type(ntype)

        extra: Dict[str, Any] = {
            "raw_type": ntype,
            "id": nid,
            "sub_id": sub_id,
            "side": side,
            "position": pos,
            "width": width,
            "status": n.get("status"),
        }

        note_events.append({
            "time_beats": t,
            "lane": _lane_bucket(side, pos),
            "kind": kind,
            "extra": extra,
        })

    # Stable sort
    note_events.sort(key=lambda ev: (float(ev.get("time_beats", 0.0)), int(ev.get("lane", 0)), str(ev.get("kind", ""))))

    # max_time_beats based on holds too
    max_time = 0.0
    for ev in note_events:
        tb = ev.get("time_beats")
        if isinstance(tb, (int, float)):
            max_time = max(max_time, float(tb))
        ex = ev.get("extra")
        if isinstance(ex, dict) and isinstance(ex.get("end_time"), (int, float)):
            max_time = max(max_time, float(ex.get("end_time")))

    bar_per_min = meta.get("bar_per_min")
    time_offset = meta.get("time_offset")

    chart_meta: Dict[str, Any] = {
        # bpm is used as a tempo scalar by downstream components; Dynamix native value is bar_per_min.
        "bpm": float(bar_per_min) if isinstance(bar_per_min, (int, float)) else 0.0,
        "bar_per_min": bar_per_min,
        "time_offset": time_offset,
        "time_unit": "bars",
        "max_time_beats": max_time,
        "left_region": meta.get("left_region"),
        "right_region": meta.get("right_region"),
        "map_id": meta.get("map_id"),
        "path": meta.get("path"),
        "tempo_semantics": "bar_per_min",
    }

    adapter_metadata: Dict[str, Any] = {
        "adapter_id": "adapter_dynamix",
        "adapter_version": "1.0.0",
        "source_format": "dynamix_xml",
        "source_path": str(path),
        "notes": "Dynamix adapter parsing CMap XML (m_notes/m_notesLeft/m_notesRight) into canonical note_events.",
    }

    diagnostics: Dict[str, Any] = {
        "note_events_count": len(note_events),
        "holds_paired": len([1 for ev in note_events if ev.get("kind") == "hold_path" and isinstance(ev.get("extra"), dict) and float(ev["extra"].get("duration_bars", 0.0)) > 0]),
        "time_unit": "bars",
    }

    internal_metadata: Dict[str, Any] = {
        "adapter_id": adapter_metadata.get("adapter_id"),
        "adapter_version": adapter_metadata.get("adapter_version"),
        "sections_source": None,
    }

    _, inferred_diff = _infer_chart_id_and_difficulty(path)

    payload: Dict[str, Any] = {
        "game_id": "dynamix",
        "chart_id": str(path),
        "difficulty": inferred_diff,

        "note_events": note_events,
        "chart_meta": chart_meta,
        "adapter_metadata": adapter_metadata,
        "diagnostics": diagnostics,
        "internal_metadata": internal_metadata,
        # sections optional
    }

    return payload


# ----------------------------
# Adapter class
# ----------------------------


class DynamixAdapter(BaseAdapter):
    game_id = "dynamix"

    def accepts_file(self, path: Path) -> bool:
        return path.suffix.lower() in {".xml"}

    def load(self, path: Path) -> DynamixIngestRaw:
        chart_id, diff = _infer_chart_id_and_difficulty(path)
        return DynamixIngestRaw(chart_path=path, chart_id=chart_id, difficulty=diff)

    def to_canonical_payload(self, source_ref: str) -> Dict[str, Any]:
        return build_canonical_payload_dynamix(source_ref)

    def to_canonical_row(self, raw: DynamixIngestRaw) -> Dict[str, Any]:
        payload = self.to_canonical_payload(str(raw.chart_path))
        note_events = payload.get("note_events") or []
        note_total_chart = len(note_events) if isinstance(note_events, list) else 0
        chart_meta = payload.get("chart_meta") or {}
        return {
            "game": self.game_id,
            "song_id": raw.chart_id,
            "difficulty_label": payload.get("difficulty") or raw.difficulty or "UNKNOWN",
            "note_total_chart": int(note_total_chart),
            "duration_ms": None,
            "bpm": chart_meta.get("bpm"),
            "chart_path": str(raw.chart_path),
        }

    def capabilities(self) -> dict:
        return {
            "note_model": "spatial",
            "supports_sections": False,
            "supports_variable_bpm": False,
            "supports_bpm_changes": False,
            "supports_width": True,
            "supports_sides": True,
            "emits_canonical_payload": True,
            "source_format": "dynamix_xml",
        }


__all__ = [
    "DynamixAdapter",
    "DynamixIngestRaw",
    "build_canonical_payload_dynamix",
    "parse_dynamix_xml",
]
