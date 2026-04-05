from __future__ import annotations

"""
severity_engine.py
Phase 3 wiring layer for Stage 5.1 (Track A): Severity + score + coverage.

Responsibilities (per Phase 1/2 definitions):
- Consume SectionMetrics ("sections") produced upstream (Stage 2–4.1).
- Run Track A calibrated inference to produce elements_skeleton:
    element_id, element_name (JP), category, severity, score, section_coverage
  as described in the Phase 1 guide. 
- Optionally enrich elements_skeleton with:
    matched_tags, training_items  (from Stage 4.2/4.3 element candidates)
  without changing the set of detected elements (non-breaking behavior).
- Add dominant_score = score * section_coverage (Stage 7 convention). [2](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!saa6eb18249c5477d8dcfcbe9f3a8e933)

This module MUST NOT modify completed Phase 1/2 code. It only calls their
public wrappers and adds metadata fields in an additive way.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


DEFAULT_CALIBRATION_CONFIG_PATH = "score_calibration_config_v0.2.1.json"


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _compute_dominant_score(el: Dict[str, Any]) -> float:
    """
    Dominant score definition:
        dominant_score = score * section_coverage
    (Phase 1/2 Stage 7 convention). [2](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!saa6eb18249c5477d8dcfcbe9f3a8e933)
    """
    score = _safe_float(el.get("score"), 0.0)
    cov = _safe_float(el.get("section_coverage"), 0.0)
    return score * cov


def _index_candidates_by_name(
    element_candidates: Sequence[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    Build a map: element_name -> candidate dict.

    Candidates are expected to use "element_name" (JP) because
    tips_training_mapping.json keys are JP names. 
    """
    out: Dict[str, Dict[str, Any]] = {}
    for c in element_candidates or []:
        nm = c.get("element_name")
        if isinstance(nm, str) and nm:
            out[nm] = c
    return out


def merge_candidate_metadata(
    elements_skeleton: List[Dict[str, Any]],
    element_candidates: Sequence[Dict[str, Any]],
    *,
    overwrite: bool = False,
) -> List[Dict[str, Any]]:
    """
    Enrich elements_skeleton with Stage 4.2/4.3 metadata:
        matched_tags, training_items, tag_hit_count

    This is additive and non-breaking:
    - We do NOT add/remove elements
    - We do NOT alter severity/score/coverage
    - We only attach metadata keys if present in candidates

    Parameters
    ----------
    overwrite:
        If False (default), only fill missing keys on skeleton elements.
        If True, overwrite existing keys.
    """
    cand_by_name = _index_candidates_by_name(element_candidates)
    out: List[Dict[str, Any]] = []

    for el in elements_skeleton or []:
        el2 = dict(el)
        nm = el2.get("element_name") or el2.get("name")
        if isinstance(nm, str) and nm and nm in cand_by_name:
            c = cand_by_name[nm]
            for k in ("matched_tags", "training_items", "tag_hit_count"):
                if overwrite or k not in el2:
                    if k in c:
                        el2[k] = c[k]
        out.append(el2)

    return out


def run_track_a_proseka(
    sections: Sequence[Any],
    *,
    calibration_config_path: str = DEFAULT_CALIBRATION_CONFIG_PATH,
    preserve_severity: bool = True,
    coverage_threshold: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Track A (Phase 2) wrapper call.

    Uses proseka_score_calibration.infer_severities_for_chart_calibrated() which:
    - runs base inference
    - calibrates element scores (and optionally severity)
    - returns dict containing elements_skeleton
    without changing schemas (non-breaking). [1](https://onedrive.live.com/?id=71da77e2-df0e-49ca-9768-be8dcfb83419&cid=d5d62a1ef303ba22&web=1)
    """
    from . import proseka_score_calibration  # type: ignore

    return proseka_score_calibration.infer_severities_for_chart_calibrated(
        sections=list(sections) if sections is not None else [],
        calibration_config_path=calibration_config_path,
        preserve_severity=preserve_severity,
        coverage_threshold=coverage_threshold,
    )


def build_elements_skeleton(
    game_id: str,
    canonical_payload: Dict[str, Any],
    *,
    element_candidates: Optional[Sequence[Dict[str, Any]]] = None,
    detected_tags: Optional[Sequence[str]] = None,
    calibration_config_path: str = DEFAULT_CALIBRATION_CONFIG_PATH,
    preserve_severity: bool = True,
    coverage_threshold: Optional[str] = None,
    attach_to_payload: bool = True,
    add_dominant_score: bool = True,
) -> Dict[str, Any]:
    """
    Unified entry point for Stage 5.1 wiring.

    Parameters
    ----------
    game_id:
        Only "proseka" is supported in this module currently.

    canonical_payload:
        Must contain "sections" for Track A (SectionMetrics list).

    element_candidates:
        Optional list of candidates from element_inference.infer_element_candidates()
        to merge matched_tags/training_items onto elements_skeleton.

    detected_tags:
        Optional detected tag list. If provided and element_candidates is None,
        this function may infer candidates using element_inference.

    attach_to_payload:
        If True, stores canonical_payload["elements_skeleton"] = list[dict].

    add_dominant_score:
        If True, adds "dominant_score" to each element dict as score*coverage.
        This is additive and used by Stage 7 summaries. [2](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!saa6eb18249c5477d8dcfcbe9f3a8e933)

    Returns
    -------
    dict:
        {
          "elements_skeleton": List[dict],
          "debug": Optional[dict],
        }
    """
    gid = (game_id or "").lower().strip()
    sections = canonical_payload.get("sections") or []

    if gid != "proseka":
        res = {"elements_skeleton": [], "debug": {"warning": f"unsupported game_id={game_id!r}"}}
        if attach_to_payload:
            canonical_payload["elements_skeleton"] = res["elements_skeleton"]
        return res

    # Track A inference
    track_a_result = run_track_a_proseka(
        sections=sections,
        calibration_config_path=calibration_config_path,
        preserve_severity=preserve_severity,
        coverage_threshold=coverage_threshold,
    )

    elements: List[Dict[str, Any]] = list(track_a_result.get("elements_skeleton") or [])

    # Optional: infer candidates from detected_tags if candidates not supplied
    if element_candidates is None and detected_tags is not None:
        try:
            from .element_inference import infer_element_candidates  # type: ignore
            element_candidates = infer_element_candidates(list(detected_tags))
        except Exception:
            element_candidates = None

    # Optional: merge candidate metadata
    if element_candidates is not None:
        elements = merge_candidate_metadata(elements, element_candidates, overwrite=False)

    # Optional: add dominant_score
    if add_dominant_score:
        elements2: List[Dict[str, Any]] = []
        for el in elements:
            el2 = dict(el)
            if "dominant_score" not in el2:
                el2["dominant_score"] = _compute_dominant_score(el2)
            elements2.append(el2)
        elements = elements2

    if attach_to_payload:
        canonical_payload["elements_skeleton"] = elements

    return {
        "elements_skeleton": elements,
        "debug": {
            "track_a_keys": list(track_a_result.keys()),
            "sections_present": bool(sections),
            "merged_candidates": bool(element_candidates),
            "dominant_score_added": add_dominant_score,
        },
    }


__all__ = [
    "run_track_a_proseka",
    "merge_candidate_metadata",
    "build_elements_skeleton",
]

