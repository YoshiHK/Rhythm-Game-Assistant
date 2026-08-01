"""
rhythm_ingestion.orchestrator_ext.reason_codes
Stable reason-code enum set for orchestrator gates.

Policy:
- Additions are allowed.
- Renames/removals are not allowed.
- Codes are control-plane signals; they must not encode gameplay semantics.
"""

from __future__ import annotations

from enum import Enum


class ReasonCode(str, Enum):
    # Adapter/Registry
    ADAPTER_NOT_FOUND = "ADAPTER_NOT_FOUND"
    VALIDATOR_NOT_FOUND = "VALIDATOR_NOT_FOUND"
    UNSUPPORTED_EXTENSION = "UNSUPPORTED_EXTENSION"
    CAPABILITIES_MISMATCH = "CAPABILITIES_MISMATCH"

    # Invocation / Mode
    INVALID_MODE = "INVALID_MODE"
    UNSUPPORTED_MODE = "UNSUPPORTED_MODE"

    # Schema / Precheck
    PRECHECK_FAILED = "PRECHECK_FAILED"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    SCHEMA_MISSING = "SCHEMA_MISSING"

    # Stabilizer control-plane
    UNHANDLED_EXCEPTION = "UNHANDLED_EXCEPTION"
    RETRY_EXHAUSTED = "RETRY_EXHAUSTED"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    SAFE_FALLBACK_USED = "SAFE_FALLBACK_USED"
    DEGRADED_MODE = "DEGRADED_MODE"


__all__ = ["ReasonCode"]