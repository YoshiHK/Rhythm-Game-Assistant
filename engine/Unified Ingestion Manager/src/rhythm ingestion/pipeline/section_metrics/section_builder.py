"""
section_builder.py

Stage 2–4.1: Build SectionMetrics from canonical chart payload components.

This module is a deterministic, game-agnostic sectioning utility that consumes:
- chart_meta (must include max_time_beats if using uniform slicing)
- note_events (canonical list; each event must include time_beats, lane, kind)

It produces:
- List[SectionMetrics] (see section_metrics_dataclasses.py)

This module MUST NOT:
- perform file I/O
- invoke adapters or validators
- detect pattern tags
- infer severity / tips
- depend on ingestion orchestration

Inspired by the safe/deterministic aggregation style in summary_builder.py
(e.g., safe float conversion, stable ordering). [1](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!sf9d72c160e6a4576a81de9db77fde6a7)
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .section_metrics_dataclasses import LaneUsage, SectionMetrics


# ----------------------------
# Safe helpers (pure)
# ----------------------------

def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        if x is None:
            return default
        # Avoid bool -> int coercion
        if isinstance(x, bool):
            return default
        return int(x)
    except Exception:
        return default


def _normalize_kind(kind: Any) -> str:
    return str(kind).strip().lower() if kind is not None else ""


def _classify_note_kind(kind: str) -> str:
    """
    Map canonical note kind into a coarse bucket for section metrics.
    This is intentionally conservative and game-agnostic.

    Buckets:
    - "tap"
    - "hold"
    - "flick"
    - "other"
    """
    k = _normalize_kind(kind)

    # taps
    if k in ("tap", "critical_tap"):
        return "tap"

    # flicks
    if k in ("flick", "flick_arrow"):
        return "flick"

    # holds / paths
    if k in ("hold_body_or_start", "hold_path", "critical_hold_path"):
        return "hold"

    return "other"


def _iter_events_in_window(
    note_events: Sequence[Dict[str, Any]],
    start_beats: float,
    end_beats: float,
) -> List[Dict[str, Any]]:
    """
    Return events whose time_beats fall into [start_beats, end_beats).
    Deterministic: preserves original order from note_events.
    """
    out: List[Dict[str, Any]] = []
    for ev in note_events or []:
        if not isinstance(ev, dict):
            continue
        tb = ev.get("time_beats")
        if not isinstance(tb, (int, float)):
            continue
        tbf = float(tb)
        if start_beats <= tbf < end_beats:
            out.append(ev)
    return out


# ----------------------------
# Boundary construction
# ----------------------------

def compute_uniform_boundaries_by_beats(
    *,
    max_time_beats: float,
    section_count: int,
    start_beats: float = 0.0,
) -> List[Tuple[float, float]]:
    """
    Compute uniform beat windows [start,end) that cover [start_beats, max_time_beats].

    If max_time_beats <= start_beats or section_count <= 0 -> returns [].
    """
    mtb = float(max_time_beats)
    sb = float(start_beats)
    n = int(section_count)

    if n <= 0 or mtb <= sb:
        return []

    total = mtb - sb
    step = total / float(n)
    out: List[Tuple[float, float]] = []

    cur = sb
    for i in range(n):
        nxt = sb + step * float(i + 1)
        # last window ends exactly at mtb to avoid drift
        if i == n - 1:
            nxt = mtb
        out.append((cur, nxt))
        cur = nxt
    return out


def compute_boundaries_from_section_markers(
    section_markers: Sequence[Any],
    *,
    start_beats: float = 0.0,
    max_time_beats: Optional[float] = None,
) -> List[Tuple[float, float]]:
    """
    Build boundaries from a list of marker beats (e.g. measure markers).

    section_markers should be a sequence of numbers (beats) indicating section endpoints.
    Sections will be:
      [start_beats, marker0), [marker0, marker1), ..., [markerK-1, markerK)
    If max_time_beats provided and last marker < max_time_beats, append final window.
    """
    sb = float(start_beats)
    marks: List[float] = []

    for m in section_markers or []:
        if isinstance(m, (int, float)):
            marks.append(float(m))

    # keep strictly increasing markers greater than start
    marks = sorted(set(x for x in marks if x > sb))
    out: List[Tuple[float, float]] = []

    cur = sb
    for m in marks:
        if m <= cur:
            continue
        out.append((cur, m))
        cur = m

    if max_time_beats is not None:
        mtb = float(max_time_beats)
        if mtb > cur:
            out.append((cur, mtb))

    return out


# ----------------------------
# Core builder
# ----------------------------

def build_sections(
    chart_meta: Dict[str, Any],
    note_events: Sequence[Dict[str, Any]],
    *,
    section_count: int = 8,
    method: str = "uniform_beats",
    attach_lane_usage: bool = True,
    attach_extra: bool = False,
) -> List[SectionMetrics]:
    """
    Build a list of SectionMetrics objects.

    Parameters
    ----------
    chart_meta:
        Should include max_time_beats for uniform slicing.
        May include measure_markers or other marker lists for marker slicing.
    note_events:
        Canonical note event list.
    section_count:
        Used only for uniform slicing methods.
    method:
        - "uniform_beats" (default): uses chart_meta['max_time_beats']
        - "markers_beats": uses chart_meta['measure_markers'] or chart_meta['section_markers']
    attach_lane_usage:
        If True, include lane usage counts per section.
    attach_extra:
        If True, attach a small extra dict (diagnostics) to each section.

    Returns
    -------
    List[SectionMetrics]
    """
    cm = chart_meta or {}
    events = list(note_events or [])

    # Total events for coverage
    total_events = sum(
        1
        for ev in events
        if isinstance(ev, dict) and isinstance(ev.get("time_beats"), (int, float))
    )

    # Determine boundaries
    boundaries: List[Tuple[float, float]] = []

    m = (method or "").strip().lower()
    if m == "markers_beats":
        markers = cm.get("measure_markers") or cm.get("section_markers") or []
        max_time_beats = cm.get("max_time_beats")
        mtb = float(max_time_beats) if isinstance(max_time_beats, (int, float)) else None
        boundaries = compute_boundaries_from_section_markers(
            markers, start_beats=0.0, max_time_beats=mtb
        )
    else:
        # default uniform beats
        max_time_beats = cm.get("max_time_beats")
        mtb = _safe_float(max_time_beats, 0.0)
        boundaries = compute_uniform_boundaries_by_beats(
            max_time_beats=mtb, section_count=section_count, start_beats=0.0
        )

    if not boundaries:
        return []

    sections_out: List[SectionMetrics] = []

    for idx, (start_b, end_b) in enumerate(boundaries):
        # Guard against degenerate windows
        if end_b <= start_b:
            continue

        window_events = _iter_events_in_window(events, start_b, end_b)

        # Counts
        note_count = len(window_events)
        tap_count = 0
        hold_count = 0
        flick_count = 0

        lane_counts: Dict[str, int] = {}

        for ev in window_events:
            kind_bucket = _classify_note_kind(ev.get("kind"))
            if kind_bucket == "tap":
                tap_count += 1
            elif kind_bucket == "hold":
                hold_count += 1
            elif kind_bucket == "flick":
                flick_count += 1

            if attach_lane_usage:
                lane = ev.get("lane")
                if isinstance(lane, (int, float)):
                    # normalize to int-like lane id for distribution
                    lane_id = str(int(round(float(lane))))
                    lane_counts[lane_id] = lane_counts.get(lane_id, 0) + 1

        duration_beats = float(end_b - start_b)
        note_density = (note_count / duration_beats) if duration_beats > 0 else 0.0
        section_coverage = (note_count / total_events) if total_events > 0 else 0.0

        lane_usage = LaneUsage(counts=lane_counts) if (attach_lane_usage and lane_counts) else None

        extra: Optional[Dict[str, object]] = None
        if attach_extra:
            extra = {
                "window_event_count": note_count,
                "total_events": total_events,
            }

        sec = SectionMetrics(
            section_index=int(idx),
            start_time_beats=float(start_b),
            end_time_beats=float(end_b),
            note_count=int(note_count),
            tap_count=int(tap_count),
            hold_count=int(hold_count),
            flick_count=int(flick_count),
            duration_beats=float(duration_beats),
            note_density=float(note_density),
            section_coverage=float(section_coverage),
            lane_usage=lane_usage,
            extra=extra,
        )

        sections_out.append(sec)

    return sections_out


def build_sections_dicts(
    chart_meta: Dict[str, Any],
    note_events: Sequence[Dict[str, Any]],
    *,
    section_count: int = 8,
    method: str = "uniform_beats",
    attach_lane_usage: bool = True,
    attach_extra: bool = False,
) -> List[Dict[str, Any]]:
    """
    Convenience wrapper: return sections as list[dict] for canonical payload storage.
    """
    secs = build_sections(
        chart_meta,
        note_events,
        section_count=section_count,
        method=method,
        attach_lane_usage=attach_lane_usage,
        attach_extra=attach_extra,
    )
    return [s.to_dict() for s in secs]


def attach_sections_to_payload(
    canonical_payload: Dict[str, Any],
    *,
    chart_meta_key: str = "chart_meta",
    note_events_key: str = "note_events",
    output_key: str = "sections",
    section_count: int = 8,
    method: str = "uniform_beats",
    canonical_sections_version: str = "sectionmetrics_v1",
    attach_lane_usage: bool = True,
) -> Dict[str, Any]:
    """
    Additively attach computed sections into canonical_payload.

    This does not enforce schema; it only adds payload[output_key] if
    the required inputs exist.
    """
    payload = canonical_payload
    cm = payload.get(chart_meta_key) or {}
    ne = payload.get(note_events_key) or []

    if not isinstance(cm, dict) or not isinstance(ne, list):
        # Nothing to do
        return payload

    sections = build_sections_dicts(
        cm,
        ne,
        section_count=section_count,
        method=method,
        attach_lane_usage=attach_lane_usage,
        attach_extra=False,
    )

    payload[output_key] = sections
    payload["canonical_sections_version"] = str(canonical_sections_version)
    return payload


__all__ = [
    "compute_uniform_boundaries_by_beats",
    "compute_boundaries_from_section_markers",
    "build_sections",
    "build_sections_dicts",
    "attach_sections_to_payload",
]
