"""
Phase 2 execution flow.
"""

from .stage_router import run_all_stages


def run_phase2(canonical_payload: dict) -> dict:
    """
    Entry point for Phase 2 enhancement.

    Phase 2 Core Runtime.
    """
    return run_all_stages(canonical_payload)