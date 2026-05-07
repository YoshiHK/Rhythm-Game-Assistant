from __future__ import annotations

"""
Phase 4 Runtime Wrapper.

Stable import surface for application runtime.
"""

from .personalization_core import (
    Phase4RuntimeConfig,
    run_phase4_personalization,
)

__all__ = [
    "Phase4RuntimeConfig",
    "run_phase4_personalization",
]