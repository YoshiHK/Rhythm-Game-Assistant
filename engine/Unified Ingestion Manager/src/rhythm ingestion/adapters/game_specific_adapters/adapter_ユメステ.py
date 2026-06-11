#!/usr/bin/env python3
"""adapter_ユメステ.py
UMI Phase 3 adapter for ユメステ (夢のステラリウム / World Dai Star).

Goals (Phase 3 / ADAPTER_V2_SPEC wiring only):
- Structural normalization into a stable canonical payload.
- No gameplay semantics inference.
- Preserve raw tokens/fields in `extra`.
- Naming consistency: game_id is the Japanese string "ユメステ" everywhere.

Source format:
- SUS chart files (.sus)

Timing assumptions:
- ticks_per_beat is assumed 480, tick->beats is tick/480.

This adapter wires a shared SUS -> canonical extractor when available:
- extract_yumesute_note_events_from_sus()
If not importable, it falls back to a minimal local extractor stub that requires
an installed `sus` parser module.

NOTE:
- Content-side wiring only; does not modify completed UMI phases.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .base_adapter import BaseAdapter

# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

GAME_ID = "ユメステ"  # Must remain Japanese across schema/adapter/validator.
_SUS_EXTS = {".sus"}

# Canonical note kinds (must be a subset of schema.notes.canonical_kinds)
CANONICAL_KINDS = {"tap", "hold_path", "slide", "flick"}

# ---------------------------------------------------------------------
# Shared extractor (preferred) + fallback wiring
# ---------------------------------------------------------------------

try:
    # If your repo keeps it under a different filename, adjust import path accordingly.
    from .yumesute_sus_extract import extract_yumesute_note_events_from_sus  # type: ignore
except Exception:
    extract_yumesute_note_events_from_sus = None  # type: ignore


def _tick_to_beats(tick: int) -> float:
    return float(tick) / 480.0


def _bpm_changes(score: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for tick, bpm in (getattr(score, "bpms", None) or []):
        out.append({"time_beats": _tick_to_beats(int(tick)), "bpm": float(bpm)})
    return out


def _base_bpm(score: Any) -> float:
    """Return the first BPM value from score.bpms."""
    bpms = getattr(score, "bpms", None) or []
    if not bpms:
        return 0.0
    return float(bpms[0][1])


def _extract_local(sus_text: str, *, lane_offset: int = 2) -> Dict[str, Any]:
    """Local fallback extractor.

    Requires a `sus` parsing module. Kept intentionally minimal.
    """
    try:
        import sus  # type: ignore
    except Exception as e:
        raise ImportError(
            "Local SUS extractor requires a `sus` module. Install/enable it or provide "
            ".yumesute_sus_extract.extract_yumesute_note_events_from_sus."
        ) from e

    score = sus.loads(sus_text) if hasattr(sus, "loads") else sus.load(sus_text)  # type: ignore

    note_events: List[Dict[str, Any]] = []

    # taps: type 1 normal, 2 critical, 3 flick
    for t in (getattr(score, "taps", None) or []):
        try:
            time_beats = _tick_to_beats(int(getattr(t, "tick", 0)))
            lane = int(getattr(t, "lane", 0)) + int(lane_offset)
            t_type = int(getattr(t, "type", 1))
            kind = "flick" if t_type == 3 else "tap"
            note_events.append(
                {
                    "kind": kind,
                    "time_beats": time_beats,
                    "lane": lane,
                    "extra": {
                        "raw_kind": "tap",
                        "raw_type": t_type,
                        "tick": int(getattr(t, "tick", 0)),
                        "lane_offset": int(lane_offset),
                    },
                }
            )
        except Exception:
            continue

    # slides/holds (conservative): represent as hold_path anchored at start
    for s in (getattr(score, "slides", None) or []):
        try:
            start_tick = int(getattr(s, "start_tick", getattr(s, "tick", 0)))
            time_beats = _tick_to_beats(start_tick)
            lane = int(getattr(s, "lane", 0)) + int(lane_offset)
            note_events.append(
                {
                    "kind": "hold_path",
                    "time_beats": time_beats,
                    "lane": lane,
                    "extra": {
                        "raw_kind": "slide",
                        "tick": start_tick,
                        "lane_offset": int(lane_offset),
                    },
                }
            )
        except Exception:
            continue

    chart_meta: Dict[str, Any] = {
        "bpm": _base_bpm(score),
        "bpm_changes": _bpm_changes(score),
    }

    return {"note_events": note_events, "chart_meta": chart_meta}


def extract_yumesute_note_events_from_sus_wired(sus_text: str, *, lane_offset: int = 2) -> Dict[str, Any]:
    """Unified extractor entrypoint."""
    if extract_yumesute_note_events_from_sus is not None:
        return extract_yumesute_note_events_from_sus(sus_text, lane_offset=lane_offset)  # type: ignore
    return _extract_local(sus_text, lane_offset=lane_offset)


# ---------------------------------------------------------------------
# Raw ingestion model
# ---------------------------------------------------------------------

@dataclass
class ユメステIngestRaw:
    chart_path: Path
    song_id: str
    difficulty_name: str


def _infer_song_id_and_difficulty(path: Path) -> Tuple[str, str]:
    """Infer (song_id, difficulty_name) from filename.

    Convention: "Song Title [DIFF].sus" (DIFF optional).
    """
    stem = path.stem
    diff = "UNKNOWN"
    song = stem
    if "[" in stem and "]" in stem:
        try:
            l = stem.rfind("[")
            r = stem.rfind("]")
            if 0 <= l < r:
                diff = (stem[l + 1 : r].strip() or diff)
                song = (stem[:l].strip() or stem)
        except Exception:
            pass
    return song, diff


# ---------------------------------------------------------------------
# Payload builder
# ---------------------------------------------------------------------


def build_canonical_payload_yumesute(source_ref: str, *, lane_offset: int = 2) -> Dict[str, Any]:
    """Convert a ユメステ SUS chart file into a Phase-3 canonical payload."""
    path = Path(source_ref)
    sus_text = path.read_text(encoding="utf-8", errors="ignore")

    extracted = extract_yumesute_note_events_from_sus_wired(sus_text, lane_offset=lane_offset)
    note_events = list(extracted.get("note_events") or [])
    chart_meta = dict(extracted.get("chart_meta") or {})

    # --- NEW: provide lane_count for validator auto-lane detection ---
    # Prefer explicit if extractor already provides; otherwise infer from observed lanes.
    if "lane_count" not in chart_meta:
        lanes: List[int] = []
        for ev in note_events:
            if not isinstance(ev, dict):
                continue
            try:
                lanes.append(int(ev.get("lane")))
            except Exception:
                continue
        if lanes:
            lane_min = min(lanes)
            lane_max = max(lanes)
            chart_meta["lane_count"] = int(lane_max - lane_min + 1)
            chart_meta.setdefault("lane_min", int(lane_min))
            chart_meta.setdefault("lane_max", int(lane_max))

    # Ensure max_time_beats exists (helps downstream section builders).
    if "max_time_beats" not in chart_meta:
        mt = 0.0
        for ev in note_events:
            try:
                mt = max(mt, float(ev.get("time_beats", 0.0)))
            except Exception:
                pass
        chart_meta["max_time_beats"] = mt

    song_id, diff = _infer_song_id_and_difficulty(path)

    adapter_metadata: Dict[str, Any] = {
        "adapter_id": "adapter_ユメステ",
        "adapter_version": "1.0.1",
        "source_format": "sus",
        "source_path": str(path),
        "notes": "YMST adapter wiring extract_yumesute_note_events_from_sus() into Phase 3 canonical payload.",
    }

    diagnostics: Dict[str, Any] = {
        "note_events_count": len(note_events),
        "bpm_changes_count": len(chart_meta.get("bpm_changes") or []),
        "lane_offset": lane_offset,
        "lane_count": chart_meta.get("lane_count"),
    }

    internal_metadata: Dict[str, Any] = {
        "adapter_id": adapter_metadata.get("adapter_id"),
        "adapter_version": adapter_metadata.get("adapter_version"),
        "sections_source": None,
    }

    return {
        "game_id": GAME_ID,
        "source_ref": str(path),
        "song_id": song_id,
        "difficulty_name": diff,
        "note_events": note_events,
        "chart_meta": chart_meta,
        "sections": [],
        "adapter_metadata": adapter_metadata,
        "diagnostics": diagnostics,
        "internal_metadata": internal_metadata,
        "extra": {"sus_text_encoding": "utf-8"},
    }


# ---------------------------------------------------------------------
# Adapter implementation
# ---------------------------------------------------------------------


class ユメステAdapter(BaseAdapter):
    """UMI Phase 3 adapter for ユメステ."""

    game_id = GAME_ID

    def accepts_file(self, file_path: str) -> bool:
        return Path(file_path).suffix.lower() in _SUS_EXTS

    def load(self, file_path: str) -> Dict[str, Any]:
        p = Path(file_path)
        payload = build_canonical_payload_yumesute(str(p))
        return {
            "game_id": GAME_ID,
            "source_ref": str(p),
            "song_id": payload.get("song_id") or p.stem,
            "difficulty_name": payload.get("difficulty_name") or "UNKNOWN",
            "canonical_payload": payload,
        }

    def to_canonical_row(self, source_ref: str) -> Dict[str, Any]:
        return self.load(source_ref)


__all__ = [
    "ユメステAdapter",
    "ユメステIngestRaw",
    "build_canonical_payload_yumesute",
    "extract_yumesute_note_events_from_sus_wired",
    "GAME_ID",
    "CANONICAL_KINDS",
]
