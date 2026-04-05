"""
section_utils.py

Shared utility helpers for SectionMetrics (Stage 2–4.1).

This module contains small, pure helper functions used by section builders
and related QA / analysis code.

Responsibilities:
- Safe numeric conversions
- Range / window helpers
- Normalization utilities
- Deterministic math helpers

This module MUST NOT:
- perform section slicing by itself
- depend on adapters, validators, or orchestrator
- infer gameplay semantics
- mutate canonical payloads
"""

from __future__ import annotations

from typing import Any, Iterable, List, Sequence, Tuple


# -------------------------------------------------
# Safe conversions
# -------------------------------------------------

def safe_float(x: Any, default: float = 0.0) -> float:
    """Safely convert x to float, returning default on failure."""
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def safe_int(x: Any, default: int = 0) -> int:
    """Safely convert x to int, returning default on failure."""
    try:
        if x is None:
            return default
        # avoid bool -> int coercion
        if isinstance(x, bool):
            return default
        return int(x)
    except Exception:
        return default


# -------------------------------------------------
# Range / window helpers
# -------------------------------------------------

def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamp value into [min_value, max_value]."""
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


def is_in_window(
    time_value: float,
    start: float,
    end: float,
    *,
    inclusive_start: bool = True,
    inclusive_end: bool = False,
) -> bool:
    """
    Check whether time_value lies in a window.

    Default semantics match section slicing:
      [start, end)
    """
    if inclusive_start:
        if time_value < start:
            return False
    else:
        if time_value <= start:
            return False

    if inclusive_end:
        if time_value > end:
            return False
    else:
        if time_value >= end:
            return False

    return True


def window_duration(start: float, end: float) -> float:
    """Return non-negative window duration."""
    return max(0.0, end - start)


# -------------------------------------------------
# List / aggregation helpers
# -------------------------------------------------

def safe_mean(values: Sequence[float]) -> float:
    """Compute mean of values; return 0.0 if empty."""
    if not values:
        return 0.0
    return sum(values) / float(len(values))


def safe_sum(values: Sequence[float]) -> float:
    """Compute sum safely (empty -> 0.0)."""
    return float(sum(values)) if values else 0.0


def normalize_ratio(numerator: float, denominator: float) -> float:
    """
    Return numerator / denominator in [0,1], handling zero denominator.
    """
    if denominator <= 0.0:
        return 0.0
    return clamp(numerator / denominator, 0.0, 1.0)


# -------------------------------------------------
# Lane / bucket helpers
# -------------------------------------------------

def normalize_lane_id(lane: Any) -> str:
    """
    Normalize lane identifier into a stable string key.
    Intended for JSON-safe lane usage maps.
    """
    try:
        if isinstance(lane, bool):
            return "unknown"
        if isinstance(lane, (int, float)):
            return str(int(round(float(lane))))
        return str(lane)
    except Exception:
        return "unknown"


def increment_bucket(buckets: dict, key: str, amount: int = 1) -> None:
    """Increment a counter bucket in-place."""
    if key in buckets:
        buckets[key] += amount
    else:
        buckets[key] = amount


# -------------------------------------------------
# Coverage / density helpers
# -------------------------------------------------

def compute_density(count: int, duration: float) -> float:
    """Compute count / duration safely."""
    if duration <= 0.0:
        return 0.0
    return float(count) / float(duration)


def compute_coverage(count: int, total: int) -> float:
    """Compute count / total safely, normalized to [0,1]."""
    if total <= 0:
        return 0.0
    return clamp(float(count) / float(total), 0.0, 1.0)


# -------------------------------------------------
# Boundary helpers
# -------------------------------------------------

def merge_adjacent_windows(
    windows: Sequence[Tuple[float, float]],
    *,
    tolerance: float = 1e-9,
) -> List[Tuple[float, float]]:
    """
    Merge adjacent or overlapping windows.

    Useful when upstream boundaries have floating-point drift.
    """
    if not windows:
        return []

    sorted_windows = sorted(windows, key=lambda w: (w[0], w[1]))
    merged: List[Tuple[float, float]] = []

    cur_start, cur_end = sorted_windows[0]
    for start, end in sorted_windows[1:]:
        if start <= cur_end + tolerance:
            cur_end = max(cur_end, end)
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = start, end

    merged.append((cur_start, cur_end))
    return merged


__all__ = [
    "safe_float",
    "safe_int",
    "clamp",
    "is_in_window",
    "window_duration",
    "safe_mean",
    "safe_sum",
    "normalize_ratio",
    "normalize_lane_id",
    "increment_bucket",
    "compute_density",
    "compute_coverage",
    "merge_adjacent_windows",
]
