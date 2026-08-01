#!/usr/bin/env python3
from __future__ import annotations

"""
adapter_proseka.py (FULL REPLACEMENT - v2 normalized)

UMI Phase 3 adapter for Proseka.

Responsibilities:
- Parse Proseka chart sources into a canonical payload
- Keep adapter import-safe even when optional detector / song DB helpers are absent
- Guarantee minimal payload contract before validator hand-off
- Preserve raw structure in `extra`
- NO gameplay semantics inference
- NO tips generation
"""

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..base_adapter_v2 import BaseAdapterV2
from ..common_adapter_utils import (
    attach_if_missing,
    build_internal_metadata,
    canonical_sections_version,
    with_baseline_fallback_extensions,
)

# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

GAME_ID = "proseka"
SECTION_METRICS_VERSION = canonical_sections_version(GAME_ID, "chart_visual_detector_merged", "v1")

_HINTS = (
    "project sekai",
    "proseka",
    "pjsekai",
    "colorful stage",
    "プロセカ",
)

_ALLOWED_EXTS = with_baseline_fallback_extensions([".html", ".mht"])

_CANONICAL_KINDS = {
    "tap",
    "critical_tap",
    "flick",
    "flick_arrow",
    "hold_body_or_start",
    "hold_path",
    "critical_hold_path",
}

_COMBO_RAW_TYPES = {
    "tap",
    "tap_critical",
    "hold_start",
    "hold_start_critical",
    "hold_end",
    "hold_end_critical",
    "hold_tick",
    "hold_tick_critical",
    "trace_tick",
    "trace_tick_critical",
    "flick",
    "flick_critical",
    "trace_flick",
    "trace_flick_critical",
}


# ---------------------------------------------------------------------
# Optional Song DB (lazy, non-blocking)
# ---------------------------------------------------------------------

def _try_get_song_db():
    """
    Lazy / optional Song DB loader.

    Returns:
        db-like object or None

    IMPORTANT:
    - This must never block adapter import or routing.
    - Keeps runtime safe even when ProsekaSongDb is unavailable.
    """
    try:
        from .proseka_song_db import ProsekaSongDb  # type: ignore
    except Exception:
        return None

    db_csv = Path(__file__).with_name("Proseka Song DB.csv")
    if not db_csv.exists():
        return None

    try:
        return ProsekaSongDb(str(db_csv))
    except Exception:
        return None


# ---------------------------------------------------------------------
# Raw ingestion structure
# ---------------------------------------------------------------------

@dataclass
class ProsekaIngestRaw:
    chart_path: Path
    song_id: str
    difficulty_name: str
    note_total_chart: Optional[int] = None


# ---------------------------------------------------------------------
# Proseka note typing
# ---------------------------------------------------------------------

class NoteEventType(str, Enum):
    TAP = "tap"
    TAP_CRITICAL = "tap_critical"

    HOLD_START = "hold_start"
    HOLD_START_CRITICAL = "hold_start_critical"
    HOLD_END = "hold_end"
    HOLD_END_CRITICAL = "hold_end_critical"
    HOLD_TICK = "hold_tick"
    HOLD_TICK_CRITICAL = "hold_tick_critical"
    HOLD_BODY_SEGMENT = "hold_body_segment"

    TRACE_BODY_SEGMENT = "trace_body_segment"
    TRACE_TICK = "trace_tick"
    TRACE_TICK_CRITICAL = "trace_tick_critical"
    TRACE_FLICK = "trace_flick"
    TRACE_FLICK_CRITICAL = "trace_flick_critical"

    FLICK = "flick"
    FLICK_CRITICAL = "flick_critical"


