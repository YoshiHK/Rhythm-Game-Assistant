from __future__ import annotations

"""
rhythm_ingestion.validators.common_validator_utils
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

from typing import Any, Dict, Optional, Sequence, Set


# ---------------------------------------------------------------------
# 1) Low-level numeric helpers
# ---------------------------------------------------------------------

def safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    """Best-effort conversion to int."""
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    """Best-effort conversion to float."""
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


# ---------------------------------------------------------------------
# 2) Delta computation helpers
# ---------------------------------------------------------------------

def compute_delta(a: Optional[int], b: Optional[int]) -> Optional[int]:
    """Compute |a - b| safely."""
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
    """Return whether delta <= threshold."""
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
    """Safe equality check."""
    try:
        return a == b
    except Exception:
        return None


def numeric_equal(a: Any, b: Any, *, tol: float = 0.0) -> Optional[bool]:
    """Compare two numeric-ish values with an optional tolerance."""
    af = safe_float(a)
    bf = safe_float(b)
    if af is None or bf is None:
        return None
    try:
        return abs(af - bf) <= float(tol)
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
    """
    return {
        "ok": True,
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
    """
    return {
        "ok": False,
        "errors": list(errors),
        "warnings": list(warnings or []),
        "degraded_mode": bool(degraded_mode),
    }


# ---------------------------------------------------------------------
# 6) Phase-4 gate interpretation helpers (informational only)
# ---------------------------------------------------------------------

def compute_phase4_gate_state(
    *,
    engine_mode: Optional[str],
    feature_flags: Optional[dict],
    opt_in: Optional[bool],
) -> dict:
    """
    Compute Phase-4 gate state in a PURE, informational way.

    This helper does not make runtime decisions; it only normalizes inputs
    into a compact state summary that validators can attach for diagnostics.
    """
    flags = dict(feature_flags or {})
    return {
        "engine_mode": engine_mode,
        "feature_flags_present": bool(flags),
        "feature_flags_enabled": sorted([k for k, v in flags.items() if bool(v)]),
        "opt_in": bool(opt_in) if opt_in is not None else None,
        "phase4_active": bool(opt_in) and bool(flags),
    }


# ---------------------------------------------------------------------
# 7) Explainability helpers (Validator v2 optional support)
# ---------------------------------------------------------------------

def explain_gate_failures(gate_fail_reasons: Optional[list[str]]) -> str:
    """
    Convert Phase-4 gate failure reasons into a human-readable explanation.
    """
    reasons = [str(x).strip() for x in (gate_fail_reasons or []) if str(x).strip()]
    if not reasons:
        return "No gate-failure reasons were provided."
    return "; ".join(reasons)


# ---------------------------------------------------------------------
# 8) Suggested cross-layer baseline extension helpers (optional)
# ---------------------------------------------------------------------
# NOTE:
# These are a practical alignment helper so validators can remain consistent
# with adapter-side baseline fallback extension handling.
# This is an additive engineering helper, not a source-mandated behavior.

BASELINE_FALLBACK_EXTENSIONS: Set[str] = {".html", ".mht"}


def normalize_extensions(extensions: Optional[Sequence[str]]) -> Set[str]:
    """Normalize an iterable of extensions to lower-case dotted strings."""
    out: Set[str] = set()
    for ext in extensions or []:
        if ext is None:
            continue
        e = str(ext).strip().lower()
        if not e:
            continue
        if not e.startswith("."):
            e = "." + e
        out.add(e)
    return out


def with_baseline_fallback_extensions(
    extensions: Optional[Sequence[str]] = None,
    *,
    include_baseline: bool = True,
) -> Set[str]:
    """
    Return normalized extensions with baseline fallback extensions added.
    """
    out = normalize_extensions(extensions)
    if include_baseline:
        out.update(BASELINE_FALLBACK_EXTENSIONS)
    return out


def file_matches_extensions(path: Any, extensions: Optional[Sequence[str]] = None) -> bool:
    """
    Return True if the file suffix matches the normalized extension set.
    """
    suffix = str(getattr(path, "suffix", "") or "").lower()
    allowed = with_baseline_fallback_extensions(extensions)
    return suffix in allowed


__all__ = [
    "safe_int",
    "safe_float",
    "compute_delta",
    "is_within_threshold",
    "values_equal",
    "numeric_equal",
    "build_validation_ok",
    "build_validation_fail",
    "compute_phase4_gate_state",
    "explain_gate_failures",
    "BASELINE_FALLBACK_EXTENSIONS",
    "normalize_extensions",
    "with_baseline_fallback_extensions",
    "file_matches_extensions",
]