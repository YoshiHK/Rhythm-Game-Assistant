#!/usr/bin/env python3
"""adapter_chunithm.py

UMI Phase 3 adapter for CHUNITHM.

Grounding (from Charting.md in this repo):
- Charts are plain-text .c2s files.
- Playfield has 16 columns (cells 0-15) and each note has a width extending right.
- Timing is measure + offset where RESOLUTION is (typically) 384 and represents one measure.
- Note types include TAP/CHR/HLD/SLD/SLC/FLK/AIR/AUR/AUL/AHD/ADW/ADR/ADL/MNE.
- BPM changes are specified by "BPM <measure> <offset> <bpm>".
- MET (time signature) and SFL (speed multiplier) are cosmetic; preserved as metadata only.

Scope:
- Structural normalization only (ADAPTER_V2_SPEC).
- No tips, no gameplay semantics inference.
- Preserve original tokens in extra for later pipelines.

Canonical payload ordering follows the project ordering convention.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base_adapter import BaseAdapter


# ----------------------------
# Raw structure
# ----------------------------

@dataclass
class ChunithmIngestRaw:
    chart_path: Path
    song_id: str
    difficulty_name: str


# ----------------------------
# Parsing helpers
# ----------------------------

_NOTE_TYPES = {
    "TAP",
    "CHR",
    "HLD",
    "SLD",
    "SLC",
    "FLK",
    "AIR",
    "AUR",
    "AUL",
    "AHD",
    "ADW",
    "ADR",
    "ADL",
    "MNE",
}

_TAG_TYPES = {
    "VERSION",
    "MUSIC",
    "SEQUENCEID",
    "DIFFICULT",
    "LEVEL",
    "CREATOR",
    "BPM_DEF",
    "RESOLUTION",
    "CLK_DEF",
    "PROGJUDGE_BPM",
    "PROGJUDGE_AER",
    "TUTORIAL",
    "BPM",
    "MET",
    "SFL",
}


def _infer_song_id_and_difficulty(path: Path) -> Tuple[str, str]:
    stem = path.stem
    diff = "UNKNOWN"
    song = stem
    if "[" in stem and "]" in stem:
        try:
            l = stem.rfind("[")
            r = stem.rfind("]")
            if 0 <= l < r:
                diff = stem[l + 1:r].strip() or diff
                song = stem[:l].strip() or stem
        except Exception:
            pass
    return song, diff


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


def _time_beats(measure: int, offset: int, resolution: int, beats_per_measure: int = 4) -> float:
    # resolution represents one measure; offset is within [0, resolution)
    return float(measure) * float(beats_per_measure) + (float(offset) / float(resolution)) * float(beats_per_measure)


def _duration_beats(duration: int, resolution: int, beats_per_measure: int = 4) -> float:
    return (float(duration) / float(resolution)) * float(beats_per_measure)


def _lane_from_cell(cell: int) -> int:
    # canonical lane is positive integer; CHUNITHM cells are 0-based
    return int(cell) + 1


def _kind_for_note_type(note_type: str) -> str:
    # Conservative canonical kind mapping.
    if note_type == "CHR":
        return "critical_tap"
    if note_type == "FLK":
        return "flick_arrow"
    if note_type in ("HLD", "SLD", "SLC", "AHD"):
        return "hold_path"
    # AIR/ADW variants and mines are kept as tap-like structural events
    return "tap"


def parse_c2s(text: str) -> Dict[str, Any]:
    """Parse a .c2s text file into tags + note records.

    Returns:
      {
        'tags': {...},
        'bpms': [...],
        'mets': [...],
        'sfls': [...],
        'notes': [...],
      }
    """

    tags: Dict[str, Any] = {}
    bpms: List[Dict[str, Any]] = []
    mets: List[Dict[str, Any]] = []
    sfls: List[Dict[str, Any]] = []
    notes: List[Dict[str, Any]] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # common comment styles (best-effort)
        if line.startswith("//") or line.startswith(";"):
            continue

        parts = line.split()  # split on any whitespace (tabs/spaces)
        if not parts:
            continue

        head = parts[0]

        # Tag lines
        if head in _TAG_TYPES and head not in _NOTE_TYPES:
            if head == "BPM_DEF":
                vals = [p for p in parts[1:]]
                tags["BPM_DEF"] = vals
            elif head == "RESOLUTION":
                tags["RESOLUTION"] = _safe_int(parts[1], default=None) if len(parts) > 1 else None
            elif head == "CREATOR":
                tags["CREATOR"] = " ".join(parts[1:]) if len(parts) > 1 else ""
            elif head == "BPM":
                # BPM <measure> <offset> <bpm>
                if len(parts) >= 4:
                    bpms.append({
                        "measure": _safe_int(parts[1], 0) or 0,
                        "offset": _safe_int(parts[2], 0) or 0,
                        "bpm": _safe_float(parts[3], None),
                        "raw": parts,
                    })
            elif head == "MET":
                # MET <measure> <offset> <second> <first> (cosmetic)
                if len(parts) >= 5:
                    mets.append({
                        "measure": _safe_int(parts[1], 0) or 0,
                        "offset": _safe_int(parts[2], 0) or 0,
                        "second": parts[3],
                        "first": parts[4],
                        "raw": parts,
                    })
            elif head == "SFL":
                # SFL <measure> <offset> <duration> <multiplier>
                if len(parts) >= 5:
                    sfls.append({
                        "measure": _safe_int(parts[1], 0) or 0,
                        "offset": _safe_int(parts[2], 0) or 0,
                        "duration": _safe_int(parts[3], 0) or 0,
                        "multiplier": _safe_float(parts[4], None),
                        "raw": parts,
                    })
            else:
                # default: store remainder as string
                tags[head] = " ".join(parts[1:]) if len(parts) > 1 else ""
            continue

        # Note lines
        if head in _NOTE_TYPES:
            # Universal schema: type measure offset cell width [extras...]
            if len(parts) < 5:
                continue
            measure = _safe_int(parts[1], None)
            offset = _safe_int(parts[2], None)
            cell = _safe_int(parts[3], None)
            width = _safe_int(parts[4], None)
            if measure is None or offset is None or cell is None or width is None:
                continue
            notes.append({
                "note_type": head,
                "measure": int(measure),
                "offset": int(offset),
                "cell": int(cell),
                "width": int(width),
                "extras": parts[5:],
                "raw": parts,
            })
            continue

        # unknown lines ignored

    return {
        "tags": tags,
        "bpms": bpms,
        "mets": mets,
        "sfls": sfls,
        "notes": notes,
    }


# ----------------------------
# Payload builder
# ----------------------------


def build_canonical_payload_chunithm(source_ref: str) -> Dict[str, Any]:
    path = Path(source_ref)
    text = path.read_text(encoding="utf-8", errors="ignore")

    parsed = parse_c2s(text)
    tags = parsed["tags"]
    resolution = int(tags.get("RESOLUTION") or 384)

    # BPM defaults
    bpm_def = tags.get("BPM_DEF")
    base_bpm: float = 0.0
    if isinstance(bpm_def, list) and bpm_def:
        b = _safe_float(bpm_def[0], None)
        if b is not None:
            base_bpm = float(b)

    # BPM changes
    bpm_changes: List[Dict[str, Any]] = []
    for b in parsed["bpms"]:
        bpm_val = b.get("bpm")
        if bpm_val is None:
            continue
        t = _time_beats(int(b["measure"]), int(b["offset"]), resolution)
        bpm_changes.append({"time_beats": t, "bpm": float(bpm_val), "raw": b.get("raw")})

    # Notes -> note_events
    note_events: List[Dict[str, Any]] = []
    for n in parsed["notes"]:
        nt = str(n["note_type"])
        measure = int(n["measure"])
        offset = int(n["offset"])
        cell = int(n["cell"])
        width = int(n["width"])

        t = _time_beats(measure, offset, resolution)
        lane = _lane_from_cell(cell)
        kind = _kind_for_note_type(nt)

        extra: Dict[str, Any] = {
            "raw_type": nt,
            "measure": measure,
            "offset": offset,
            "cell": cell,
            "width_lanes": width,
            "resolution": resolution,
            "extras": list(n.get("extras") or []),
        }

        # Per-note-type extra parsing (structural only)
        if nt == "CHR":
            # Schema: CHR ... <modifier>
            if n.get("extras"):
                extra["chr_modifier"] = n["extras"][0]
        elif nt == "HLD":
            # Schema: HLD ... <duration>
            if n.get("extras"):
                dur_raw = _safe_int(n["extras"][0], 0) or 0
                extra["duration_raw"] = dur_raw
                dur_b = _duration_beats(dur_raw, resolution)
                extra["duration_beats"] = dur_b
                extra["rect_height"] = dur_b
                extra["shape"] = "hold"
        elif nt in ("SLD", "SLC"):
            # Schema: SLD/SLC ... <duration> <end_cell> <end_width>
            if len(n.get("extras") or []) >= 3:
                dur_raw = _safe_int(n["extras"][0], 0) or 0
                end_cell = _safe_int(n["extras"][1], None)
                end_width = _safe_int(n["extras"][2], None)
                extra["duration_raw"] = dur_raw
                dur_b = _duration_beats(dur_raw, resolution)
                extra["duration_beats"] = dur_b
                extra["rect_height"] = dur_b
                extra["shape"] = "hold"
                if end_cell is not None:
                    extra["end_cell"] = int(end_cell)
                    extra["end_lane"] = _lane_from_cell(int(end_cell))
                if end_width is not None:
                    extra["end_width_lanes"] = int(end_width)
        elif nt == "FLK":
            # Schema: FLK ... <unknown> (usually 'L')
            if n.get("extras"):
                extra["flk_unknown"] = n["extras"][0]
        elif nt in ("AIR", "AUR", "AUL", "ADW", "ADR", "ADL"):
            # Schema: ... <target_note>
            if n.get("extras"):
                extra["target_note"] = n["extras"][0]
        elif nt == "AHD":
            # Schema: AHD ... <target_note> <duration>
            if len(n.get("extras") or []) >= 2:
                extra["target_note"] = n["extras"][0]
                dur_raw = _safe_int(n["extras"][1], 0) or 0
                extra["duration_raw"] = dur_raw
                dur_b = _duration_beats(dur_raw, resolution)
                extra["duration_beats"] = dur_b
                extra["rect_height"] = dur_b
                extra["shape"] = "hold"

        note_events.append({
            "time_beats": t,
            "lane": lane,
            "kind": kind,
            "extra": extra,
        })

    # Stable sorting
    note_events.sort(key=lambda ev: (float(ev.get("time_beats", 0.0)), int(ev.get("lane", 0)), str(ev.get("kind", ""))))

    # max_time_beats
    max_time_beats = 0.0
    for ev in note_events:
        tb = ev.get("time_beats")
        if isinstance(tb, (int, float)):
            max_time_beats = max(max_time_beats, float(tb))

    # chart_meta
    chart_meta: Dict[str, Any] = {
        "bpm": base_bpm,
        "max_time_beats": max_time_beats,
        "resolution": resolution,
    }
    if bpm_def is not None:
        chart_meta["bpm_def"] = bpm_def
    if bpm_changes:
        chart_meta["bpm_changes"] = bpm_changes
    if parsed["mets"]:
        chart_meta["met_events"] = parsed["mets"]
    if parsed["sfls"]:
        chart_meta["sfl_events"] = parsed["sfls"]
    if "CREATOR" in tags:
        chart_meta["creator"] = tags.get("CREATOR")

    # adapter metadata
    adapter_metadata: Dict[str, Any] = {
        "adapter_id": "adapter_chunithm",
        "adapter_version": "1.0.0",
        "source_format": "c2s",
        "source_path": str(path),
        "notes": "CHUNITHM adapter parsing .c2s (tags + note lines) and emitting canonical note_events.",
    }

    diagnostics: Dict[str, Any] = {
        "note_events_count": len(note_events),
        "bpm_changes_count": len(bpm_changes),
        "resolution": resolution,
    }

    internal_metadata: Dict[str, Any] = {
        "adapter_id": adapter_metadata.get("adapter_id"),
        "adapter_version": adapter_metadata.get("adapter_version"),
        "sections_source": None,
    }

    song_id, difficulty_label = _infer_song_id_and_difficulty(path)

    payload: Dict[str, Any] = {
        "game_id": "chunithm",
        "chart_id": str(path),
        "difficulty": difficulty_label,

        "note_events": note_events,
        "chart_meta": chart_meta,
        "adapter_metadata": adapter_metadata,
        "diagnostics": diagnostics,
        "internal_metadata": internal_metadata,
        # sections optional
    }

    return payload


# ----------------------------
# Adapter implementation
# ----------------------------


class ChunithmAdapter(BaseAdapter):
    game_id = "chunithm"

    def accepts_file(self, path: Path) -> bool:
        return path.suffix.lower() in {".c2s", ".txt"}

    def load(self, path: Path) -> ChunithmIngestRaw:
        song_id, diff = _infer_song_id_and_difficulty(path)
        return ChunithmIngestRaw(chart_path=path, song_id=song_id, difficulty_name=diff)

    def to_canonical_payload(self, source_ref: str) -> Dict[str, Any]:
        return build_canonical_payload_chunithm(source_ref)

    def to_canonical_row(self, raw: ChunithmIngestRaw) -> Dict[str, Any]:
        payload = self.to_canonical_payload(str(raw.chart_path))
        note_events = payload.get("note_events") or []
        note_total_chart = len(note_events) if isinstance(note_events, list) else 0
        chart_meta = payload.get("chart_meta") or {}

        return {
            "game": self.game_id,
            "song_id": raw.song_id,
            "difficulty_label": payload.get("difficulty") or raw.difficulty_name or "UNKNOWN",
            "note_total_chart": int(note_total_chart),
            "duration_ms": None,
            "bpm": chart_meta.get("bpm"),
            "chart_path": str(raw.chart_path),
        }

    def capabilities(self) -> dict:
        return {
            "note_model": "lane_based",
            "supports_sections": False,
            "supports_variable_bpm": True,
            "supports_bpm_changes": True,
            "emits_canonical_payload": True,
            "source_format": "c2s",
        }


__all__ = [
    "ChunithmAdapter",
    "ChunithmIngestRaw",
    "build_canonical_payload_chunithm",
]
