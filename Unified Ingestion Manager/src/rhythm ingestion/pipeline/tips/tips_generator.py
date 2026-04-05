from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

# Phase-3 wiring: reuse Stage 4.2 utility instead of duplicating mapping logic.
from .element_inference import (
    load_tips_training_mapping as _ei_load_tips_training_mapping,
    infer_element_candidates as _ei_infer_element_candidates,
    attach_candidates_to_payload as _ei_attach_candidates_to_payload,  # <-- NEW
)


DEFAULT_CALIBRATION_CONFIG_PATH = "score_calibration_config_v0.2.1.json"
DEFAULT_TRAINING_MAPPING_PATH = "tips_training_mapping.json"


@lru_cache(maxsize=4)
def _load_tips_training_mapping(path: str = DEFAULT_TRAINING_MAPPING_PATH) -> Dict[str, Dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r", encoding="utf-8") as f:
        data = __import__("json").load(f)
    return data if isinstance(data, dict) else {}


def _enrich_elements_with_training_mapping(
    elements: List[Dict[str, Any]],
    detected_tags: List[str],
    mapping: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Phase-3 wiring:
    Enrich Track-A elements_skeleton with matched_tags + training_items using
    the shared Stage 4.2 utility (element_inference.py) to avoid duplicated logic.

    This does NOT change Phase 1/2 behavior:
    - matched_tags are still computed as intersection(detected_tags, mapping[element].tags)
    - training_items still come from tips_training_mapping.json
    """
    # Build candidates for *all* mapping entries, including zero-hit, so we can
    # attach training_items consistently even when matched_tags is empty.
    candidates = _ei_infer_element_candidates(
        detected_tags or [],
        mapping=mapping,
        min_tag_hits=1,
        include_zero_hit=True,
    )

    # Index by element_name for quick attach
    cand_by_name: Dict[str, Dict[str, Any]] = {
        str(c.get("element_name")): c for c in candidates if isinstance(c, dict) and c.get("element_name")
    }

    enriched: List[Dict[str, Any]] = []
    for el in elements:
        el2 = dict(el)
        name = el2.get("element_name") or el2.get("name")
        if isinstance(name, str) and name in cand_by_name:
            c = cand_by_name[name]
            el2["matched_tags"] = c.get("matched_tags", []) or []
            el2["training_items"] = c.get("training_items", []) or []
        enriched.append(el2)
    return enriched


def build_chart_summary(
    game_id: str,
    canonical_row: Dict[str, Any],
    all_elements: List[Dict[str, Any]],
    *,
    selected_element_names: Optional[List[str]] = None,
    chart_id: Optional[Union[str, int]] = None,
) -> Dict[str, Any]:
    """
    Per-chart summary block compliant with proseka_summary_blocks_canonical.json. [2](https://onedrive.live.com/?id=0d6babc4-4a7a-4ed6-98aa-d027e9f6d0f6&cid=d5d62a1ef303ba22&web=1)
    Dominant score convention: score * section_coverage. 
    """
    selected_element_names = selected_element_names or []
    song_id = canonical_row.get("song_id")

    element_frequency: Dict[str, int] = {}
    severity_distribution: Dict[str, int] = {}

    dom_scores: List[float] = []
    coverages: List[float] = []

    for elem in all_elements:
        name = elem.get("element_name") or elem.get("name") or "UNKNOWN"
        sev = elem.get("severity", "UNKNOWN")
        score = float(elem.get("score", 0.0) or 0.0)
        cov = float(elem.get("section_coverage", 0.0) or 0.0)
        dom = float(elem.get("dominant_score", score * cov))

        element_frequency[name] = element_frequency.get(name, 0) + 1
        severity_distribution[sev] = severity_distribution.get(sev, 0) + 1
        dom_scores.append(dom)
        coverages.append(cov)

    avg_score = (sum(dom_scores) / len(dom_scores)) if dom_scores else 0.0
    avg_cov = (sum(coverages) / len(coverages)) if coverages else 0.0
    max_score = max(dom_scores) if dom_scores else 0.0

    eps = 1e-6
    dominant_elements: List[str] = []
    for elem in all_elements:
        name = elem.get("element_name") or elem.get("name") or "UNKNOWN"
        score = float(elem.get("score", 0.0) or 0.0)
        cov = float(elem.get("section_coverage", 0.0) or 0.0)
        dom = float(elem.get("dominant_score", score * cov))
        if abs(dom - max_score) <= eps and name not in dominant_elements:
            dominant_elements.append(name)

    sel = set(selected_element_names)
    dominant_selected_flags = {n: (n in sel) for n in dominant_elements}

    return {
        "chart_id": chart_id,
        "song_id": song_id,
        "element_count": len(all_elements),
        "element_frequency": element_frequency,
        "severity_distribution": severity_distribution,
        "avg_score": avg_score,
        "avg_section_coverage": avg_cov,
        "max_score": max_score,
        "dominant_elements": dominant_elements,
        "dominant_selected_flags": dominant_selected_flags,
    }


def _percentile(sorted_vals: List[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if p <= 0:
        return float(sorted_vals[0])
    if p >= 1:
        return float(sorted_vals[-1])
    i = int(round(p * (len(sorted_vals) - 1)))
    i = max(0, min(i, len(sorted_vals) - 1))
    return float(sorted_vals[i])


def _word_count(text: str) -> int:
    t = (text or "").strip()
    return len([w for w in t.split() if w]) if t else 0


def _two_paragraphs(text: str) -> bool:
    t = (text or "").strip()
    return bool(t) and ("\n\n" in t)


def build_batch_summary(
    difficulty: str,
    per_chart_summaries: List[Dict[str, Any]],
    *,
    batch_id: Optional[str] = None,
    tips_texts: Optional[List[str]] = None,
    top_k: int = 5,
    include_presenter_text: bool = False,
) -> Dict[str, Any]:
    """
    Batch summary aggregates per-chart blocks (Stage 7). 
    Uses BatchLevelSummary dataclasses mirror + validate_basic(). [3](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!s5a8069e528b04db59d07bc92cf415c7a)
    Presenter is formatting-only. [2](https://onedrive.live.com/?id=0d6babc4-4a7a-4ed6-98aa-d027e9f6d0f6&cid=d5d62a1ef303ba22&web=1)
    """
    from .proseka_batch_summary_dataclasses import (  # type: ignore
        BatchLevelSummary, ScoreDistribution, TopElement, TipsCompliance
    )

    diff = (difficulty or "expert").lower()
    chart_count = len(per_chart_summaries)

    element_frequency: Dict[str, int] = {}
    severity_distribution: Dict[str, int] = {}

    total_elements = 0
    sum_avg_score_w = 0.0
    sum_avg_cov_w = 0.0

    dom_total = 0
    dom_sel = 0
    full_dom = 0
    zero_dom = 0

    per_chart_avg_scores: List[float] = []

    for s in per_chart_summaries:
        ec = int(s.get("element_count", 0) or 0)
        total_elements += ec

        ef = s.get("element_frequency", {}) or {}
        for k, v in ef.items():
            kk = str(k)
            element_frequency[kk] = element_frequency.get(kk, 0) + int(v or 0)

        sd = s.get("severity_distribution", {}) or {}
        for k, v in sd.items():
            kk = str(k)
            severity_distribution[kk] = severity_distribution.get(kk, 0) + int(v or 0)

        avg_sc = float(s.get("avg_score", 0.0) or 0.0)
        avg_cov = float(s.get("avg_section_coverage", 0.0) or 0.0)
        per_chart_avg_scores.append(avg_sc)

        if ec > 0:
            sum_avg_score_w += avg_sc * ec
            sum_avg_cov_w += avg_cov * ec

        dom_elems = s.get("dominant_elements", []) or []
        flags = s.get("dominant_selected_flags", {}) or {}
        d_total = len(dom_elems)
        d_sel = sum(1 for n in dom_elems if bool(flags.get(n, False)))

        dom_total += d_total
        dom_sel += d_sel

        if d_total > 0:
            if d_sel == d_total:
                full_dom += 1
            if d_sel == 0:
                zero_dom += 1

    avg_score = (sum_avg_score_w / total_elements) if total_elements > 0 else 0.0
    avg_cov = (sum_avg_cov_w / total_elements) if total_elements > 0 else 0.0
    dom_ratio = (dom_sel / dom_total) if dom_total > 0 else 0.0

    score_distribution: Optional[ScoreDistribution] = None
    ss = sorted(per_chart_avg_scores)
    if ss:
        score_distribution = ScoreDistribution(
            min=float(ss[0]),
            p25=_percentile(ss, 0.25),
            p50=_percentile(ss, 0.50),
            p75=_percentile(ss, 0.75),
            p90=_percentile(ss, 0.90),
            max=float(ss[-1]),
        )

    top_elements: Optional[List[TopElement]] = None
    if element_frequency:
        tot = sum(element_frequency.values()) or 0
        top = sorted(element_frequency.items(), key=lambda kv: (-kv[1], kv[0]))[: max(1, int(top_k))]
        top_elements = [
            TopElement(element=name, count=count, share=(count / tot if tot > 0 else 0.0))
            for name, count in top
        ]

    tips_compliance: Optional[TipsCompliance] = None
    if tips_texts is not None:
        texts = [t for t in tips_texts if isinstance(t, str)]
        generated = sum(1 for t in texts if t.strip())
        valid = sum(1 for t in texts if _two_paragraphs(t))
        wc = [_word_count(t) for t in texts if t.strip()]
        tips_compliance = TipsCompliance(
            tips_generated_count=generated,
            tips_valid_count=valid,
            tips_valid_ratio=(valid / generated if generated > 0 else 0.0),
            avg_word_count=(sum(wc) / len(wc) if wc else None),
            max_word_count=(max(wc) if wc else None),
            over_limit_count=None,
        )

    batch = BatchLevelSummary(
        batch_id=batch_id,
        difficulty=diff,
        chart_count=chart_count,
        element_frequency=element_frequency,
        severity_distribution=severity_distribution,
        avg_score=float(avg_score),
        avg_section_coverage=float(avg_cov),
        dominant_total=int(dom_total),
        dominant_selected_count=int(dom_sel),
        dominant_selection_ratio=float(dom_ratio),
        charts_with_full_dominant_coverage=int(full_dom),
        charts_with_zero_dominant_coverage=int(zero_dom),
        score_distribution=score_distribution,
        top_elements=top_elements,
        tips_compliance=tips_compliance,
        notes=None,
    )
    batch.validate_basic()
    out = batch.to_dict()

    if include_presenter_text:
        try:
            from .proseka_batch_summary_presenter import present_batch_summary  # type: ignore
            out["presented"] = present_batch_summary(out, style="markdown")
        except Exception:
            pass

    return out


def run_for_batch(
    game_id: str,
    chart_inputs: List[Dict[str, Any]],
    *,
    mode: str = "production",
    attach_to_payload: bool = True,
    batch_id: Optional[str] = None,
    include_presenter_text: bool = False,
) -> Dict[str, Any]:
    gid = (game_id or "").lower().strip()

    per_chart_results: List[Dict[str, Any]] = []
    per_chart_summaries: List[Dict[str, Any]] = []
    tips_texts: List[str] = []

    difficulty = "expert"
    if chart_inputs:
        row0 = chart_inputs[0].get("canonical_row") or {}
        difficulty = str(row0.get("difficulty_label") or row0.get("difficulty") or "expert").lower()

    if gid != "proseka":
        return {
            "per_chart": [],
            "per_chart_summaries": [],
            "batch_summary": build_batch_summary(
                difficulty=difficulty,
                per_chart_summaries=[],
                batch_id=batch_id,
                tips_texts=[],
                include_presenter_text=include_presenter_text,
            ),
        }

    for item in chart_inputs:
        payload = item.get("canonical_payload") or {}
        row = item.get("canonical_row") or {}
        res = run_for_chart(gid, payload, row, mode=mode, attach_to_payload=attach_to_payload)
        per_chart_results.append(res)
        per_chart_summaries.append(res.get("chart_summary") or {})
        tips_texts.append(res.get("tips_text") or "")

    batch_summary = build_batch_summary(
        difficulty=difficulty,
        per_chart_summaries=per_chart_summaries,
        batch_id=batch_id,
        tips_texts=tips_texts,
        include_presenter_text=include_presenter_text,
    )

    return {
        "per_chart": per_chart_results,
        "per_chart_summaries": per_chart_summaries,
        "batch_summary": batch_summary,
    }


def _run_proseka_pipeline(
    canonical_payload: Dict[str, Any],
    canonical_row: Dict[str, Any],
    mode: str,
) -> Dict[str, Any]:
    # Track modules (Phase 1/2 code; do not modify)
    from . import proseka_score_calibration  # type: ignore
    from . import selector_v2               # type: ignore
    from . import guidance_engine_v2        # type: ignore
    from . import narrative_module_v2       # type: ignore

    detected_tags: List[str] = canonical_payload.get("detected_tags", []) or []
    sections = canonical_payload.get("sections") or []
    canonical_payload.setdefault("diagnostics", {})

    # ------------------------------------------------------------
    # Phase-3 debug-only: attach Stage 4.2/4.3 element_candidates
    # ------------------------------------------------------------
    if mode == "debug":
      try:
          # This is additive-only: it attaches canonical_payload["element_candidates"]
          # and may normalize detected_tags + record diagnostics.tag_parity.unknown_tags.
          _ei_attach_candidates_to_payload(
              canonical_payload,
              detected_tags_key="detected_tags",
              output_key="element_candidates",
              mapping_path=DEFAULT_TRAINING_MAPPING_PATH,
              min_tag_hits=1,  # Stage 4.2 default presence threshold
          )
      except Exception as e:
          # Non-blocking: debug diagnostics only (do not change Phase 1/2 behavior)
          canonical_payload.setdefault("diagnostics", {}).setdefault("tips_debug", {})[
              "element_candidates_warning"
          ] = f"attach_candidates_to_payload failed: {type(e).__name__}: {e}"

    difficulty = str(
        canonical_row.get("difficulty_label")
        or canonical_row.get("difficulty")
        or "expert"
    ).lower()

    if sections:
        sev_result = proseka_score_calibration.infer_severities_for_chart_calibrated(
            sections=sections,
            calibration_config_path=DEFAULT_CALIBRATION_CONFIG_PATH,
            preserve_severity=True,
        )
        elements = sev_result.get("elements_skeleton") or []
    else:
        sev_result = {}
        elements = []

    canonical_payload["elements_skeleton"] = elements
    if not elements:
        
        return {
              "tips_text": tips_text,
              "chart_summary": chart_summary,
              "elements": guided,
              "debug": {
                  "severity_result_keys": list(sev_result.keys()),
                  "sections_present": bool(sections),
                  "detected_tag_count": len(detected_tags),

                  # NEW: element_candidates count (debug-only, additive)
                  "element_candidates_count": (
                      len(canonical_payload.get("element_candidates") or [])
                      if isinstance(canonical_payload.get("element_candidates"), list)
                      else 0
                  ),

                  # Optional: quick signal whether candidates were attached
                  "element_candidates_attached": isinstance(
                      canonical_payload.get("element_candidates"), list
                  ),
              } if mode == "debug" else None,
          }


    mapping = _ei_load_tips_training_mapping(DEFAULT_TRAINING_MAPPING_PATH)
    elements = _enrich_elements_with_training_mapping(elements, detected_tags, mapping)
    canonical_payload["elements_skeleton"] = elements

    selected = selector_v2.select_elements_v2(elements_skeleton=elements, difficulty=difficulty)
    guided = guidance_engine_v2.fill_guidance_for_elements_v2(selected_elements=selected, difficulty=difficulty)
    tips_text = narrative_module_v2.generate_tips_text_v2(difficulty=difficulty, selected_elements=guided)

    selected_names = [
        e.get("element_name")
        for e in guided
        if isinstance(e.get("element_name"), str) and e.get("element_name")
    ]

    chart_summary = build_chart_summary(
        game_id="proseka",
        canonical_row=canonical_row,
        all_elements=elements,
        selected_element_names=selected_names,
        chart_id=canonical_row.get("difficulty_code"),
    )

    return {
        "tips_text": tips_text,
        "chart_summary": chart_summary,
        "elements": guided,
        "debug": {
            "severity_result_keys": list(sev_result.keys()),
            "sections_present": bool(sections),
            "detected_tag_count": len(detected_tags),
        } if mode == "debug" else None,
    }


def run_for_chart(
    game_id: str,
    canonical_payload: Dict[str, Any],
    canonical_row: Dict[str, Any],
    *,
    mode: str = "production",
    attach_to_payload: bool = True,
) -> Dict[str, Any]:
    gid = (game_id or "").lower().strip()

    if gid == "proseka":
        result = _run_proseka_pipeline(canonical_payload, canonical_row, mode=mode)
        if attach_to_payload:
            canonical_payload["tips_text"] = result.get("tips_text", "")
            canonical_payload["chart_summary"] = result.get("chart_summary", {})
            canonical_payload["tips_elements"] = result.get("elements", [])
            if mode == "debug" and result.get("debug") is not None:
                canonical_payload.setdefault("diagnostics", {})["tips_debug"] = result["debug"]
        return result

    fallback = {
        "tips_text": "",
        "chart_summary": {},
        "elements": [],
        "debug": {"warning": f"No tips pipeline implemented for game_id={game_id!r}"} if mode == "debug" else None,
    }
    if attach_to_payload:
        canonical_payload["tips_text"] = ""
        canonical_payload["chart_summary"] = {}
        canonical_payload["tips_elements"] = []
        if mode == "debug":
            canonical_payload.setdefault("diagnostics", {})["tips_debug"] = fallback["debug"]
    return fallback


__all__ = [
    "run_for_chart",
    "run_for_batch",
    "build_chart_summary",
    "build_batch_summary",
]
