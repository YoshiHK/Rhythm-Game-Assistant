"""
safety_checks.py
Phase 4 CI — Safety Checks (Design-Locked)

Purpose:
- Ensure Phase 4 personalization does not mutate semantic meaning
- Enforce presentation-only personalization constraints

This module defines hard guardrails.
Any violation here is an architectural error.
"""

from typing import Any, Dict, List, Set


# Fields that MUST NOT change during personalization
IMMUTABLE_FIELDS: Set[str] = {
    "severity",
    "score",
    "coverage",
    "guidance",
}


def _extract_semantic_snapshot(
    elements: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    Extract a semantic snapshot keyed by element_id.

    Snapshot contains only immutable semantic fields.
    """
    snapshot: Dict[str, Dict[str, Any]] = {}

    for el in elements:
        eid = el.get("element_id")
        if not isinstance(eid, str):
            raise AssertionError(
                "Phase 4 safety violation: element missing valid element_id"
            )

        snap = {k: el.get(k) for k in IMMUTABLE_FIELDS if k in el}
        snapshot[eid] = snap

    return snapshot


def run_safety_checks(
    *,
    base_elements: List[Dict[str, Any]],
    personalized_elements: List[Dict[str, Any]],
) -> None:
    """
    Compare base vs personalized outputs for safety.

    Enforced invariants:
    1. Element count must not change
    2. Element identity (element_id set) must not change
    3. Immutable semantic fields must not change
    """

    # --- 1. Element count invariant
    if len(base_elements) != len(personalized_elements):
        raise AssertionError(
            f"Phase 4 safety violation: element count changed "
            f"(base={len(base_elements)}, personalized={len(personalized_elements)})"
        )

    # --- 2. Element identity invariant
    base_ids = {el.get("element_id") for el in base_elements}
    out_ids = {el.get("element_id") for el in personalized_elements}

    if base_ids != out_ids:
        missing = base_ids - out_ids
        extra = out_ids - base_ids
        raise AssertionError(
            "Phase 4 safety violation: element identity changed "
            f"(missing={sorted(missing)}, extra={sorted(extra)})"
        )

    # --- 3. Semantic immutability invariant
    base_snapshot = _extract_semantic_snapshot(base_elements)
    out_snapshot = _extract_semantic_snapshot(personalized_elements)

    if base_snapshot != out_snapshot:
        diffs = []
        for eid in base_snapshot:
            if base_snapshot[eid] != out_snapshot.get(eid):
                diffs.append(
                    {
                        "element_id": eid,
                        "before": base_snapshot[eid],
                        "after": out_snapshot.get(eid),
                    }
                )

        raise AssertionError(
            "Phase 4 safety violation: immutable semantic fields modified "
            f"(diffs={diffs})"
        )