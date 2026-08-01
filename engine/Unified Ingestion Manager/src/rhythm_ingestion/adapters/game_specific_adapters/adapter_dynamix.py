#!/usr/bin/env python3
from __future__ import annotations

"""
adapter_dynamix.py (FULL REPLACEMENT - v2 normalized)

UMI Phase 3 adapter for Dynamix.

Grounding
---------
Observed / documented Dynamix XML shape:
- root: <CMap>
- meta tags:
  m_path, m_barPerMin, m_timeOffset, m_leftRegion, m_rightRegion, m_mapID
- note blocks:
  m_notes (front), m_notesLeft, m_notesRight
- each contains inner <m_notes> with repeated <CMapNoteAsset>
- each CMapNoteAsset includes:
  m_id, m_type, m_time, m_position, m_width, m_subId, status

Scope
-----
- structural normalization only
- no gameplay inference
- no validator imports
- no persistence
- no verification
- preserve raw fields in extra

Time convention
---------------
- native chart time axis is in BAR units
- canonical payload stores that native unit in time_beats for stable ordering
- chart_meta includes:
  time_unit='bars', bar_per_min, time_offset
"""

import re
import xml.etree.ElementTree as ET
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

GAME_ID = "dynamix"
_ADAPTER_ID = "adapter_dynamix"
_ADAPTER_VERSION = "2.0.0"
_SECTION_VERSION = canonical_sections_version(GAME_ID, "adapter_dynamix", "v2")

# Difficulty inference aligned to observed naming conventions
_RE_CHART_NAME = re.compile(r"_(?P<diff>[BCNHMGTbcnhmgt])(?P<lv>_[0-9]+)?\.[Xx][Mm][Ll]$")

_SIDE_LEFT = -1
_SIDE_FRONT = 0
_SIDE_RIGHT = 1

_REGION_TYPES = {"MULTI", "MIXER", "PAD"}
_NOTE_TYPES = {"NORMAL", "CHAIN", "HOLD", "SUB"}

# Canonical subset currently emitted by this adapter
_CANONICAL_KINDS = {
    "tap",
    "hold_body_or_start",
    "hold_path",
}


# ---------------------------------------------------------------------
# Raw ingestion structure
# ---------------------------------------------------------------------

@dataclass
class DynamixIngestRaw:
    chart_path: Path
    chart_id: str
    difficulty: str


# ---------------------------------------------------------------------
# Difficulty inference
# ---------------------------------------------------------------------

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
        return stem, diff
    return stem, "UNKNOWN"


def _infer_title(path: Path) -> str:
    return path.stem.strip() or path.name


# ---------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------

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
    """
    Create a stable positive integer bucket from (side, position).

    Dynamix uses continuous horizontal positions; canonical lane must be int.
    We quantize position at 0.01 units and offset by side.
    """
    q = int(round(float(position) * 100.0))
    base = (side + 2) * 100000  # side: -1/0/1 -> 100000 / 200000 / 300000
    return int(base + q)


def _kind_for_note_type(ntype: str) -> str:
    """
    Conservative canonical mapping.

    Mapping policy:
    - NORMAL -> tap
    - CHAIN -> hold_path
    - HOLD  -> hold_body_or_start (paired structural hold start)
    - SUB   -> tap (rare structural marker if unpaired)

    Original type is always preserved in extra['raw_type'].
    """
    t = (ntype or "").upper()
    if t == "NORMAL":
        return "tap"
    if t == "CHAIN":
        return "hold_path"
    if t == "HOLD":
        return "hold_body_or_start"
    return "tap"


# ---------------------------------------------------------------------
# XML parser
# ---------------------------------------------------------------------

def parse_dynamix_xml(path: Path) -> Dict[str, Any]:
    """
    Parse a Dynamix chart xml file into meta + region note lists.
    """
    root = ET.parse(path).getroot()

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

            out.append(
                {
                    "id": int(rid),
                    "type": str(rtype),
                    "time": float(rtime),
                    "position": float(rpos),
                    "width": float(rwidth),
                    "sub_id": int(rsub) if rsub is not None else -1,
                    "status": rstatus,
                }
            )
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


# ---------------------------------------------------------------------
# Payload builder
# ---------------------------------------------------------------------

