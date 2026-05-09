"""
Phase 2 Runtime Layer

Deterministic execution spine for Phase 2 (Enhancement).

This package defines:
- the canonical Phase 2 execution entrypoint
- the internal stage and track routing structure
- a stable black-box interface for Phase 3 orchestration

Design principles:
- orchestration only (no domain logic)
- deterministic execution
- no mutation of Phase 1 semantics
- safe to wrap, bypass, or replace by Phase 3
"""

# Public entrypoints (intended for external callers)
from .phase2_core import run_phase2
from .runtime_wrapper import run

# Internal routing primitives (documented but not encouraged for external use)
from .stage_router import run_all_stages
from .track_router import (
    run_track_a,
    run_track_b,
    run_track_c,
    run_track_d,
)

__all__ = [
    # External / stable surface
    "run_phase2",
    "run",

    # Internal routing (exposed for testing, QA, and diagnostics)
    "run_all_stages",
    "run_track_a",
    "run_track_b",
    "run_track_c",
    "run_track_d",
]