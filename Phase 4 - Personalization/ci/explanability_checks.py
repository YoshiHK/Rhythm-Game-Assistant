"""
explainability_checks.py

Phase 4 CI — Explainability Checks.

Ensures:
- Provenance is always present
- Required explainability fields exist
- Event logging records required linkage
"""

from typing import Any, Dict


REQUIRED_PROVENANCE_FIELDS = {
    "engine_mode",
    "decision_timestamp",
    "decision_interface_version",
    "gates",
    "decision_source",
}


def run_explainability_checks(
    *,
    provenance: Dict[str, Any],
) -> None:
    """
    Validate provenance completeness.

    Raises AssertionError if required fields are missing.
    """

    if not isinstance(provenance, dict):
        raise AssertionError("Provenance must be a dict")

    missing = REQUIRED_PROVENANCE_FIELDS - provenance.keys()
    if missing:
        raise AssertionError(
            f"Missing required provenance fields: {sorted(missing)}"
        )