def classify_proseka_note(src: Dict[str, Any]) -> NoteEventType:
    note_type = src.get("type")
    is_critical = bool(src.get("is_critical"))

    if note_type == "tap":
        return NoteEventType.TAP_CRITICAL if is_critical else NoteEventType.TAP

    if note_type == "hold_start":
        return NoteEventType.HOLD_START_CRITICAL if is_critical else NoteEventType.HOLD_START
    if note_type == "hold_end":
        return NoteEventType.HOLD_END_CRITICAL if is_critical else NoteEventType.HOLD_END
    if note_type == "hold_tick":
        return NoteEventType.HOLD_TICK_CRITICAL if is_critical else NoteEventType.HOLD_TICK
    if note_type == "hold_body":
        return NoteEventType.HOLD_BODY_SEGMENT

    if note_type == "trace_body":
        return NoteEventType.TRACE_BODY_SEGMENT
    if note_type == "trace_tick":
        return NoteEventType.TRACE_TICK_CRITICAL if is_critical else NoteEventType.TRACE_TICK
    if note_type == "trace_flick":
        return NoteEventType.TRACE_FLICK_CRITICAL if is_critical else NoteEventType.TRACE_FLICK

    if note_type == "flick":
        return NoteEventType.FLICK_CRITICAL if is_critical else NoteEventType.FLICK

    return NoteEventType.TAP


def map_note_event_type_to_kind(t: NoteEventType) -> str:
    if t == NoteEventType.TAP:
        return "tap"
    if t == NoteEventType.TAP_CRITICAL:
        return "critical_tap"

    if t in (
        NoteEventType.HOLD_START,
        NoteEventType.HOLD_END,
        NoteEventType.HOLD_TICK,
        NoteEventType.TRACE_TICK,
    ):
        return "hold_body_or_start"

    if t in (
        NoteEventType.HOLD_START_CRITICAL,
        NoteEventType.HOLD_END_CRITICAL,
        NoteEventType.HOLD_TICK_CRITICAL,
        NoteEventType.TRACE_TICK_CRITICAL,
    ):
        return "critical_hold_path"

    if t in (NoteEventType.HOLD_BODY_SEGMENT, NoteEventType.TRACE_BODY_SEGMENT):
        return "hold_path"

    if t in (
        NoteEventType.TRACE_FLICK,
        NoteEventType.TRACE_FLICK_CRITICAL,
        NoteEventType.FLICK,
        NoteEventType.FLICK_CRITICAL,
    ):
        return "flick_arrow"

    return "tap"


def compute_combo_from_note_events(note_events: List[Dict[str, Any]]) -> int:
    combo = 0
    for ev in note_events:
        if not isinstance(ev, dict):
            continue
        extra = ev.get("extra")
        if not isinstance(extra, dict):
            continue
        raw_type = extra.get("raw_type")
        if raw_type in _COMBO_RAW_TYPES:
            combo += 1
    return combo


# ---------------------------------------------------------------------
# Path heuristics
# ---------------------------------------------------------------------

def _looks_like_proseka_path(path: Path) -> bool:
    s = str(path).replace("\\", "/").casefold()
    name = path.name.casefold()
    return any(h in s for h in _HINTS) or any(h in name for h in _HINTS)


def _infer_title_and_difficulty_from_filename(path: Path) -> Tuple[str, str]:
    """
    Examples:
      Beat Eater (APPEND 28) の譜面 - プロセカ練習場.html
      夜に駆ける (MASTER 30) の譜面 - プロセカ練習場.html
    """
    stem = path.stem.strip()

    # Remove common trailing hosting suffix
    stem = re.sub(r"\s*の譜面\s*-\s*プロセカ練習場.*$", "", stem).strip()

    difficulty = "EXPERT"

    m = re.search(r"\((EASY|NORMAL|HARD|EXPERT|MASTER|APPEND)\b.*?\)", stem, flags=re.IGNORECASE)
    if m:
        difficulty = m.group(1).upper()
        title = stem[:m.start()].strip()
        return title or path.stem, difficulty

    # Fallback from parent folders
    for part in reversed(path.parts):
        token = str(part).strip().upper()
        if token in {"EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"}:
            difficulty = token
            break

    return stem or path.stem, difficulty


def _infer_song_id_from_path(path: Path) -> str:
    """
    Stable, path-based fallback.
    """
    stem = path.stem.strip()
    if stem:
        return stem
    return path.name


def _stable_chart_id(path: Path) -> str:
    return str(path.resolve())


# ---------------------------------------------------------------------
# Optional detector bridge
# ---------------------------------------------------------------------

