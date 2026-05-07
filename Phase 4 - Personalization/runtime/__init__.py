"""
Phase 4 — Runtime Layer (deterministic execution spine).

This package provides the ONLY supported runtime entrypoints for Phase 4:
- run_phase4_personalization (end-to-end)
- Phase4RuntimeConfig (runtime configuration)

Hard rules:
- Do NOT import curator.* from runtime
- Do NOT perform IO persistence
- Deterministic fallback must always exist
"""

from .personalization_core import (
    Phase4RuntimeConfig,
    run_phase4_personalization,
)

__all__ = [
    "Phase4RuntimeConfig",
    "run_phase4_personalization",
]