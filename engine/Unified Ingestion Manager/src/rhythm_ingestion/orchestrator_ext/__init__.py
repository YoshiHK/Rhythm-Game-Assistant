"""
rhythm_ingestion.orchestrator_ext

Stable extension surface for orchestrator integration.

This package provides:
- a single stable bridge entrypoint,
- additive control-plane extensions,
- zero gameplay semantics.

If all feature flags are disabled, behavior is a thin pass-through.
"""

from .bridge import OrchestratorBridge, wrap_orchestrator
from .config import OrchestratorExtensionConfig
from .feature_flags import FeatureFlags
from .types import (
    RunMode,
    Stage,
    GateDecision,
    StageStatus,
    GateResult,
    StageResult,
    RunPlan,
    RunReport,
    RunContext,
    compute_run_key,
    compute_run_key_sha256,
)
from .reason_codes import ReasonCode

__all__ = [
    # Bridge (primary entrypoint)
    "OrchestratorBridge",
    "wrap_orchestrator",

    # Config & flags
    "OrchestratorExtensionConfig",
    "FeatureFlags",

    # Control-plane types
    "RunMode",
    "Stage",
    "GateDecision",
    "StageStatus",
    "GateResult",
    "StageResult",
    "RunPlan",
    "RunReport",
    "RunContext",
    "compute_run_key",
    "compute_run_key_sha256",

    # Reason codes
    "ReasonCode",
]