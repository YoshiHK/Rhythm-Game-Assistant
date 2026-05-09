"""
routing_debug.py (Phase 2)

Provides lightweight routing and execution state snapshots.

This module is observational only.
"""

from __future__ import annotations
from typing import Dict, Any


def snapshot_routing_state(
    *,
    stage: str,
    track: str | None = None,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Capture a routing snapshot for debugging or diagnostics.
    """
    return {
        "stage": stage,
        "track": track,
        "extra": extra or {},
    }


__all__ = ["snapshot_routing_state"]