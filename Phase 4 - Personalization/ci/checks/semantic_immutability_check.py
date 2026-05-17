"""
semantic_immutability_check.py
Phase 4 CI — Semantic Immutability (Design-Locked)

Purpose:
- Ensure Phase 4 does NOT alter semantic structure
- Enforce strict element identity preservation

Any violation is an architectural error.
"""

from typing import Any, Dict, List

# ✅ Fields that define element identity (must never change)
IDENTITY_FIELDS = {
    "element_id",
    "element_type",
}

# ✅ Fields that define semantic meaning (must never change)
SEMANTIC_FIELDS = {
    "severity",
    "score",
    "coverage",
    "guidance",
    "matched_tags",
}


def run_semantic_immutability_checks(
    *,
    base_elements: List[Dict[str, Any]],
    personalized_elements: List[Dict[str, Any]],
) -> None:

    if len(base_elements) != len(personalized_elements):
        raise AssertionError(
            "Semantic Immutability FAIL: element count mismatch"
        )

    base_map = {e["element_id"]: e for e in base_elements}
    personalized_map = {e["element_id"]: e for e in personalized_elements}

    if set(base_map.keys()) != set(personalized_map.keys()):
        raise AssertionError(
            "Semantic Immutability FAIL: element_id set mismatch"
        )

    for element_id in base_map:

        base = base_map[element_id]
        cur = personalized_map[element_id]

        # ✅ Identity fields must match exactly
        for field in IDENTITY_FIELDS:
            if base.get(field) != cur.get(field):
                raise AssertionError(
                    f"Semantic Immutability FAIL: identity field '{field}' changed for {element_id}"
                )

        # ✅ Semantic fields must match exactly
        for field in SEMANTIC_FIELDS:
            if base.get(field) != cur.get(field):
                raise AssertionError(
                    f"Semantic Immutability FAIL: semantic field '{field}' changed for {element_id}"
                )