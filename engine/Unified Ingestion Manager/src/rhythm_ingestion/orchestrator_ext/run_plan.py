"""
rhythm_ingestion.orchestrator_ext.run_plan

Booster: assemble a RunPlan from mode and capabilities.

- Deterministic
- No I/O
- No gameplay semantics
"""

from __future__ import annotations

from typing import Optional

from .types import CapabilityMatrix, RunMode, RunPlan, Stage


def assemble_run_plan(
    *,
    mode: RunMode,
    capability_matrix: Optional[CapabilityMatrix] = None,
    enable_reasoned_gates: bool = False,
) -> RunPlan:
    """
    Assemble a RunPlan based on RunMode.

    This function defines the control-plane stage order only.
    It must not call into any phase logic.
    """
    if mode == RunMode.INGEST:
        stages = [Stage.INGEST, Stage.VALIDATE, Stage.APPROACHABILITY]
    elif mode == RunMode.TIPS:
        stages = [
            Stage.INGEST,
            Stage.VALIDATE,
            Stage.APPROACHABILITY,
            Stage.PHASE1,
            Stage.PHASE2,
        ]
    elif mode == RunMode.PERSONALIZED:
        stages = [
            Stage.INGEST,
            Stage.VALIDATE,
            Stage.APPROACHABILITY,
            Stage.PHASE1,
            Stage.PHASE2,
            Stage.PHASE4,
        ]
    else:
        # Safe default: treat as personalized pipeline (downstream-only, additive)
        stages = [
            Stage.INGEST,
            Stage.VALIDATE,
            Stage.APPROACHABILITY,
            Stage.PHASE1,
            Stage.PHASE2,
            Stage.PHASE4,
        ]

    return RunPlan(
        mode=mode,
        stages=stages,
        gates_enabled=bool(enable_reasoned_gates),
        degraded_mode=False,
        capability_matrix=capability_matrix,
    )


__all__ = ["assemble_run_plan"]