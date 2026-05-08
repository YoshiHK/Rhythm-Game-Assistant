## proseka_element_selector.py
## Portable schema-driven element selector

from __future__ import annotations
from typing import List, Dict, Any
import json

SEVERITY_ORDER = [
    "slight",
    "light",
    "mild",
    "moderate",
    "dense",
    "complex",
    "demanding",
]
SEV_INDEX = {s: i for i, s in enumerate(SEVERITY_ORDER)}


def severity_rank(s: str) -> int:
    return SEV_INDEX.get(s, 0)


def load_schema(
    path: str = "proseka_internal_analysis_schema_v1.4.0.json",
) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def select_elements(
    elements_skeleton: List[Dict[str, Any]],
    difficulty: str,
    schema_path: str = "proseka_internal_analysis_schema_v1.4.0.json",
):
    schema = load_schema(schema_path)
    rules = schema["element_selection_rules"]

    min_sev_rank = severity_rank(rules["min_severity"])
    score_ratio = rules["score_ratio_threshold"]
    target = rules["target_count"][difficulty]

    # NOTE: selection logic intentionally omitted (handled elsewhere)
    return elements_skeleton