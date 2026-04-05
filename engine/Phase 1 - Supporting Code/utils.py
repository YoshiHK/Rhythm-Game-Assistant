# -*- coding: utf-8 -*-
"""
Utility helpers for the Project Sekai element rule registry.

These functions operate purely on the RULES dict defined in element_rules.py,
and are meant to simplify wiring the detector and tips pipeline.

Typical usage:

    from rules import RULES
    from rules.utils import get_rules_by_category, get_metric_keys_for_all_rules

    metrics_needed = get_metric_keys_for_all_rules()
    rhythm_rules = get_rules_by_category("rhythm")

"""

from __future__ import annotations
from typing import Dict, Any, Iterable, Set

from .element_rules import RULES


def get_rule(element_id: str) -> Dict[str, Any]:
    """Return the rule dict for a given internal element_id.

    Parameters
    ----------
    element_id : str
        Internal identifier key, e.g. "trill", "high_density", "swing_rhythm".

    Returns
    -------
    dict
        Rule entry from RULES. Raises KeyError if not found.
    """
    return RULES[element_id]


def get_all_element_ids() -> Iterable[str]:
    """Return an iterable of all element ids defined in RULES.

    Useful for iterating detection over all supported elements.
    """
    return RULES.keys()


def get_rules_by_category(category: str) -> Dict[str, Dict[str, Any]]:
    """Filter RULES by 'category'.

    Categories are free-form strings defined in element_rules.py, e.g.:
        "rhythm", "density", "visual", "long_note", "flick",
        "trace", "pattern", "layout", "chart_meta", "meta", ...

    Parameters
    ----------
    category : str
        Category name to filter by.

    Returns
    -------
    dict
        {element_id: rule_dict, ...} for rules whose "category" matches.
    """
    return {
        element_id: rule
        for element_id, rule in RULES.items()
        if rule.get("category") == category
    }


def get_all_categories() -> Set[str]:
    """Return the set of categories used across all rules.

    This is handy to inspect current taxonomy and to drive grouped detection
    (e.g., run all "rhythm" rules on rhythm-related features).
    """
    return {rule.get("category", "") for rule in RULES.values() if "category" in rule}


def get_metric_keys_for_all_rules() -> Set[str]:
    """Collect the union of all metric_keys required by all rules.

    This is especially useful for:
      - designing SectionMetrics (Step 5.1),
      - precomputing exactly the features the detector must expose.

    Returns
    -------
    set[str]
        All metric_keys referenced by any rule.
    """
    keys: Set[str] = set()
    for rule in RULES.values():
        for k in rule.get("metric_keys", []):
            keys.add(k)
    return keys


def get_tag_candidates_for_all_rules() -> Set[str]:
    """Collect the union of all tag_candidates from all rules.

    These tags should correspond to the pattern-signal vocabulary used in:
      - pattern_signals_export.json,
      - tips_training_mapping.json.

    Returns
    -------
    set[str]
        All tag candidate strings mentioned in any rule.
    """
    tags: Set[str] = set()
    for rule in RULES.values():
        for t in rule.get("tag_candidates", []):
            tags.add(t)
    return tags


def get_jp_name_map() -> Dict[str, str]:
    """Build a mapping from element_id -> jp_name.

    Useful when:
      - constructing elements[] for the tips pipeline,
      - aligning canonical IDs with official JP names defined in 要素名.docx.

    Returns
    -------
    dict
        {element_id: jp_name}
    """
    return {
        element_id: rule.get("jp_name", element_id)
        for element_id, rule in RULES.items()
    }
