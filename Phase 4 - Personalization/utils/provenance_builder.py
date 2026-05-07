from __future__ import annotations

"""
provenance_builder.py

Phase 4 — Provenance helper utilities.

These helpers assist in constructing and merging provenance dictionaries
that conform to PHASE_4_PROVENANCE.schema.json.

This module:
- does NOT perform validation
- does NOT write logs
- does NOT mutate input provenance dicts
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_base_provenance(
    *,
    engine_mode: str,
    decision_interface_version: str,
    gates: Dict[str, Any],
    decision_source: str = "rule",
    model_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a base Phase 4 provenance object.

    Intended to be called after the Personalization Decision step.
    """

    prov: Dict[str, Any] = {
        "engine_mode": str(engine_mode),
        "decision_timestamp": _utc_now_iso(),
        "decision_interface_version": str(decision_interface_version),
        "gates": dict(gates),
        "decision_source": str(decision_source),
    }

    if model_metadata is not None:
        prov["model_metadata"] = dict(model_metadata)

    return prov


def merge_adjustment_provenance(
    *,
    base_provenance: Dict[str, Any],
    adjustments: Dict[str, Any],
    safe_adjustment_applied: bool,
    explainability: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Merge adjustment-related fields into an existing provenance dict.

    Returns a NEW dict (does not mutate base_provenance).
    """

    merged: Dict[str, Any] = dict(base_provenance)

    merged["adjustments"] = dict(adjustments) if adjustments else {}
    merged["safe_adjustment_applied"] = bool(safe_adjustment_applied)

    if explainability is not None:
        merged["explainability"] = dict(explainability)

    return merged


__all__ = [
    "build_base_provenance",
    "merge_adjustment_provenance",
]