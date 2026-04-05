"""rhythm_ingestion.validators.common_validator_utils

Shared validator utilities for UMI Phase 3 (foundation-layer helper).

Scope:
- Pure, lightweight helpers used by multiple game validators.
- MUST NOT modify any Phase 1/2 logic.
- MUST NOT raise validation exceptions or decide pass/fail outcomes.
- No IO, no registry lookups, no dependency on concrete validators.

This module is intentionally parallel to adapters/common_adapter_utils.py:
- adapters aggregate/attach (diagnostics/internal metadata)
- validators compute/compare (deltas/equality/threshold checks)

All functions here return values that validators may use to build their own
error lists and enforcement policies.
"""

from __future__ import annotations

from typing import Any, Optional


# ---------------------------------------------------------------------
# 1) Low-level numeric helpers
# ---------------------------------------------------------------------

def safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    """Best-effort conversion to int.

    Returns default if conversion is not possible.
    """
    try:
        if value is None:
            return default
        # Avoid converting booleans to 1/0 implicitly
        if isinstance(value, bool):
            return default
        return int(value)
    except Exception:
        return default


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """Best-effort conversion to float.

    Returns default if conversion is not possible.
    """
    try:
        if value is None:
            return default
        if isinstance(value, bool):
            return default
        return float(value)
    except Exception:
        return default


# ---------------------------------------------------------------------
# 2) Delta computation helpers
# ---------------------------------------------------------------------

def compute_delta(a: Optional[int], b: Optional[int]) -> Optional[int]:
    """Compute |a - b| safely.

    Returns None if either input is None.
    """
    if a is None or b is None:
        return None
    try:
        return abs(int(a) - int(b))
    except Exception:
        return None


# ---------------------------------------------------------------------
# 3) Threshold comparison helpers
# ---------------------------------------------------------------------

def is_within_threshold(delta: Optional[int], threshold: int) -> Optional[bool]:
    """Return whether delta <= threshold.

    Returns None if delta is None.

    Note: This function does not decide what to do when False; validators do.
    """
    if delta is None:
        return None
    try:
        return int(delta) <= int(threshold)
    except Exception:
        return None


# ---------------------------------------------------------------------
# 4) Symmetry / parity helpers
# ---------------------------------------------------------------------

def values_equal(a: Any, b: Any) -> Optional[bool]:
    """Safe equality check.

    - Returns None if either value is None.
    - Otherwise returns (a == b).

    Intended for exact parity checks when types are already normalized.
    """
    if a is None or b is None:
        return None
    try:
        return a == b
    except Exception:
        return None


def numeric_equal(a: Any, b: Any, *, tol: float = 0.0) -> Optional[bool]:
    """Compare two numeric-ish values with an optional tolerance.

    - Returns None if either value cannot be converted to float.
    - If tol <= 0, uses exact float equality.
    - If tol > 0, returns abs(a-b) <= tol.

    Useful for BPM/duration comparisons across payload/row/DB values.
    """
    fa = safe_float(a, default=None)
    fb = safe_float(b, default=None)
    if fa is None or fb is None:
        return None
    try:
        t = float(tol or 0.0)
        if t <= 0.0:
            return float(fa) == float(fb)
        return abs(float(fa) - float(fb)) <= t
    except Exception:
        return None

# ---------------------------------------------------------------------
# 5) ValidationResult builders (Validator v2 spec helpers)
# ---------------------------------------------------------------------

def build_validation_ok(
    *,
    warnings: Optional[list[str]] = None,
    degraded_mode: bool = False,
) -> dict:
    """
    Build a successful ValidationResult dict.

    This helper does NOT decide whether a chart should pass.
    It only standardizes the output shape for validators.

    Aligned with VALIDATOR_V2_SPEC.md.
    """
    return {
        "supported": True,
        "errors": [],
        "warnings": list(warnings or []),
        "degraded_mode": bool(degraded_mode),
    }


def build_validation_fail(
    *,
    errors: list[str],
    warnings: Optional[list[str]] = None,
    degraded_mode: bool = False,
) -> dict:
    """
    Build a failed ValidationResult dict.

    Validators decide *when* to call this.
    This helper only standardizes the shape.
    """
    return {
        "supported": False,
        "errors": list(errors),
        "warnings": list(warnings or []),
        "degraded_mode": bool(degraded_mode),
    }


# ---------------------------------------------------------------------
# 6) Phase‑4 gate interpretation helpers (informational only)
# ---------------------------------------------------------------------

def compute_phase4_gate_state(
    *,
    engine_mode: Optional[str],
    feature_flags: Optional[dict],
    opt_in: Optional[bool],
) -> dict:
    """
    Compute Phase‑4 gate state in a PURE, informational way.

    This helper mirrors Phase‑4 deterministic gating logic,
    but does NOT execute Phase‑4 or enforce behavior.

    Intended usage:
    - Validators may attach warnings
    - Validators may set degraded_mode
    - Validators may explain why personalization will not apply

    Returns a dict safe to include in diagnostics or explanations.
    """
    mode = (engine_mode or "deterministic").strip().lower()
    flags = feature_flags or {}

    phase4_enabled = bool(flags.get("phase4_enabled", True))

    gate_fail_reasons: list[str] = []

    if not phase4_enabled:
        gate_fail_reasons.append("FLAG_DISABLED")

    if opt_in is False:
        gate_fail_reasons.append("OPT_OUT")

    personalization_allowed = (
        mode == "personalized"
        and phase4_enabled
        and opt_in is not False
    )

    return {
        "engine_mode": mode,
        "phase4_enabled": phase4_enabled,
        "personalization_allowed": personalization_allowed,
        "gate_fail_reasons": gate_fail_reasons,
    }


# ---------------------------------------------------------------------
# 7) Explainability helpers (Validator v2 optional support)
# ---------------------------------------------------------------------

def explain_gate_failures(gate_fail_reasons: Optional[list[str]]) -> str:
    """
    Convert Phase‑4 gate failure reasons into a human‑readable explanation.

    Intended for Validator.explain_failure() implementations.
    """
    reasons = list(gate_fail_reasons or [])
    if not reasons:
        return ""

    if "FLAG_DISABLED" in reasons:
        return (
            "Personalization is currently disabled by feature flags. "
            "Deterministic tips will be used."
        )

    if "OPT_OUT" in reasons:
        return (
            "The player has opted out of personalization. "
            "Deterministic tips will be used."
        )

    return (
        "Personalization is unavailable due to gating conditions. "
        "Deterministic tips will be used."
    )


# ---------------------------------------------------------------------
# Public exports (additive)
# ---------------------------------------------------------------------

__all__ += [
    "build_validation_ok",
    "build_validation_fail",
    "compute_phase4_gate_state",
    "explain_gate_failures",
]

__all__ = [
    "safe_int",
    "safe_float",
    "compute_delta",
    "is_within_threshold",
    "values_equal",
    "numeric_equal",
]
