from __future__ import annotations

from typing import Any, Dict

ALLOWED_KEYS = {
    "element_ordering",
    "ranking_weights",
    "narrative_template_id",
    "variant_id",
}


def validate_directives(directives: Dict[str, Any]) -> bool:
    if not isinstance(directives, dict):
        return False

    for k in directives.keys():
        if k not in ALLOWED_KEYS:
            return False

    if "element_ordering" in directives and not isinstance(directives.get("element_ordering"), list):
        return False

    if "ranking_weights" in directives and not isinstance(directives.get("ranking_weights"), dict):
        return False

    return True