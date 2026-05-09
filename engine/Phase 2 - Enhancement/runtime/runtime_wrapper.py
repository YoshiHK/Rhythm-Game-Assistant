"""
Phase 2 Runtime Wrapper

Provides a stable integration surface for Phase 3 Orchestrator.
"""

from .phase2_core import run_phase2


def run(payload: dict) -> dict:
    """
    Run Phase 2 enhancement as a black-box operation.
    """
    return run_phase2(payload)