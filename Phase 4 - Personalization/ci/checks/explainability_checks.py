"""
explainability_checks.py
Phase 4 CI — Explainability Checks (Design-Locked)

Purpose:
- Enforce explainability contract for Phase 4 personalization
- Ensure provenance is complete, explicit, and auditable

This module defines hard explainability guardrails.
Any violation here is an architectural error.
"""

from typing import Any, Dict, Set


# Required provenance keys for every Phase 4 personalization decision
REQUIRED_PROVENANCE_FIELDS: Set[str] = {
    "engine_mode",
    "decision_timestamp",
    "decision_interface_version",
    "gates",
    "decision_source",
}

# Allowed decision sources (explicit, auditable)
ALLOWED_DECISION_SOURCES: Set[str] = {
    "rule",
    "model",
    "hybrid",
}


def run_explainability_checks(
    *,
    provenance: Dict[str, Any],
) -> None:
    """
    Validate Phase 4 explainability provenance.

    Enforced invariants:
    1. Provenance object must exist and be a dict
    2. All required provenance fields must be present
    3. decision_source must be explicit and allowed
    """

    # --- 1. Provenance existence & type
    if not isinstance(provenance, dict):
        raise AssertionError(
            "Phase 4 explainability violation: provenance must be a dict"
        )

    # --- 2. Required field completeness
    missing_fields = REQUIRED_PROVENANCE_FIELDS - provenance.keys()
    if missing_fields:
        raise AssertionError(
            "Phase 4 explainability violation: missing provenance fields "
            f"{sorted(missing_fields)}"
        )

    # --- 3. decision_source validity
    decision_source = provenance.get("decision_source")
    if not isinstance(decision_source, str) or decision_source not in ALLOWED_DECISION_SOURCES:
        raise AssertionError(
            "Phase 4 explainability violation: invalid decision_source "
            f"(got={decision_source!r}, allowed={sorted(ALLOWED_DECISION_SOURCES)})"
        )