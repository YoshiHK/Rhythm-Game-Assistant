"""
rhythm_ingestion.orchestrator_ext.types
Interface skeleton (dataclasses + enums) for orchestrator extensions.

Control-plane only. Must not embed gameplay semantics.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .reason_codes import ReasonCode


class RunMode(str, Enum):
    INGEST = "ingest"
    TIPS = "tips"
    PERSONALIZED = "personalized"
    FULL = "full"


class Stage(str, Enum):
    INGEST = "INGEST"
    VALIDATE = "VALIDATE"
    APPROACHABILITY = "APPROACHABILITY"
    PHASE1 = "PHASE1"
    PHASE2 = "PHASE2"
    PHASE4 = "PHASE4"


class GateDecision(str, Enum):
    ALLOW = "ALLOW"
    STOP = "STOP"
    DEGRADED = "DEGRADED"


class StageStatus(str, Enum):
    OK = "OK"
    STOP = "STOP"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass(frozen=True)
class GateResult:
    decision: GateDecision
    stage: Stage
    reason_code: Optional[ReasonCode] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StageResult:
    stage: Stage
    status: StageStatus
    ms: Optional[int] = None
    gate: Optional[GateResult] = None
    warnings: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class CapabilityMatrix:
    note_model: Optional[str] = None
    supports_sections: Optional[bool] = None
    supports_variable_bpm: Optional[bool] = None
    supports_width: Optional[bool] = None
    supports_bpm_changes: Optional[bool] = None
    emits_canonical_payload: Optional[bool] = None
    time_unit: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunPlan:
    mode: RunMode
    stages: List[Stage]
    gates_enabled: bool = False
    degraded_mode: bool = False
    capability_matrix: Optional[CapabilityMatrix] = None


@dataclass(frozen=True)
class RunReport:
    run_key: str
    game_id: str
    chart_id: str
    mode: RunMode
    stage_results: List[StageResult]
    gates: List[GateResult] = field(default_factory=list)
    degraded_mode: bool = False
    warnings: List[str] = field(default_factory=list)
    diagnostics: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunContext:
    game_id: str
    chart_id: str
    difficulty: Optional[str] = None
    adapter_version: Optional[str] = None
    pipeline_version: Optional[str] = None
    feature_flags_digest: Optional[str] = None
    trace: Dict[str, Any] = field(default_factory=dict)


def coerce_run_mode(mode: Any) -> RunMode:
    """
    Coerce external mode input (string/enum) into RunMode.
    This keeps bridge + stabilizer tolerant and phase-safe.
    """
    if isinstance(mode, RunMode):
        return mode
    s = str(mode or "").strip().lower()
    for m in RunMode:
        if m.value == s:
            return m
    # Default fallback (control-plane only)
    return RunMode.FULL


def compute_run_key(ctx: RunContext) -> str:
    """
    Compute a deterministic RunKey string (caller may hash).
    Stable with respect to input field values.
    """
    parts = [
        f"game_id={ctx.game_id}",
        f"chart_id={ctx.chart_id}",
        f"difficulty={ctx.difficulty or ''}",
        f"adapter_version={ctx.adapter_version or ''}",
        f"pipeline_version={ctx.pipeline_version or ''}",
        f"flags={ctx.feature_flags_digest or ''}",
    ]
    return "|".join(parts)


def compute_run_key_sha256(ctx: RunContext) -> str:
    """
    Convenience: return a SHA256 digest of compute_run_key(ctx).
    """
    s = compute_run_key(ctx)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


__all__ = [
    "RunMode",
    "Stage",
    "GateDecision",
    "StageStatus",
    "GateResult",
    "StageResult",
    "CapabilityMatrix",
    "RunPlan",
    "RunReport",
    "RunContext",
    "coerce_run_mode",
    "compute_run_key",
    "compute_run_key_sha256",
]