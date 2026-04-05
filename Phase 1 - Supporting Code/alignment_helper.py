# -*- coding: utf-8 -*-
"""
alignment_helper.py

Helper utilities for working with canonical <-> Japanese element names
for the Project Sekai tips pipeline.

This module wraps the data defined in proseka_element_alignment.py and
makes it easier to:
  - map JP element names to canonical IDs
  - get JP labels for a canonical family
  - attach canonical IDs to elements_skeleton entries (Step 5.3/7)
"""

from __future__ import annotations
from typing import Dict, List, Any

from proseka_element_alignment import (
    CANONICAL_ELEMENTS,
    ELEMENT_ALIGNMENT,
    JP_TO_CANONICAL,
)


def jp_to_canonical(jp_name: str) -> str | None:
    """Return the canonical element ID for a given JP element name.

    Parameters
    ----------
    jp_name : str
        Official Japanese element label, e.g. "物量", "トリル".

    Returns
    -------
    str | None
        Canonical ID (e.g. "stream", "trill"), or None if not found.
    """
    return JP_TO_CANONICAL.get(jp_name)


def canonical_to_jp_list(canonical_id: str) -> List[str]:
    """Return the list of JP labels aligned to a canonical element ID.

    Parameters
    ----------
    canonical_id : str
        Internal canonical identifier, e.g. "stream".

    Returns
    -------
    list[str]
        List of JP labels, or empty list if canonical_id is unknown.
    """
    return ELEMENT_ALIGNMENT.get(canonical_id, [])


def attach_canonical_ids_to_elements(
    elements_skeleton: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Attach canonical IDs to each element_skeleton entry based on its JP name.

    This function assumes that each element dict has at least:
      - "name": JP element label

    It adds:
      - "canonical_id": canonical ID from JP_TO_CANONICAL (or None if not mapped)

    Parameters
    ----------
    elements_skeleton : list[dict]
        List of element dicts as produced by severity_detector_stub.

    Returns
    -------
    list[dict]
        Same list (modified in-place) with "canonical_id" added per element.
    """
    for el in elements_skeleton:
        jp_name = el.get("name")
        if isinstance(jp_name, str):
            el["canonical_id"] = JP_TO_CANONICAL.get(jp_name)
        else:
            el["canonical_id"] = None
    return elements_skeleton


def group_elements_by_canonical(
    elements_skeleton: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """Group elements_skeleton entries by canonical_id.

    If canonical_id is None, they are grouped under the key "__unmapped__".

    This is useful in Step 5.3 and Step 7 when summarizing difficulty by
    canonical family rather than individual JP elements.
    """
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for el in elements_skeleton:
        cid = el.get("canonical_id") or "__unmapped__"
        grouped.setdefault(cid, []).append(el)

    return grouped


def get_all_canonical_elements() -> List[str]:
    """Return the list of canonical element IDs.

    This simply exposes CANONICAL_ELEMENTS from proseka_element_alignment.
    """
    return list(CANONICAL_ELEMENTS)
