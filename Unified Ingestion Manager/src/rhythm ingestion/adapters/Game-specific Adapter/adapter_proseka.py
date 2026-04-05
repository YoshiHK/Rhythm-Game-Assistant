from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base_adapter import BaseAdapter
from ..utils.proseka_song_db import ProsekaSongDb


# ---------------------------------------------------------------------
# DB singleton (loaded once per process)
# ---------------------------------------------------------------------
_DEFAULT_DB_CSV = Path(__file__).with_name("Proseka Song DB.csv")
_SONG_DB = ProsekaSongDb(str(_DEFAULT_DB_CSV))


# ---------------------------------------------------------------------
# Raw structure used by this ingestion adapter
# ---------------------------------------------------------------------
@dataclass
class ProsekaIngestRaw:
    chart_path: Path
    song_id: str
    difficulty_name: str
    note_total_chart: Optional[int] = None


# ---------------------------------------------------------------------
# Proseka note typing (aligned with validator expectations)
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

    if t in (NoteEventType.HOLD_START, NoteEventType.HOLD_END, NoteEventType.HOLD_TICK, NoteEventType.TRACE_TICK):
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
        extra = ev.get("extra")
        if not isinstance(extra, dict):
            continue
        raw_type = extra.get("raw_type")
        if raw_type in _COMBO_RAW_TYPES:
            combo += 1
    return combo


# ---------------------------------------------------------------------
# Stage 2–4.1 bridge: load chart + parse notes + build sections
# ---------------------------------------------------------------------
def _load_chart(source_ref: str) -> Dict[str, Any]:
    from chart_visual_detector_merged import (
        load_svg_from_html,
        infer_title_and_difficulty_from_filename,
        lookup_song_metadata,
    )

    path = Path(source_ref)
    if not path.is_file():
        raise FileNotFoundError(f"Proseka chart file not found: {path}")

    svg_root = load_svg_from_html(str(path))
    title, diff_name, diff_level = infer_title_and_difficulty_from_filename(str(path))
    bpm, duration_sec = lookup_song_metadata(title)
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
    Convert visual detector note events -> proseka-native note dicts.
    """
    from chart_visual_detector_merged import parse_svg_to_note_events  # expected in your detector

    svg_root = raw_chart.get("svg_root")
    visual_notes = parse_svg_to_note_events(svg_root)

    out: List[Dict[str, Any]] = []
    for vn in visual_notes:
        extra = getattr(vn, "extra", None) or {}
        kind = getattr(vn, "kind", "tap")
        shape = extra.get("shape")

        # Map detector kind -> proseka-native (type, is_critical)
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
            # Treat path/polyline as trace body, else hold body
            note_type = "trace_body" if shape in ("path", "polyline") else "hold_body"
            is_critical = (kind == "critical_hold_path")

        src = {
            "time_beats": float(getattr(vn, "time_beats")),
            "lane_index": int(getattr(vn, "lane")),
            "type": note_type,
            "is_critical": bool(is_critical),
        }

        # Carry optional geometry metadata for diagnostics (safe)
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
    """
    Convert proseka-native notes into canonical note_events + chart_meta.
    """
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
    Build SectionMetrics dicts using detector's section builder.
    """
    bpm = float(chart_meta.get("bpm") or 0.0)
    if bpm <= 0.0 or not note_events:
        return []

    from chart_visual_detector_merged import NoteEvent as VisualNoteEvent, build_section_metrics

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

    # Convert dataclass-like objects to dicts
    out = []
    for s in sections:
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
    return out


