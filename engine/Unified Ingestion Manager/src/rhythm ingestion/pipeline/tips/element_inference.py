from __future__ import annotations

"""
element_inference.py
Phase 1/2 Stage 4.2–4.3: Tag → element candidates (Project SEKAI / Proseka)

Grounded in the Phase 1/2 pipeline definitions:

- Stage 4.2: Tag -> element candidates
  - Use tips_training_mapping.json
  - For each element:
      matched_tags = detected_tags ∩ element.tags
  - If matched_tags >= min_tag_hits => element present

- Stage 4.3:
  - Produce a list of inferred element candidates
    (with matched_tags + training_items)

This module is a *wiring utility* for Phase 3 and does NOT change any
completed Phase 1/2 behavior. It simply provides a standard, testable
function to build element candidates.

References:
- tips_training_mapping.json: element(JP) -> tags -> training_items [1](https://onedrive.live.com/?id=0d6babc4-4a7a-4ed6-98aa-d027e9f6d0f6&cid=d5d62a1ef303ba22&web=1)
- Phase 1 guide: Stage 4.2 / 4.3 semantics [2](https://onedrive.live.com/?id=d44c7174-a178-4217-8cdb-5d394357b719&cid=d5d62a1ef303ba22&web=1)
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union
from rhythm_ingestion.pipeline.pattern_tags.pattern_tags_taxonomy import PatternTagsTaxonomy
import json


DEFAULT_TRAINING_MAPPING_PATH = "tips_training_mapping.json"


@dataclass(frozen=True)
class ElementCandidate:
    """
    Lightweight element candidate container.

    This is intentionally schema-minimal so we do not impose a new contract
    on completed phases. Callers can convert to dict via to_dict().
    """
    element_name: str
    matched_tags: Tuple[str, ...]
    training_items: Tuple[str, ...]
    tag_hit_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "element_name": self.element_name,
            "matched_tags": list(self.matched_tags),
            "training_items": list(self.training_items),
            "tag_hit_count": self.tag_hit_count,
        }


@lru_cache(maxsize=8)
def load_tips_training_mapping(path: str = DEFAULT_TRAINING_MAPPING_PATH) -> Dict[str, Dict[str, Any]]:
    """
    Load tips_training_mapping.json.

    Expected structure:
        {
          "<JP element name>": {
              "tags": [ ... ],
              "training_items": [ ... ]
          },
          ...
        }

    This mapping is authoritative for Stage 4.2–4.3 inference. [1](https://onedrive.live.com/?id=0d6babc4-4a7a-4ed6-98aa-d027e9f6d0f6&cid=d5d62a1ef303ba22&web=1)[2](https://onedrive.live.com/?id=d44c7174-a178-4217-8cdb-5d394357b719&cid=d5d62a1ef303ba22&web=1)
    """
    p = Path(path)
    if not p.exists():
        return {}

    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return data if isinstance(data, dict) else {}


def infer_element_candidates(
    detected_tags: Sequence[str],
    *,
    mapping: Optional[Dict[str, Dict[str, Any]]] = None,
    min_tag_hits: int = 1,
    include_zero_hit: bool = False,
) -> List[Dict[str, Any]]:
    """
    Infer element candidates from detected tags (Stage 4.2–4.3).

    Parameters
    ----------
    detected_tags:
        Tags detected by earlier pipeline stages (e.g. ["stream","burst.start",...]).
        These must align to your tag taxonomy and mapping file. [2](https://onedrive.live.com/?id=d44c7174-a178-4217-8cdb-5d394357b719&cid=d5d62a1ef303ba22&web=1)

    mapping:
        Optional pre-loaded tips_training_mapping.json dictionary.
        If None, we load DEFAULT_TRAINING_MAPPING_PATH.

    min_tag_hits:
        Minimum number of matched tags required to treat an element as present.
        Phase 1 guide states: if matched_tags >= min_tag_hits => element present. [2](https://onedrive.live.com/?id=d44c7174-a178-4217-8cdb-5d394357b719&cid=d5d62a1ef303ba22&web=1)

    include_zero_hit:
        If True, include elements even if tag_hit_count < min_tag_hits.
        Default False to stay aligned with Stage 4.2 presence semantics. [2](https://onedrive.live.com/?id=d44c7174-a178-4217-8cdb-5d394357b719&cid=d5d62a1ef303ba22&web=1)

    Returns
    -------
    List[dict]
        A list of element candidate dicts, each containing:
            - element_name: str (JP element key)
            - matched_tags: List[str]
            - training_items: List[str]
            - tag_hit_count: int

    Notes
    -----
    - This function does NOT assign severity/score/coverage; that is Stage 5.1+.
    - This function does NOT modify detected_tags; it only intersects with mapping tags.
    """
    if mapping is None:
        mapping = load_tips_training_mapping(DEFAULT_TRAINING_MAPPING_PATH)

    tag_set: Set[str] = set(detected_tags or [])
    out: List[Dict[str, Any]] = []

    # Iterate deterministically (stable ordering) by JP element key
    for element_name in sorted(mapping.keys()):
        entry = mapping.get(element_name) or {}
        element_tags = entry.get("tags", []) or []
        training_items = entry.get("training_items", []) or []

        matched = sorted(t for t in element_tags if t in tag_set)
        hit_count = len(matched)

        if include_zero_hit or hit_count >= int(min_tag_hits):
            out.append(
                ElementCandidate(
                    element_name=str(element_name),
                    matched_tags=tuple(matched),
                    training_items=tuple(str(x) for x in training_items),
                    tag_hit_count=hit_count,
                ).to_dict()
            )

    return out

def _normalize_and_report_tags(
    canonical_payload: Dict[str, Any],
    detected_tags: Sequence[str],
    *,
    diagnostics_key: str = "diagnostics",
    tag_parity_key: str = "tag_parity",
) -> List[str]:
    """
    Phase-3 additive helper:
    - normalize detected tags using PatternTagsTaxonomy
    - record unknown tags into canonical_payload diagnostics (non-blocking)
    - return normalized tag list
    """
    normalized: List[str] = []
    for t in detected_tags or []:
        if isinstance(t, str):
            normalized.append(PatternTagsTaxonomy.normalize_tag(t))

    unknown = PatternTagsTaxonomy.validate_tags(normalized)
    if unknown:
        diag = canonical_payload.get(diagnostics_key)
        if not isinstance(diag, dict):
            diag = {}
            canonical_payload[diagnostics_key] = diag
        tp = diag.setdefault(tag_parity_key, {})
        tp["unknown_tags"] = unknown

    return normalized


def attach_candidates_to_payload(
    canonical_payload: Dict[str, Any],
    *,
    detected_tags_key: str = "detected_tags",
    output_key: str = "element_candidates",
    mapping_path: str = DEFAULT_TRAINING_MAPPING_PATH,
    min_tag_hits: int = 1,
) -> Dict[str, Any]:
    """
    Convenience helper: infer candidates and attach them into canonical_payload.

    This is purely additive and does not break schema contracts:
    it adds canonical_payload[output_key] = [ ...candidate dicts... ].

    Parameters
    ----------
    canonical_payload:
        Chart payload containing detected tags (and possibly sections/diagnostics).
        The phase guides recommend payload shapes that include detected_tags. [2](https://onedrive.live.com/?id=d44c7174-a178-4217-8cdb-5d394357b719&cid=d5d62a1ef303ba22&web=1)

    detected_tags_key:
        Key where detected tags live (default: "detected_tags").

    output_key:
        Key to store candidates (default: "element_candidates").

    mapping_path:
        Path to tips_training_mapping.json.

    min_tag_hits:
        Stage 4.2 presence threshold. [2](https://onedrive.live.com/?id=d44c7174-a178-4217-8cdb-5d394357b719&cid=d5d62a1ef303ba22&web=1)

    Returns
    -------
    canonical_payload (mutated, but returned for convenience)
    """
    tags = canonical_payload.get(detected_tags_key, []) or []
    normalized = _normalize_and_report_tags(canonical_payload, tags)
    canonical_payload[detected_tags_key] = normalized  # safe canonicalization

    mapping = load_tips_training_mapping(mapping_path)
    candidates = infer_element_candidates(normalized, mapping=mapping, min_tag_hits=min_tag_hits)
    canonical_payload[output_key] = candidates
    return canonical_payload


__all__ = [
    "ElementCandidate",
    "load_tips_training_mapping",
    "infer_element_candidates",
    "attach_candidates_to_payload",
]