def _try_load_chart(source_ref: str) -> Optional[Dict[str, Any]]:
    """
    Best-effort detector bridge.

    Never raises for missing detector wiring; returns None instead.
    """
    try:
        from chart_visual_detector_merged import (
            load_svg_from_html,
            infer_title_and_difficulty_from_filename as detector_infer_title_and_difficulty,
            lookup_song_metadata,
        )
    except Exception:
        return None

    path = Path(source_ref)
    if not path.is_file():
        return None

    try:
        svg_root = load_svg_from_html(str(path))
        title, diff_name, diff_level = detector_infer_title_and_difficulty(str(path))
        bpm, duration_sec = lookup_song_metadata(title)
    except Exception:
        return None

    return {
        "svg_root": svg_root,
        "title": title,
        "difficulty_name": diff_name,
        "difficulty_level": diff_level,
        "bpm": float(bpm or 0.0),
        "duration_sec": duration_sec,
    }


def _build_proseka_native_notes(raw_chart: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert detector note events -> proseka-native note dicts.

    Returns empty list if detector parser bridge is unavailable.
    """
    try:
        from chart_visual_detector_merged import parse_svg_to_note_events
    except Exception:
        return []

    svg_root = raw_chart.get("svg_root")
    if svg_root is None:
        return []

    try:
        visual_notes = parse_svg_to_note_events(svg_root)
    except Exception:
        return []

    out: List[Dict[str, Any]] = []
    for vn in visual_notes:
        extra = getattr(vn, "extra", None) or {}
        kind = getattr(vn, "kind", "tap")
        shape = extra.get("shape")

        is_critical = False
        note_type = "tap"

        if kind == "tap":
            note_type = "tap"
        elif kind == "critical_tap":
            note_type = "tap"
            is_critical = True
        elif kind in ("flick", "flick_arrow"):
            note_type = "flick"
        elif kind in ("hold_body_or_start", "hold_path", "critical_hold_path"):
            note_type = "trace_body" if shape in ("path", "polyline") else "hold_body"
            is_critical = (kind == "critical_hold_path")

        try:
            src = {
                "time_beats": float(getattr(vn, "time_beats")),
                "lane_index": int(getattr(vn, "lane")),
                "type": note_type,
                "is_critical": bool(is_critical),
            }
        except Exception:
            continue

        if "width_lanes" in extra:
            src["width_lanes"] = int(extra["width_lanes"])
        if "rect_height" in extra:
            src["rect_height"] = float(extra["rect_height"])
        if "direction" in extra:
            src["direction"] = str(extra["direction"])
        if "shape" in extra:
            src["shape"] = str(extra["shape"])

        out.append(src)

    return out


def _normalize_events(raw_chart: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    proseka_notes = _build_proseka_native_notes(raw_chart)

    note_events: List[Dict[str, Any]] = []
    for src in proseka_notes:
        nt = classify_proseka_note(src)
        canonical_kind = map_note_event_type_to_kind(nt)
        if canonical_kind not in _CANONICAL_KINDS:
            canonical_kind = "tap"

        extra: Dict[str, Any] = {"raw_type": nt.value}
        extra["width_lanes"] = int(src.get("width_lanes", 1))
        if src.get("rect_height") is not None:
            extra["rect_height"] = float(src["rect_height"])
        if src.get("direction") is not None:
            extra["direction"] = str(src["direction"])
        if src.get("shape") is not None:
            extra["shape"] = str(src["shape"])

        note_events.append(
            {
                "time_beats": float(src["time_beats"]),
                "lane": int(src["lane_index"]),
                "kind": canonical_kind,
                "extra": extra,
            }
        )

    max_time_beats = max((ev["time_beats"] for ev in note_events), default=0.0)

    bpm = float(raw_chart.get("bpm") or 0.0)
    chart_meta = {
        "bpm": bpm,
        "max_time_beats": float(max_time_beats),
        "duration_sec": raw_chart.get("duration_sec"),
        "title": raw_chart.get("title"),
    }
    return chart_meta, note_events


def _build_sections(chart_meta: Dict[str, Any], note_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Best-effort section builder through detector module.

    Returns [] if unavailable.
    """
    bpm = float(chart_meta.get("bpm") or 0.0)
    if bpm <= 0.0 or not note_events:
        return []

    try:
        from chart_visual_detector_merged import NoteEvent as VisualNoteEvent, build_section_metrics
    except Exception:
        return []

    try:
        visual_notes = [
            VisualNoteEvent(
                time_beats=float(ev["time_beats"]),
                lane=int(ev["lane"]),
                kind=str(ev["kind"]),
                extra=ev.get("extra", {}),
            )
            for ev in note_events
        ]
        sections = build_section_metrics(visual_notes, bpm)
    except Exception:
        return []

    out = []
    for s in sections:
        try:
            out.append(
                {
                    "duration_sec": s.duration_sec,
                    "bpm": s.bpm,
                    "npb": s.npb,
                    "nps": s.nps,
                    "avg_npb_chart": s.avg_npb_chart,
                    "avg_nps_chart": s.avg_nps_chart,
                    "peak_npb_chart": s.peak_npb_chart,
                    "peak_nps_chart": s.peak_nps_chart,
                    "rest_ratio": s.rest_ratio,
                    "hold_coverage": s.hold_coverage,
                    "notes_during_hold_ratio": s.notes_during_hold_ratio,
                    "slide_cross_lane_rate": s.slide_cross_lane_rate,
                    "trace_flick_count": s.trace_flick_count,
                    "flick_density": s.flick_density,
                    "overlap_ratio": s.overlap_ratio,
                    "lane_cross_rate": s.lane_cross_rate,
                    "spacing_variance": s.spacing_variance,
                    "bpm_delta_ratio": s.bpm_delta_ratio,
                    "bpm_shift_count": s.bpm_shift_count,
                    "chart_stop_count": s.chart_stop_count,
                    "fake_end_flag": s.fake_end_flag,
                }
            )
        except Exception:
            continue
    return out


# ---------------------------------------------------------------------
# Minimal payload builder
# ---------------------------------------------------------------------

def build_canonical_payload_proseka(source_ref: str) -> Dict[str, Any]:
    """
    Main module-level builder.

    Guarantees a structurally valid payload even if optional detector / Song DB
    enrichment is unavailable.
    """
    path = Path(source_ref)

    title, difficulty_name = _infer_title_and_difficulty_from_filename(path)
    song_id = _infer_song_id_from_path(path)

    raw_chart = _try_load_chart(source_ref)

    if raw_chart is not None:
        chart_meta, note_events = _normalize_events(raw_chart)
        sections = _build_sections(chart_meta, note_events)
    else:
        chart_meta = {
            "bpm": 0.0,
            "max_time_beats": 0.0,
        }
        note_events = []
        sections = []

    combo_from_events = compute_combo_from_note_events(note_events)

    # Optional Song DB enrichment
    rec = None
    song_db = _try_get_song_db()
    if song_db is not None:
        try:
            rec = song_db.get(song_id)
        except Exception:
            rec = None

    level = None
    note_total_db = None
    difficulty_label = difficulty_name

    if rec is not None:
        try:
            level = song_db.get_level_for_difficulty(rec, difficulty_name)
        except Exception:
            level = None
        try:
            note_total_db = song_db.get_combo_for_difficulty(rec, difficulty_name)
        except Exception:
            note_total_db = None

        if level is not None:
            difficulty_label = f"{difficulty_name} {level}"

    note_delta = abs(combo_from_events - note_total_db) if isinstance(note_total_db, int) else None
    is_consistent = (note_delta == 0) if isinstance(note_delta, int) else None

    diagnostics: Dict[str, Any] = {
        "note_event_count": len(note_events),
        "combo_from_events": combo_from_events,
        "song_db_hit": rec is not None,
        "detector_enabled": raw_chart is not None,
    }

    if sections:
        diagnostics["sections_count"] = len(sections)

    adapter_metadata: Dict[str, Any] = {
        "adapter_id": "adapter_proseka",
        "adapter_version": "2.0.0",
        "source_format": "html/svg or structured",
        "source_path": source_ref,
        "song_id": song_id,
        "difficulty_name": difficulty_name,
        "difficulty_details": {
            "song_id": song_id,
            "difficulty": difficulty_name,
            "level": level,
            "note_total_db": note_total_db,
        },
        "difficulty_consistency": {
            "combo_from_events": combo_from_events,
            "note_total_db": note_total_db,
            "note_delta": note_delta,
            "note_delta_threshold": 0,
            "is_consistent": is_consistent,
        },
    }

    internal_metadata = build_internal_metadata(
        adapter_id="adapter_proseka",
        adapter_version="2.0.0",
        sections_source="chart_visual_detector_merged.build_section_metrics" if sections else None,
        extra={
            "detector_enabled": raw_chart is not None,
            "song_db_enabled": rec is not None,
        },
    )

    payload: Dict[str, Any] = {
        "game_id": GAME_ID,
        "chart_id": _stable_chart_id(path),
        "title": title,
        "difficulty": difficulty_name.upper(),
        "note_events": note_events,
        "chart_meta": chart_meta,
        "adapter_metadata": adapter_metadata,
        "diagnostics": diagnostics,
        "internal_metadata": internal_metadata,
        "sections": sections,
        "canonical_sections_version": SECTION_METRICS_VERSION,
    }

    if rec is not None:
        attach_if_missing(
            payload,
            "song_db_metadata",
            {
                "song_id": getattr(rec, "song_id", None),
                "title": getattr(rec, "title", None),
                "bpm": getattr(rec, "bpm", None),
                "duration_ms": getattr(rec, "duration_ms", None),
            },
        )

    return payload


# ---------------------------------------------------------------------
# Adapter class
# ---------------------------------------------------------------------

class ProsekaAdapter(BaseAdapterV2):
    game_id = GAME_ID
    adapter_id = "adapter_proseka"
    adapter_version = "2.0.0"

    def accepts_file(self, path) -> bool:
        p = Path(path)
        if p.suffix.lower() not in _ALLOWED_EXTS:
            return False
        return _looks_like_proseka_path(p)

    def load(self, path):
        p = Path(path)
        return p.read_text(encoding="utf-8", errors="ignore")

    def to_canonical_payload(self, path: str) -> Dict[str, Any]:
        p = Path(path)
        payload = build_canonical_payload_proseka(str(p))

        # Enforce minimum adapter-validator contract.
        payload = self.finalize_payload_v2(
            payload,
            source_path=str(p),
            default_chart_id=payload.get("chart_id") or _stable_chart_id(p),
            default_difficulty=payload.get("difficulty") or "EXPERT",
        )

        return payload

    def to_canonical_row(self, raw) -> Dict[str, Any]:
        if isinstance(raw, dict):
            payload = raw
        else:
            payload = self.to_canonical_payload(str(raw))

        note_events = payload.get("note_events") if isinstance(payload, dict) else []
        if not isinstance(note_events, list):
            note_events = []

        chart_meta = payload.get("chart_meta") if isinstance(payload, dict) else {}
        if not isinstance(chart_meta, dict):
            chart_meta = {}

        bpm = chart_meta.get("bpm")
        max_time_beats = chart_meta.get("max_time_beats") or 0.0

        duration_ms = 0
        try:
            bpm_f = float(bpm)
            mtb_f = float(max_time_beats)
            if bpm_f > 0:
                duration_ms = int((mtb_f / bpm_f) * 60_000.0)
        except Exception:
            duration_ms = 0

        title = payload.get("title") or payload.get("chart_id") or "UNKNOWN"
        difficulty = payload.get("difficulty") or "EXPERT"

        return {
            "game": GAME_ID,
            "game_id": GAME_ID,
            "song_id": payload.get("chart_id"),
            "name": title,
            "title": title,
            "tier": difficulty,
            "difficulty_label": difficulty,
            "note_total_chart": len(note_events),
            "note_total_db": None,
            "note_delta": None,
            "duration_ms": duration_ms,
            "bpm": bpm,
        }

    def capabilities(self) -> Dict[str, Any]:
        return {
            "note_model": "lane_based",
            "supports_sections": True,
            "supports_variable_bpm": True,
            "supports_flicks": True,
            "supports_holds": True,
            "supports_html_chart_sources": True,
            "supports_best_effort_fallback": True,
        }


__all__ = ["ProsekaAdapter"]