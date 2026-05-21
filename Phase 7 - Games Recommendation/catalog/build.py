"""
build.py
Phase 7 — LEGACY / TOOLING ONLY

⚠️ This file is NOT part of the Phase 7 runtime path.

It is retained for:
- early experiments
- local prototyping
- historical reference

Phase 7 runtime wiring is now owned by:
- Phase 6 integration
- routing/
- registry/
- contracts/
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# NOTE:
# Intentionally NOT importing routing / ranking / explanation layers.
# This avoids accidental runtime usage.


def build_registry_from_dict(raw: Dict[str, Any]):
    """
    LEGACY helper — do not use in production.

    Use:
      registry.load_games_registry()
    instead.
    """
    raise RuntimeError(
        "build_registry_from_dict is deprecated. "
        "Use registry.load_games_registry(...) instead."
    )


def build_phase7_router(
    *,
    config: Optional[Any] = None,
    registry: Optional[Any] = None,
    ranker: Optional[Any] = None,
    explainer: Optional[Any] = None,
):
    """
    LEGACY helper — do not use in production.

    Phase 7 routers are now constructed explicitly via:
    - registry
    - routing policy
    - ranker
    - explainer

    under Phase 6 control.
    """
    raise RuntimeError(
        "build_phase7_router is deprecated. "
        "Phase 7 routing is owned by Phase 6 integration."
    )
