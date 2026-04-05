# proseka_element_selector.py
# Portable schema-driven element selector
from __future__ import annotations
from typing import List, Dict, Any
import json

SEVERITY_ORDER = ["slight","light","mild","moderate","dense","complex","demanding"]
SEV_INDEX = {s:i for i,s in enumerate(SEVERITY_ORDER)}

def severity_rank(s): return SEV_INDEX.get(s,0)

def load_schema(path="proseka_internal_analysis_schema_v1.4.0.json"):
    with open(path,"r",encoding="utf-8") as f: return json.load(f)

def select_elements(elements_skeleton: List[Dict[str,Any]], difficulty: str,
                    schema_path="proseka_internal_analysis_schema_v1.4.0.json"):
    schema = load_schema(schema_path)
    rules = schema["element_selection_rules"]
    min_sev_rank = severity_rank(rules["min_severity"])
    score_ratio = rules["score_ratio_threshold"]
    target = rules["target_count"][difficulty]

    chart_defining_enabled = rules["chart_defining_overrides_enabled"]
    chart_defining = set(rules["chart_defining_elements"])

    if elements_skeleton:
        max_score = max(el.get("score",0) for el in elements_skeleton)
    else:
        max_score = 0

    def passes(el):
        if severity_rank(el.get("severity","slight")) < min_sev_rank: return False
        if max_score>0 and el.get("score",0) < max_score*score_ratio: return False
        return True

    filtered = [el for el in elements_skeleton if passes(el)]

    if chart_defining_enabled:
        for el in elements_skeleton:
            if el.get("element_name") in chart_defining and el not in filtered:
                filtered.append(el)

    def key(el):
        return (el.get("score",0), severity_rank(el.get("severity","slight")), el.get("section_coverage",0), rank_score = score * (0.65 + 0.70 * section_coverage))

    filtered.sort(key=key, reverse=True)
    return filtered[:target]
