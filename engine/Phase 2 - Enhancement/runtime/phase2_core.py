""" Phase 2 execution flow. """

from .stage_router import run_all_stages


def run_phase2(canonical_payload: dict) -> dict:
    """
    Entry point for Phase 2 enhancement.

    Input:
      - canonical_payload (dict): Phase 1 output payload

    Output:
      - enhanced_payload (dict): Phase 2 enriched output
    """
    return run_all_stages(canonical_payload)
Phase 2 Core Runtime

