"""rhythm_ingestion.orchestrator_ext.run_plan

Booster: assemble a RunPlan from mode, flags, and capabilities.
"""

from __future__ import annotations

from typing import Optional

from .types import CapabilityMatrix, RunMode, RunPlan, Stage


def assemble_run_plan(*, mode: RunMode, capability_matrix: Optional[CapabilityMatrix] = None, enable_reasoned_gates: bool = False) -> RunPlan:
    if mode == RunMode.INGEST:
        stages = [Stage.INGEST, Stage.VALIDATE, Stage.APPROACHABILITY]
    elif mode == RunMode.TIPS:
        stages = [Stage.INGEST, Stage.VALIDATE, Stage.APPROACHABILITY, Stage.PHASE1, Stage.PHASE2]
    elif mode == RunMode.PERSONALIZED:
        stages = [Stage.INGEST, Stage.VALIDATE, Stage.APPROACHABILITY, Stage.PHASE1, Stage.PHASE2, Stage.PHASE4]
    else:
        stages = [Stage.INGEST, Stage.VALIDATE, Stage.APPROACHABILITY, Stage.PHASE1, Stage.PHASE2, Stage.PHASE4]

    return RunPlan(mode=mode, stages=stages, gates_enabled=bool(enable_reasoned_gates), degraded_mode=False, capability_matrix=capability_matrix)
