from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class DeploymentGateConfig:
    """
    Configuration for deployment gate enforcement.
    """
    require_guard_pass: bool = True
    require_training_success: bool = True
    allow_no_data: bool = False


@dataclass(frozen=True)
class DeploymentDecision:
    allowed: bool
    reason: str
    details: Dict[str, Any]


def evaluate_deployment_eligibility(
    pipeline_result: Dict[str, Any],
    *,
    config: DeploymentGateConfig = DeploymentGateConfig(),
) -> Dict[str, Any]:
    """
    Determine whether a Phase 5 pipeline result is safe to deploy.

    Input:
    - pipeline_result (output from orchestrator)

    Output:
    {
        "allowed": bool,
        "reason": "...",
        "details": {...}
    }
    """

    if not isinstance(pipeline_result, dict):
        return _deny("invalid_result_object")

    status = pipeline_result.get("status")
    summary = pipeline_result.get("summary") or {}

    training = summary.get("training") or {}
    evaluation = summary.get("evaluation") or {}

    guard_pass = evaluation.get("guard_pass")
    used_defaults = training.get("used_defaults")

    # ------------------------------------------------------------------
    # Rule 1: must have valid pipeline status
    # ------------------------------------------------------------------
    if status not in {"OK", "GUARD_FAIL", "NO_DATA"}:
        return _deny("unknown_status", extra={"status": status})

    # ------------------------------------------------------------------
    # Rule 2: no data
    # ------------------------------------------------------------------
    if status == "NO_DATA":
        if config.allow_no_data:
            return _allow("no_data_allowed")
        return _deny("no_data_not_allowed")

    # ------------------------------------------------------------------
    # Rule 3: regression guard
    # ------------------------------------------------------------------
    if config.require_guard_pass:
        if not guard_pass:
            return _deny(
                "evaluation_guard_failed",
                extra={"guard_pass": guard_pass},
            )

    # ------------------------------------------------------------------
    # Rule 4: training sanity
    # ------------------------------------------------------------------
    if config.require_training_success:
        # If everything fell back to defaults, treat as weak signal
        if used_defaults is True:
            return _deny(
                "insufficient_learning_signal",
                extra={"used_defaults": used_defaults},
            )

    # ------------------------------------------------------------------
    # Passed all checks
    # ------------------------------------------------------------------
    return _allow("deployment_allowed")


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _allow(reason: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "allowed": True,
        "reason": reason,
        "details": extra or {},
    }


def _deny(reason: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "allowed": False,
        "reason": reason,
        "details": extra or {},
    }


__all__ = [
    "DeploymentGateConfig",
    "DeploymentDecision",
    "evaluate_deployment_eligibility",
]