"""
safety_checks.py

Phase 4 CI — Safety Checks.

Ensures:
- No creation or deletion of elements
- No modification of semantic fields (severity, score, guidance)
- Adjustments remain presentation-only
"""

from typing import Any, Dict, List


IMMUTABLE_FIELDS = {
    "severity",
    "score",
    "coverage",
    "guidance",
}


def _extract_semantic_snapshot(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    snapshot = []
    for el in elements:
        snap = {k: el.get(k) for k in IMMUTABLE_FIELDS if k in el}
        snapshot.append(snap)
    return snapshot


def run_safety_checks(
    *,
    base_elements: List[Dict[str, Any]],
    personalized_elements: List[Dict[str, Any]],
) -> None:
    """
    Compare base vs personalized outputs for safety.

    Raises AssertionError if semantic drift is detected.
    """

    if len(base_elements) != len(personalized_elements):
        raise AssertionError("Element count changed by personalization")

    base_snapshot = _extract_semantic_snapshot(base_elements)
    personalized_snapshot = _extract_semantic_snapshot(personalized_elements)

    if base_snapshot != personalized_snapshot:
        raise AssertionError("Semantic fields were modified by personalization")