def build_canonical_payload_dynamix(source_ref: str) -> Dict[str, Any]:
    path = Path(source_ref)
    parsed = parse_dynamix_xml(path)
    meta = parsed["meta"]

    # Collect all note objects with side tag
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

    by_id: Dict[int, Dict[str, Any]] = {
        int(n["id"]): n for n in all_notes if isinstance(n.get("id"), int)
    }

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

        # Pair HOLD start -> SUB end when available
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

            note_events.append(
                {
                    "time_beats": t,
                    "lane": _lane_bucket(side, pos),
                    "kind": "hold_body_or_start",
                    "extra": extra,
                }
            )
            continue

        # Skip SUB notes already used as paired ends
        if idx := int(nid) in consumed and ntype == "SUB":
            continue

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

        # CHAIN preserved as structural path note
        if ntype == "CHAIN":
            extra["shape"] = "chain"

        note_events.append(
            {
                "time_beats": t,
                "lane": _lane_bucket(side, pos),
                "kind": kind,
                "extra": extra,
            }
        )

    # Stable order
    note_events.sort(
        key=lambda ev: (
            float(ev.get("time_beats", 0.0)),
            int(ev.get("lane", 0)),
            str(ev.get("kind", "")),
        )
    )

    # max_time_beats includes hold end time if present
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
        # downstream still expects a numeric tempo field; preserve Dynamix-native meaning explicitly
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
        "adapter_id": _ADAPTER_ID,
        "adapter_version": _ADAPTER_VERSION,
        "source_format": "dynamix_xml",
        "source_path": str(path),
        "notes": "Dynamix adapter parsing CMap XML sides into canonical note_events.",
    }

    diagnostics: Dict[str, Any] = {
        "note_events_count": len(note_events),
        "holds_paired": len(
            [
                1
                for ev in note_events
                if ev.get("kind") == "hold_body_or_start"
                and isinstance(ev.get("extra"), dict)
                and float(ev["extra"].get("duration_bars", 0.0)) > 0
            ]
        ),
        "time_unit": "bars",
    }

    internal_metadata: Dict[str, Any] = build_internal_metadata(
        adapter_id=_ADAPTER_ID,
        adapter_version=_ADAPTER_VERSION,
        sections_source=None,
        notes="structural-only; no gameplay inference",
    )

    _, inferred_diff = _infer_chart_id_and_difficulty(path)

    payload: Dict[str, Any] = {
        "game_id": GAME_ID,
        "chart_id": str(path.resolve()),
        "title": meta.get("map_id") or _infer_title(path),
        "difficulty": inferred_diff,

        "note_events": note_events,
        "chart_meta": chart_meta,
        "adapter_metadata": adapter_metadata,
        "diagnostics": diagnostics,
        "internal_metadata": internal_metadata,

        # compatibility alias
        "song_id": path.stem,
    }

    return payload


# ---------------------------------------------------------------------
# Adapter class
# ---------------------------------------------------------------------

class DynamixAdapter(BaseAdapterV2):
    game_id = GAME_ID
    adapter_id = _ADAPTER_ID
    adapter_version = _ADAPTER_VERSION

    def accepts_file(self, path) -> bool:
        p = Path(path)
        allowed = with_baseline_fallback_extensions(
            [".xml"],
            include_baseline=False,
        )
        return p.suffix.casefold() in allowed

    def load(self, path) -> DynamixIngestRaw:
        p = Path(path)
        chart_id, difficulty = _infer_chart_id_and_difficulty(p)
        return DynamixIngestRaw(
            chart_path=p,
            chart_id=chart_id,
            difficulty=difficulty,
        )

    def to_canonical_payload(self, source_ref: str) -> Dict[str, Any]:
        payload = build_canonical_payload_dynamix(source_ref)
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
                sections_source="dynamix-xml",
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

    def to_canonical_row(self, raw) -> Dict[str, Any]:
        if isinstance(raw, DynamixIngestRaw):
            payload = self.to_canonical_payload(str(raw.chart_path))
            chart_path = str(raw.chart_path)
            song_id = raw.chart_id
            difficulty = raw.difficulty
        elif isinstance(raw, dict):
            payload = raw
            chart_path = str(raw.get("chart_id") or raw.get("source_path") or "")
            song_id = payload.get("song_id")
            difficulty = payload.get("difficulty") or "UNKNOWN"
        else:
            chart_path = str(raw)
            payload = self.to_canonical_payload(chart_path)
            song_id, difficulty = _infer_chart_id_and_difficulty(Path(chart_path))

        if not isinstance(payload, dict):
            payload = {}

        note_events = payload.get("note_events")
        if not isinstance(note_events, list):
            note_events = []

        chart_meta = payload.get("chart_meta")
        if not isinstance(chart_meta, dict):
            chart_meta = {}

        title = payload.get("title") or _infer_title(Path(chart_path)) if chart_path else None
        difficulty = payload.get("difficulty") or difficulty or "UNKNOWN"

        # Native unit is bars; estimate duration only if bar_per_min is known
        duration_ms = None
        max_time_bars = chart_meta.get("max_time_beats")
        bar_per_min = chart_meta.get("bar_per_min")
        if isinstance(max_time_bars, (int, float)) and isinstance(bar_per_min, (int, float)) and float(bar_per_min) > 0:
            try:
                duration_ms = int(float(max_time_bars) * 60000.0 / float(bar_per_min))
            except Exception:
                duration_ms = None

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
            "duration_ms": duration_ms,
            "bpm": chart_meta.get("bpm"),
            "rating_raw": None,
            "chart_path": chart_path,
        }

    def capabilities(self) -> dict:
        return {
            "note_model": "spatial_three_side",
            "supports_sections": False,
            "supports_variable_bpm": True,
            "supports_xml": True,
            "emits_canonical_payload": True,
            "source_format": "dynamix_xml",
            "time_unit": "bars",
            "canonical_kinds": list(_CANONICAL_KINDS),
        }


__all__ = [
    "DynamixAdapter",
    "DynamixIngestRaw",
    "build_canonical_payload_dynamix",
    "parse_dynamix_xml",
]