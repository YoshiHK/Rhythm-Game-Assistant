"""
rhythm_ingestion.validators package

v2 compatibility exports (additive, non-breaking).

Supported games (SOURCE OF TRUTH):
- The authoritative list of supported games is defined in **games.json**.
- This package MUST NOT hardcode any supported game list.
- Each concrete validator MUST declare `game_id` matching an entry in games.json.
- Enable / disable / availability decisions belong to:
    games.json  → games loader  → orchestrator wiring
  NOT to validators or this package.

This ensures:
- No duplicate sources of truth
- Clean separation between configuration and implementation
- Safe evolution as new games are added (ingestion-only, tips-enabled, future)

Goals:
- Provide a stable import surface for validators.
- Preserve the legacy BaseValidator contract (exception-based).
- Expose the v2 BaseValidatorV2 contract (ValidationResult dict).
- Re-export common validator utilities for consistency and auditability.

Notes:
- Per VALIDATOR_V2_SPEC:
  - Game-specific validators MUST NOT be version-suffixed.
  - The `v2` suffix is used ONLY for shared base modules.
- This __init__.py does NOT import concrete validators to avoid
  import-time side effects and accidental auto-registration.
"""

from __future__ import annotations

# ---------------------------------------------------------------------
# Legacy base contract (exception-based)
# ---------------------------------------------------------------------
from .base_validator import BaseValidator

# ---------------------------------------------------------------------
# v2 additive base (ValidationResult-based)
# ---------------------------------------------------------------------
try:
    from .base_validator_v2 import BaseValidatorV2, ValidationResult
except Exception:  # pragma: no cover
    # Allows gradual rollout without breaking older deployments
    BaseValidatorV2 = None  # type: ignore
    ValidationResult = None  # type: ignore

# ---------------------------------------------------------------------
# Common validator utilities (pure helpers, Phase-3 safe)
# ---------------------------------------------------------------------
from .common_validator_utils import (
    safe_int,
    safe_float,
    compute_delta,
    is_within_threshold,
    values_equal,
    numeric_equal,
    build_validation_ok,
    build_validation_fail,
    compute_phase4_gate_state,
    explain_gate_failures,
)

__all__ = [
    # Base contracts
    "BaseValidator",
    "BaseValidatorV2",
    "ValidationResult",

    # Common utils
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
]