def build_canonical_payload(source_ref: str) -> Dict[str, Any]:
    """
    Main module-level builder: convert Proseka chart file into canonical payload dict.
    """
    raw_chart = _load_chart(source_ref)
    chart_meta, note_events = _normalize_events(raw_chart)
    sections = _build_sections(chart_meta, note_events)
    combo_from_events = compute_combo_from_note_events(note_events)

    # Infer song_id/difficulty from filename (same logic as adapter)
    path = Path(source_ref)
    stem = path.stem
    digits = []
    for ch in stem:
        if ch.isdigit():
            digits.append(ch)
        elif digits:
            break
    song_id = "".join(digits) if digits else stem

    diff_names = ["Easy", "Normal", "Hard", "Expert", "Master", "Append"]
    lower = stem.lower()
    difficulty_name = "Expert"
    for n in diff_names:
        if n.lower() in lower:
            difficulty_name = n
            break

    rec = _SONG_DB.get(song_id)
    level = _SONG_DB.get_level_for_difficulty(rec, difficulty_name) if rec else None
    note_total_db = _SONG_DB.get_combo_for_difficulty(rec, difficulty_name) if rec else None
    difficulty_label = f"{difficulty_name} {level}" if level is not None else difficulty_name

    note_delta = abs(combo_from_events - note_total_db) if isinstance(note_total_db, int) else None
    is_consistent = (note_delta == 0) if isinstance(note_delta, int) else None

    diagnostics: Dict[str, Any] = {}
    if sections:
        diagnostics["sections_count"] = len(sections)
        diagnostics["avg_nps"] = sum(s.get("nps", 0.0) for s in sections) / max(1, len(sections))
        diagnostics["avg_npb"] = sum(s.get("npb", 0.0) for s in sections) / max(1, len(sections))
        diagnostics["total_hold_coverage"] = sum(s.get("hold_coverage", 0.0) for s in sections) / max(1, len(sections))

    adapter_metadata: Dict[str, Any] = {
        "adapter_id": "adapter_proseka_v1",
        "adapter_version": "1.0.0",
        "source_format": "html/svg or structured",
        "source_path": source_ref,
        "song_id": song_id,
        "difficulty_name": difficulty_name,
        "combo_from_events": combo_from_events,
        "difficulty_details": {
            "song_id": song_id,
            "name": rec.title if rec else chart_meta.get("title"),
            "difficulty": difficulty_name,
            "level": level,
            "note_total_db": note_total_db,
            "bpm_db": rec.bpm if rec else None,
            "duration_ms_db": rec.duration_ms if rec else None,
        },
        "difficulty_consistency": {
            "combo_from_events": combo_from_events,
            "note_total_db": note_total_db,
            "note_delta": note_delta,
            "note_delta_threshold": 0,
            "is_consistent": is_consistent,
        },
    }

    internal_metadata = {
        "sections_source": "chart_visual_detector_merged.build_section_metrics",
        "adapter_id": adapter_metadata.get("adapter_id"),
        "adapter_version": adapter_metadata.get("adapter_version"),
    }

    return {
        "game_id": "proseka",
        "chart_id": source_ref,
        "difficulty": difficulty_label,
        "note_events": note_events,
        "chart_meta": chart_meta,
        "adapter_metadata": adapter_metadata,
        "diagnostics": diagnostics,
        "internal_metadata": internal_metadata,
        "sections": sections,
        "canonical_sections_version": SECTION_METRICS_VERSION,
        # detected_tags can be added by tagging pipeline later
    }


# ---------------------------------------------------------------------
# Adapter implementation
# ---------------------------------------------------------------------
class ProsekaAdapter(BaseAdapter):
    game_id = "proseka"

    def accepts_file(self, path: Path) -> bool:
        return path.suffix.lower() in {".html", ".htm", ".svg", ".json"}

    def load(self, path: Path) -> ProsekaIngestRaw:
        song_id, difficulty_name = self._infer_song_id_and_difficulty(path)
        return ProsekaIngestRaw(chart_path=path, song_id=song_id, difficulty_name=difficulty_name)

    def to_canonical_payload(self, source_ref: str) -> Dict[str, Any]:
        # IMPORTANT: this must be a method for UMI to call it (hasattr check)
        return build_canonical_payload(source_ref)

    def to_canonical_row(self, raw: ProsekaIngestRaw) -> Dict[str, Any]:
        song_id = raw.song_id
        difficulty_name = raw.difficulty_name
        tier = difficulty_name

        rec = _SONG_DB.get(song_id)
        name = rec.title if rec else None
        level = _SONG_DB.get_level_for_difficulty(rec, difficulty_name) if rec else None
        difficulty_label = f"{tier} {level}" if level is not None else tier

        note_total_db = _SONG_DB.get_combo_for_difficulty(rec, difficulty_name) if rec else None
        bpm = rec.bpm if rec else None
        duration_ms = rec.duration_ms if rec else 0

        # Compute note_total_chart from canonical payload note_events (best effort)
        note_total_chart: int
        try:
            payload = self.to_canonical_payload(str(raw.chart_path))
            note_total_chart = compute_combo_from_note_events(payload.get("note_events", []) or [])
        except Exception:
            note_total_chart = int(raw.note_total_chart or 0)

        return {
            "game": "proseka",
            "song_id": song_id,
            "name": name,
            "tier": tier,
            "level": level,
            "difficulty_code": None,
            "difficulty_label": difficulty_label,
            "note_total_chart": int(note_total_chart),
            "note_total_db": note_total_db,
            "note_delta": None,  # validator may fill
            "duration_ms": int(duration_ms),
            "bpm": bpm,
            "rating_raw": None,
            "chart_path": str(raw.chart_path),
        }

    def _infer_song_id_and_difficulty(self, path: Path) -> Tuple[str, str]:
        stem = path.stem

        digits: List[str] = []
        for ch in stem:
            if ch.isdigit():
                digits.append(ch)
            elif digits:
                break
        song_id = "".join(digits) if digits else stem

        diff_names = ["Easy", "Normal", "Hard", "Expert", "Master", "Append"]
        lower = stem.lower()
        difficulty_name = "Expert"
        for name in diff_names:
            if name.lower() in lower:
                difficulty_name = name
                break

        return song_id, difficulty_name

    def capabilities(self) -> dict:
        return {
            "note_model": "lane_based",
            "supports_sections": True,
            "supports_trace_notes": True,
            "supports_variable_bpm": True,
            "emits_canonical_payload": True,
        }


__all__ = ["ProsekaAdapter", "ProsekaIngestRaw", "build_canonical_payload"]
