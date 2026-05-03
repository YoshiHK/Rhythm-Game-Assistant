# presentation/badges.py
# Phase 3 presentation helpers (UI metadata only)

from typing import Dict
from config.games_loader import _normalize_status_for_priority


STATUS_BADGES: Dict[str, Dict[str, str]] = {
    "rulebook": {"label": "Rulebook", "color": "purple"},
    "anchor": {"label": "Anchor", "color": "blue"},
    "enabled": {"label": "Supported", "color": "green"},
    "disabled": {"label": "Disabled", "color": "gray"},
    "future": {"label": "Coming Soon", "color": "orange"},
}

CAPABILITY_BADGES: Dict[str, Dict[str, str]] = {
    "rulebook": {"label": "Rulebook", "color": "purple"},
    "anchor": {"label": "Anchor", "color": "blue"},
    "enabled": {"label": "Enabled", "color": "green"},
    # ready ≠ new capability, just UI nuance
    "ready": {"label": "Ready", "color": "green-outline"},
    "disabled": {"label": "Disabled", "color": "gray"},
    "future": {"label": "Planned", "color": "orange"},
}


def get_status_badge(status: str) -> Dict[str, str]:
    """
    Map overall_status -> UI badge.
    """
    s = _normalize_status_for_priority(status)
    return dict(STATUS_BADGES.get(s, {"label": s or "Unknown", "color": "gray"}))


def get_capability_badge(value: str) -> Dict[str, str]:
    """
    Map capability value -> UI badge.
    """
    raw = (value or "").strip().lower()
    if raw == "ready":
        return dict(CAPABILITY_BADGES["ready"])

    s = _normalize_status_for_priority(raw)
    return dict(CAPABILITY_BADGES.get(s, {"label": s or "Unknown", "color": "gray"}))