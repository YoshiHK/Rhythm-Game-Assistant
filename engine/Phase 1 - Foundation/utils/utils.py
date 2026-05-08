"""
Phase 1 Foundation – Utils

Shared utility helpers used across Phase 1 Foundation layers.

Design principles:
- Non-decisional
- Deterministic
- Side-effect free
- No business logic
- No orchestration responsibility

This module is LOCKED.
Do not extend with new logic; enhancements belong to Phase 2+.
"""

from typing import Any, Dict, Iterable, List, Optional


def safe_get(d: Optional[Dict[str, Any]], key: str, default: Any = None) -> Any:
    """
    Safely retrieve a value from a dict-like object.

    Returns default if:
    - d is None
    - d is not a dict
    - key does not exist
    """
    if not isinstance(d, dict):
        return default
    return d.get(key, default)


def ensure_list(value: Any) -> List[Any]:
    """
    Ensure the returned value is a list.

    - None -> []
    - list -> list
    - other -> [value]
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def dedupe_preserve_order(items: Iterable[Any]) -> List[Any]:
    """
    Deduplicate items while preserving original order.

    Used for:
    - tags
    - element names
    - summary blocks
    """
    seen = set()
    out: List[Any] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    """
    Clamp a numeric value into a closed interval.

    Commonly used for:
    - scores
    - coverage ratios
    """
    try:
        v = float(value)
    except Exception:
        return min_value
    return max(min_value, min(max_value, v))


def is_non_empty_string(value: Any) -> bool:
    """
    Check whether a value is a non-empty string after stripping.
    """
    return isinstance(value, str) and bool(value.strip())