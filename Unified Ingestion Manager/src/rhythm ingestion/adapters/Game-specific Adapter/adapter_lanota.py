#!/usr/bin/env python3
"""adapter_lanota.py

UMI Phase 3 adapter for Lanota.

Grounding (from the Lanotalium editor runtime model):
- Chart JSON contains top-level keys: events, bpm, scroll, eos (song length).
- Note-like events have Type in {0,2,3,4} (tap-family) and {5} (hold).
- BPM and scroll are time-aligned lists with Timing/timing fields.
- The editor injects initial BPM at Time=-3 and initial scroll at Time=-10 when missing.

This adapter is geometry-native (Bucket B): Lanota charts are radial/polar.
We normalize:
- time_beats: float timeline unit derived from Timing (seconds-like), shifted so earliest relevant time maps to 0.
- lane: integer bucket derived from Degree (angle), while preserving raw degree in extra.

Non-goals (per ADAPTER_V2_SPEC):
- No gameplay/tips inference, no registry calls, no writer usage.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base_adapter import BaseAdapter


@dataclass
class LanotaIngestRaw:
    chart_path: Path
    chart_id: str


# ----------------------------
# Loading helpers
# ----------------------------

def _infer_chart_id(path: Path) -> str:
    return path.stem


def _load_chart_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


# ----------------------------
# Normalization helpers
# ----------------------------

# Note event types (as used by ChartData constructor in Lanotalium)
_TAP_TYPES = {0, 2, 3, 4}
_HOLD_TYPE = 5

# Types we treat as non-note (camera, defaults, etc.) are ignored at Phase 3.


def _degree_to_lane_bucket(deg: Any) -> int:
    """Bucket Lanota radial degree into a positive integer lane.

    We avoid imposing a fixed lane count; we simply make a stable bucket.
    Preserve raw degree in extra.
    """
    try:
        d = float(deg)
    except Exception:
        return 1
    # Normalize degree to [0, 360)
    d = d % 360.0
    # Use 1-degree buckets (1..360)
    lane = int(round(d)) + 1
    # Clamp within 1..360
    if lane < 1:
        lane = 1
    if lane > 360:
        lane = 360
    return lane


def _collect_time_candidates(data: Dict[str, Any]) -> List[float]:
    """Collect all time-like values we care about for setting time origin."""
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
    """Choose a deterministic origin so that canonical time_beats is non-negative."""
    if not times:
        return 0.0
    mn = min(times)
    return mn if mn < 0.0 else 0.0


# ----------------------------
# Payload builder
# ----------------------------

def build_canonical_payload_lanota(source_ref: str) -> Dict[str, Any]:
    path = Path(source_ref)
    data = _load_chart_json(path)

    # Determine time origin (Lanota commonly uses negative initial values like -3, -10)
    t_candidates = _collect_time_candidates(data)
    origin = _time_origin(t_candidates)

    events = data.get("events") or []
    bpms = data.get("bpm") or []
    scroll = data.get("scroll") or []
    eos = data.get("eos")

    note_events: List[Dict[str, Any]] = []

    # Extract note-like events
    if isinstance(events, list):
        for e in events:
            if not isinstance(e, dict):
                continue
            etype = e.get("Type")
            try:
                etype_i = int(etype)
            except Exception:
                continue

            # Only ingest tap/hold as Phase-3 note_events
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

            # Holds can include joints
            joints = e.get("joints")
            if kind == "hold_path":
                # duration proxy for downstream density computations
                if dur > 0:
                    extra["rect_height"] = dur
                    extra["shape"] = "hold"
                if isinstance(joints, dict):
                    extra["joints"] = joints

            note_events.append({
                "time_beats": float(t - origin),
                "lane": int(lane),
                "kind": kind,
                "extra": extra,
            })

    # Sort for stability
    note_events.sort(key=lambda ev: (float(ev.get("time_beats", 0.0)), int(ev.get("lane", 0)), str(ev.get("kind", ""))))

    # BPM changes (optional)
    bpm_changes: List[Dict[str, Any]] = []
    base_bpm: float = 100.0
    if isinstance(bpms, list) and bpms:
        # Use the first bpm entry if present
        first = bpms[0]
        if isinstance(first, dict) and isinstance(first.get("Bpm"), (int, float)):
            base_bpm = float(first.get("Bpm"))
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
            bpm_changes.append({"time_beats": float(t - origin), "bpm": bpm_f, "time_raw": t_raw})

    # Scroll events (optional; kept as meta, not used for timing)
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
            scroll_events.append({"time_beats": float(t - origin), "speed": spd_f, "time_raw": t_raw})

    # chart_meta
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

    adapter_metadata: Dict[str, Any] = {
        "adapter_id": "adapter_lanota",
        "adapter_version": "1.0.0",
        "source_format": "lanota_json",
        "source_path": str(path),
        "notes": "Lanota adapter flattening tap/hold events (Type 0/2/3/4/5) and preserving bpm/scroll as chart_meta.",
    }

    diagnostics: Dict[str, Any] = {
        "note_events_count": len(note_events),
        "bpm_changes_count": len(bpm_changes),
        "scroll_events_count": len(scroll_events),
    }

    internal_metadata: Dict[str, Any] = {
        "adapter_id": adapter_metadata.get("adapter_id"),
        "adapter_version": adapter_metadata.get("adapter_version"),
        "sections_source": None,
    }

    payload: Dict[str, Any] = {
        "game_id": "lanota",
        "chart_id": str(path),
        "difficulty": "UNKNOWN",
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

class LanotaAdapter(BaseAdapter):
    game_id = "lanota"

    def accepts_file(self, path: Path) -> bool:
        # Lanotalium charts are JSON (often chart.txt contains JSON, but extension may be .txt)
        return path.suffix.lower() in {".json", ".txt"}

    def load(self, path: Path) -> LanotaIngestRaw:
        return LanotaIngestRaw(chart_path=path, chart_id=_infer_chart_id(path))

    def to_canonical_payload(self, source_ref: str) -> Dict[str, Any]:
        return build_canonical_payload_lanota(source_ref)

    def to_canonical_row(self, raw: LanotaIngestRaw) -> Dict[str, Any]:
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
            "note_model": "spatial",
            "supports_sections": False,
            "supports_variable_bpm": True,
            "supports_bpm_changes": True,
            "emits_canonical_payload": True,
            "source_format": "lanota_json",
        }


__all__ = [
    "LanotaAdapter",
    "LanotaIngestRaw",
    "build_canonical_payload_lanota",
]
