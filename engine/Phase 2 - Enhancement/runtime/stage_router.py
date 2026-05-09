"""
Phase 2 Stage Router

Executes Phase 2 stages in canonical order.
"""

from .track_router import (
    run_track_a,
    run_track_b,
    run_track_c,
    run_track_d,
)


def run_all_stages(payload: dict) -> dict:
    """
    Execute all Phase 2 stages sequentially.
    """
    payload = run_track_a(payload)  # Stage 5.1
    payload = run_track_b(payload)  # Stage 5.2
    payload = run_track_c(payload)  # Stage 5.3
    payload = run_track_d(payload)  # Stage 6
    return payload