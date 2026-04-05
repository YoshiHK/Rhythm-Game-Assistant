"""rhythm_ingestion.orchestrator_ext.reason_codes

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

    # Schema/Structure
    SCHEMA_INVALID = "SCHEMA_INVALID"
    NOTE_EVENTS_EMPTY = "NOTE_EVENTS_EMPTY"
    CHART_META_INVALID = "CHART_META_INVALID"

    # Approachability Gate
    APPROACHABILITY_FAIL_INSUFFICIENT_STRUCTURE = "APPROACHABILITY_FAIL_INSUFFICIENT_STRUCTURE"
    APPROACHABILITY_FAIL_UNSUPPORTED_MODEL = "APPROACHABILITY_FAIL_UNSUPPORTED_MODEL"

    # Tips Pipeline (control-plane only)
    TIPS_DISABLED_FOR_GAME = "TIPS_DISABLED_FOR_GAME"
    PATTERN_TAXONOMY_INCOMPLETE = "PATTERN_TAXONOMY_INCOMPLETE"
    SECTIONS_UNAVAILABLE = "SECTIONS_UNAVAILABLE"

    # Personalization
    PHASE4_FLAG_DISABLED = "PHASE4_FLAG_DISABLED"
    PHASE4_OPT_OUT = "PHASE4_OPT_OUT"
    PHASE4_GATING_FAIL = "PHASE4_GATING_FAIL"

    # Operational
    IO_TRANSIENT_FAILURE = "IO_TRANSIENT_FAILURE"
    TIMEOUT = "TIMEOUT"
    UNHANDLED_EXCEPTION = "UNHANDLED_EXCEPTION"
