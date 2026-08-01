#!/usr/bin/env python3
from __future__ import annotations

"""
adapter_lanota.py (FULL REPLACEMENT - v2 normalized)

UMI Phase 3 adapter for Lanota.

Grounding model
---------------
Lanota chart JSON commonly contains:
- top-level keys such as events, bpm, scroll, eos
- note-like events with Type in {0,2,3,4} (tap-family) and {5} (hold)
- bpm / scroll as time-aligned lists using Timing / timing-like fields

This adapter is geometry-native / radial:
- time_beats: stable normalized float timeline derived from Timing minus origin
- lane: integer bucket derived from Degree
- preserves raw radial / size / critical fields in extra

Scope
-----
- adapter only
- no validator imports
- no gameplay semantics inference
- no tips logic
- no persistence
- no verification
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

GAME_ID = "lanota"
_ADAPTER_ID = "adapter_lanota"
_ADAPTER_VERSION = "2.0.0"
_SECTION_VERSION = canonical_sections_version(GAME_ID, "adapter_lanota", "v2")

# Conservative canonical subset currently emitted
_CANONICAL_KINDS = {
    "tap",
    "hold_path",
}

# Note event types from Lanotalium-like chart model
_TAP_TYPES = {0, 2, 3, 4}
_HOLD_TYPE = 5


# ---------------------------------------------------------------------
# Raw ingestion model
# ---------------------------------------------------------------------

@dataclass
class LanotaIngestRaw:
    chart_path: Path
    chart_id: str


# ---------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------

def _infer_chart_id(path: Path) -> str:
    return path.stem


def _infer_title(path: Path) -> str:
    return path.stem.strip() or path.name


def _load_chart_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


# ---------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------

def _degree_to_lane_bucket(deg: Any) -> int:
    """
    Bucket Lanota radial degree into a positive integer lane bucket.

    We intentionally avoid hardcoding a gameplay lane count.
    Raw degree is preserved in extra.
    """
    try:
        d = float(deg)
    except Exception:
        return 1

    d = d % 360.0
    lane = int(round(d)) + 1

    if lane < 1:
        lane = 1
    if lane > 360:
        lane = 360
    return lane


def _collect_time_candidates(data: Dict[str, Any]) -> List[float]:
    """
    Collect time-like values used to choose a deterministic origin.
    """
    out: List[float] = []

    events = data.get("events") or []
    if isinstance(events, list):
        for e in events:
            if not isinstance(e, dict):
                continue
            t = e.get("Timing")
            try:
                out.append(float(t))
            except Exception:
                pass

    bpms = data.get("bpm") or []
    if isinstance(bpms, list):
        for b in bpms:
            if not isinstance(b, dict):
                continue
            t = b.get("Timing")
            try:
                out.append(float(t))
            except Exception:
                pass

    scroll = data.get("scroll") or []
    if isinstance(scroll, list):
        for s in scroll:
            if not isinstance(s, dict):
                continue
            t = s.get("timing")
            try:
                out.append(float(t))
            except Exception:
                pass

    return out


def _time_origin(times: List[float]) -> float:
    """
    Choose a deterministic origin so canonical time_beats stays non-negative.
    """
    if not times:
        return 0.0
    mn = min(times)
    return mn if mn < 0.0 else 0.0


# ---------------------------------------------------------------------
# Payload builder
# ---------------------------------------------------------------------

def build_canonical_payload_lanota(source_ref: str) -> Dict[str, Any]:
    """
    Convert a Lanota chart JSON into CanonicalChartPayload.
    """
    path = Path(source_ref)
    data = _load_chart_json(path)

    # Determine origin so early negative bootstrap values are normalized away
    t_candidates = _collect_time_candidates(data)
    origin = _time_origin(t_candidates)

    events = data.get("events") or []
    bpms = data.get("bpm") or []
    scroll = data.get("scroll") or []
    eos = data.get("eos")

    note_events: List[Dict[str, Any]] = []

    # --------------------------------------------------
    # Extract note-like events
    # --------------------------------------------------
    if isinstance(events, list):
        for e in events:
            if not isinstance(e, dict):
                continue

            etype = e.get("Type")
            try:
                etype_i = int(etype)
            except Exception:
                continue

            # Only ingest tap/hold families as note_events
            if etype_i not in _TAP_TYPES and etype_i != _HOLD_TYPE:
                continue

            t_raw = e.get("Timing")
            try:
                t = float(t_raw)
            except Exception:
                continue

            duration_raw = e.get("Duration")
            try:
                dur = float(duration_raw or 0.0)
            except Exception:
                dur = 0.0

            degree = e.get("Degree")
            lane = _degree_to_lane_bucket(degree)

            kind = "hold_path" if etype_i == _HOLD_TYPE else "tap"

            extra: Dict[str, Any] = {
                "raw_type": etype_i,
                "time_raw": t_raw,
                "degree": degree,
                "duration": dur,
                "size": e.get("Size"),
                "sizef": e.get("Sizef"),
                "critical": e.get("Critical"),
                "combination": e.get("Combination"),
                "bpm_at_note": e.get("Bpm"),
            }

            if kind == "hold_path":
                if dur > 0:
                    extra["rect_height"] = dur
                    extra["shape"] = "hold"
                    extra["duration_proxy"] = dur
                joints = e.get("joints")
                if isinstance(joints, dict):
                    extra["joints"] = joints

            note_events.append(
                {
                    "time_beats": float(t - origin),
                    "lane": int(lane),
                    "kind": kind,
                    "extra": extra,
                }
            )

    # Stable ordering
    note_events.sort(
        key=lambda ev: (
            float(ev.get("time_beats", 0.0)),
            int(ev.get("lane", 0)),
            str(ev.get("kind", "")),
        )
    )

    # --------------------------------------------------
    # BPM changes
    # --------------------------------------------------
    bpm_changes: List[Dict[str, Any]] = []
    base_bpm: float = 100.0

    if isinstance(bpms, list) and bpms:
        first = bpms[0]
        if isinstance(first, dict):
            try:
                base_bpm = float(first.get("Bpm"))
            except Exception:
                base_bpm = 100.0

        for b in bpms:
            if not isinstance(b, dict):
                continue
            t_raw = b.get("Timing")
            bpm_val = b.get("Bpm")
            try:
                t = float(t_raw)
                bpm_f = float(bpm_val)
            except Exception:
                continue
            bpm_changes.append(
                {
                    "time_beats": float(t - origin),
                    "bpm": bpm_f,
                    "time_raw": t_raw,
                }
            )

    # --------------------------------------------------
    # Scroll events (kept in chart_meta only)
    # --------------------------------------------------
    scroll_events: List[Dict[str, Any]] = []
    if isinstance(scroll, list) and scroll:
        for s in scroll:
            if not isinstance(s, dict):
                continue
            t_raw = s.get("timing")
            spd = s.get("speed")
            try:
                t = float(t_raw)
                spd_f = float(spd)
            except Exception:
                continue
            scroll_events.append(
                {
                    "time_beats": float(t - origin),
                    "speed": spd_f,
                    "time_raw": t_raw,
                }
            )

    # --------------------------------------------------
    # chart_meta
    # --------------------------------------------------
    max_time = 0.0
    for ev in note_events:
        tb = ev.get("time_beats")
        if isinstance(tb, (int, float)):
            max_time = max(max_time, float(tb))

    chart_meta: Dict[str, Any] = {
        "bpm": base_bpm,
        "max_time_beats": max_time,
        "time_origin": origin,
    }

    if bpm_changes:
        chart_meta["bpm_changes"] = bpm_changes
    if scroll_events:
        chart_meta["scroll_events"] = scroll_events
    if eos is not None:
        chart_meta["song_length_raw"] = eos

    # --------------------------------------------------
    # metadata / diagnostics
    # --------------------------------------------------
    adapter_metadata: Dict[str, Any] = {
        "adapter_id": _ADAPTER_ID,
        "adapter_version": _ADAPTER_VERSION,
        "source_format": "lanota_json",
        "source_path": str(path),
        "notes": "Lanota adapter flattening tap/hold events and preserving bpm/scroll in chart_meta.",
    }

    diagnostics: Dict[str, Any] = {
        "note_events_count": len(note_events),
        "bpm_changes_count": len(bpm_changes),
        "scroll_events_count": len(scroll_events),
    }

    internal_metadata: Dict[str, Any] = build_internal_metadata(
        adapter_id=_ADAPTER_ID,
        adapter_version=_ADAPTER_VERSION,
        sections_source=None,
        notes="geometry-native Lanota adapter; no gameplay inference",
    )

    # --------------------------------------------------
    # payload
    # --------------------------------------------------
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

class LanotaAdapter(BaseAdapterV2):
    game_id = GAME_ID
    adapter_id = _ADAPTER_ID
    adapter_version = _ADAPTER_VERSION

    def accepts_file(self, path: Any) -> bool:
        p = Path(path)
        allowed = with_baseline_fallback_extensions(
            [".json", ".txt"],
            include_baseline=False,
        )
        return p.suffix.casefold() in allowed

    def load(self, path: Any) -> LanotaIngestRaw:
        p = Path(path)
        return LanotaIngestRaw(chart_path=p, chart_id=_infer_chart_id(p))

    def to_canonical_payload(self, source_ref: str) -> Dict[str, Any]:
        payload = build_canonical_payload_lanota(source_ref)
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
                sections_source="lanota-json",
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
        if isinstance(raw, LanotaIngestRaw):
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
            "supports_bpm_changes": True,
            "emits_canonical_payload": True,
            "source_format": "lanota_json",
            "canonical_kinds": list(_CANONICAL_KINDS),
        }


__all__ = [
    "LanotaAdapter",
    "LanotaIngestRaw",
    "build_canonical_payload_lanota",
]