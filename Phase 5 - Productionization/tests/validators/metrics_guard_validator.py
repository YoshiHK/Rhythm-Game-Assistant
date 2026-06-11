from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


def _result(
    *,
    validator: str,
    errors: List[str],
    warnings: Optional[List[str]] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "validator": validator,
        "passed": len(errors) == 0,
        "errors": errors,
        "warnings": warnings or [],
        "details": details or {},
    }


def _to_float(x: Any) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def validate_drift(
    *,
    current_metrics: Dict[str, Any],
    baseline_metrics: Dict[str, Any],
    metric_names: Iterable[str],
    tolerance: float,
) -> Dict[str, Any]:
    """
    Validate that current metrics have not drifted away from baseline
    by more than the allowed absolute tolerance.
    """
    errors: List[str] = []
    details: Dict[str, Any] = {"checked_metrics": {}}

    for name in metric_names:
        cur = _to_float(current_metrics.get(name))
        base = _to_float(baseline_metrics.get(name))

        if cur is None or base is None:
            details["checked_metrics"][name] = {
                "status": "SKIPPED",
                "current": cur,
                "baseline": base,
            }
            continue

        delta = abs(cur - base)
        details["checked_metrics"][name] = {
            "status": "PASS" if delta <= tolerance else "FAIL",
            "current": cur,
            "baseline": base,
            "delta": delta,
            "tolerance": tolerance,
        }

        if delta > tolerance:
            errors.append(f"drift check failed for {name}: delta {delta} > tolerance {tolerance}")

    return _result(
        validator="metrics_guard_validator.drift",
        errors=errors,
        details=details,
    )


def validate_regression(
    *,
    current_metrics: Dict[str, Any],
    baseline_metrics: Optional[Dict[str, Any]],
    metric_names: Iterable[str],
    tolerance: float,
    evaluation_report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Validate that current metrics have not regressed below baseline
    by more than the allowed tolerance.

    Also checks evaluation_report.guard_pass when provided.
    """
    errors: List[str] = []
    details: Dict[str, Any] = {"checked_metrics": {}}

    if isinstance(evaluation_report, dict):
        guard_pass = evaluation_report.get("guard_pass")
        details["guard_pass"] = guard_pass
        if guard_pass is False:
            errors.append("evaluation guard failed (guard_pass == False)")

    if baseline_metrics is None:
        return _result(
            validator="metrics_guard_validator.regression",
            errors=errors,
            details=details,
        )

    for name in metric_names:
        cur = _to_float(current_metrics.get(name))
        base = _to_float(baseline_metrics.get(name))

        if cur is None or base is None:
            details["checked_metrics"][name] = {
                "status": "SKIPPED",
                "current": cur,
                "baseline": base,
            }
            continue

        delta = cur - base
        details["checked_metrics"][name] = {
            "status": "PASS" if delta >= (-1.0 * tolerance) else "FAIL",
            "current": cur,
            "baseline": base,
            "delta": delta,
            "tolerance": tolerance,
        }

        if delta < (-1.0 * tolerance):
            errors.append(f"regression check failed for {name}: delta {delta} < -{tolerance}")

    return _result(
        validator="metrics_guard_validator.regression",
        errors=errors,
        details=details,
    )


def validate_deployment_gate(deployment_decision: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate deployment decision when present.

    Expected shape:
    {
      "allowed": bool,
      "reason": "...",
      "details": {...}
    }
    """
    errors: List[str] = []
    details: Dict[str, Any] = {}

    if deployment_decision is None:
        return _result(
            validator="metrics_guard_validator.deployment_gate",
            errors=[],
            details={"status": "SKIPPED"},
        )

    if not isinstance(deployment_decision, dict):
        return _result(
            validator="metrics_guard_validator.deployment_gate",
            errors=["deployment_decision must be a dict"],
        )

    allowed = deployment_decision.get("allowed")
    details["allowed"] = allowed
    details["reason"] = deployment_decision.get("reason")

    if allowed is not True:
        errors.append("deployment gate did not allow promotion")

    return _result(
        validator="metrics_guard_validator.deployment_gate",
        errors=errors,
        details=details,
    )


def validate_metrics_guard_bundle(
    *,
    current_metrics: Dict[str, Any],
    baseline_metrics: Optional[Dict[str, Any]] = None,
    metric_names: Optional[Iterable[str]] = None,
    drift_tolerance: float = 0.10,
    regression_tolerance: float = 0.0,
    evaluation_report: Optional[Dict[str, Any]] = None,
    deployment_decision: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Aggregate drift, regression, and deployment-gate checks.
    """
    metrics = list(metric_names or ("accept_or_better_rate", "played_or_better_rate", "completed_rate", "mean_outcome_score"))

    errors: List[str] = []
    details: Dict[str, Any] = {}

    if baseline_metrics is not None:
        drift_res = validate_drift(
            current_metrics=current_metrics,
            baseline_metrics=baseline_metrics,
            metric_names=metrics,
            tolerance=drift_tolerance,
        )
        details["drift"] = drift_res
        errors.extend([f"drift: {e}" for e in drift_res["errors"]])
    else:
        details["drift"] = {
            "validator": "metrics_guard_validator.drift",
            "passed": True,
            "errors": [],
            "warnings": ["baseline_metrics not provided; drift skipped"],
            "details": {"status": "SKIPPED"},
        }

    regression_res = validate_regression(
        current_metrics=current_metrics,
        baseline_metrics=baseline_metrics,
        metric_names=metrics,
        tolerance=regression_tolerance,
        evaluation_report=evaluation_report,
    )
    details["regression"] = regression_res
    errors.extend([f"regression: {e}" for e in regression_res["errors"]])

    gate_res = validate_deployment_gate(deployment_decision)
    details["deployment_gate"] = gate_res
    errors.extend([f"deployment_gate: {e}" for e in gate_res["errors"]])

    return _result(
        validator="metrics_guard_validator.bundle",
        errors=errors,
        details=details,
    )