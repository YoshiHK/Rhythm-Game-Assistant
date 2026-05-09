# selector_v2.py
# Track B selection tweaks (B1, B2, B5)
# - B1: dominance-aware ranking score
# - B2: diversity constraint by canonical family (max 1 per family)
# - B5: tie-breaking: treat near-equal scores as ties and prefer coverage

from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple
import json
import math

SEVERITY_ORDER = ["slight","light","mild","moderate","dense","complex","demanding"]
SEV_INDEX = {s: i for i, s in enumerate(SEVERITY_ORDER)}


def severity_rank(s: str) -> int:
    return SEV_INDEX.get(s, 0)


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def load_schema(path: str = "proseka_internal_analysis_schema_v1.4.0.json") -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _jp_to_canonical(jp_name: Optional[str]) -> Optional[str]:
    if not jp_name or not isinstance(jp_name, str):
        return None
    # Prefer alignment_helper if present
    try:
        from alignment_helper import jp_to_canonical as _fn  # type: ignore
        return _fn(jp_name)
    except Exception:
        pass
    # Fallback to proseka_element_alignment
    try:
        from proseka_element_alignment import JP_TO_CANONICAL  # type: ignore
        return JP_TO_CANONICAL.get(jp_name)
    except Exception:
        return None


def _rank_score(score: float, section_coverage: float, base: float = 0.65, gain: float = 0.70) -> float:
    """B1: dominance-aware ranking score.

    rank_score = score * (base + gain * section_coverage)
    - keeps score primary
    - boosts chart-defining (high coverage) elements
    """
    return score * (base + gain * section_coverage)


def select_elements_v2(
    elements_skeleton: List[Dict[str, Any]],
    difficulty: str,
    *,
    schema_path: str = "proseka_internal_analysis_schema_v1.4.0.json",
    max_per_canonical_family: int = 1,
    epsilon: float = 0.03,
    rank_base: float = 0.65,
    rank_gain: float = 0.70,
    include_debug_rank_score: bool = False,
) -> List[Dict[str, Any]]:
    """Select tip elements with Track B tweaks B1, B2, B5.

    Inputs
    - elements_skeleton: output from (5.1) severity_detector (dicts)
    - difficulty: 'expert'|'master'|'append'

    Behavior
    - Applies schema-driven eligibility filters.
    - Chart-defining elements bypass filters.
    - Ranks using B1 dominance-aware rank_score.
    - Enforces B2 diversity: max 1 per canonical family, with relaxation if needed.
    - Applies B5 tie-break: treat near-equal rank_score as ties (bucketed by epsilon) and prefer coverage.

    Returns
    - List of selected element dicts (subset of input dicts).
    """

    schema = load_schema(schema_path)
    rules = schema.get("element_selection_rules") or schema.get("element_selection_logic") or {}

    min_sev = rules.get("min_severity", "moderate")
    min_sev_rank = severity_rank(min_sev)
    score_ratio = float(rules.get("score_ratio_threshold", 0.8))

    target_map = rules.get("target_count", {})
    target = int(target_map.get(difficulty, 3 if difficulty != "append" else 4))

    chart_defining_enabled = bool(rules.get("chart_defining_overrides_enabled", True))
    chart_defining = set(rules.get("chart_defining_elements", []))

    # Compute max score for ratio threshold
    max_score = max((_safe_float(el.get("score"), 0.0) for el in elements_skeleton), default=0.0)

    def is_chart_defining(el: Dict[str, Any]) -> bool:
        # Either explicit flag or schema-defined names
        if bool(el.get("is_chart_defining")):
            return True
        nm = el.get("element_name") or el.get("name")
        return chart_defining_enabled and isinstance(nm, str) and nm in chart_defining

    def passes(el: Dict[str, Any]) -> bool:
        sev = el.get("severity") or "slight"
        if severity_rank(str(sev)) < min_sev_rank:
            return False
        sc = _safe_float(el.get("score"), 0.0)
        if max_score > 0 and sc < max_score * score_ratio:
            return False
        return True

    # Build eligibility pool
    pool: List[Dict[str, Any]] = []
    for el in elements_skeleton:
        if is_chart_defining(el) or passes(el):
            pool.append(el)

    # If pool is still empty (edge case), fall back to top by score
    if not pool:
        pool = list(elements_skeleton)

    # Compute ranking fields
    ranked: List[Tuple[Tuple[int, float, int, float], Dict[str, Any]]] = []
    # B5: bucket by epsilon so near-equal rank_scores become ties
    eps = float(epsilon) if epsilon and epsilon > 0 else 0.0

    for el in pool:
        sc = _safe_float(el.get("score"), 0.0)
        cov = _safe_float(el.get("section_coverage"), 0.0)
        sev = str(el.get("severity") or "slight")
        rs = _rank_score(sc, cov, base=rank_base, gain=rank_gain)

        # bucket: higher is better
        bucket = int(math.floor(rs / eps)) if eps > 0 else int(rs * 1_000_000)

        # Sort key (descending via reverse=True):
        # 1) bucketed rank_score
        # 2) coverage (prefer higher within tie bucket)
        # 3) severity rank
        # 4) raw score
        key = (bucket, cov, severity_rank(sev), sc)

        if include_debug_rank_score:
            el = dict(el)
            el["_rank_score"] = rs
            el["_rank_bucket"] = bucket

        ranked.append((key, el))

    ranked.sort(key=lambda x: x[0], reverse=True)

    # B2: enforce family diversity
    selected: List[Dict[str, Any]] = []
    family_counts: Dict[str, int] = {}

    def family_id(el: Dict[str, Any]) -> str:
        nm = el.get("element_name") or el.get("name")
        cid = _jp_to_canonical(nm if isinstance(nm, str) else None)
        if cid:
            return f"canonical:{cid}"
        # fallback: group unmapped by their label to avoid accidental merging
        if isinstance(nm, str) and nm:
            return f"jp:{nm}"
        # final fallback to element_id
        eid = el.get("element_id")
        return f"id:{eid}"

    # First pass: strict diversity
    for _, el in ranked:
        if len(selected) >= target:
            break
        fid = family_id(el)
        if is_chart_defining(el):
            selected.append(el)
            family_counts[fid] = family_counts.get(fid, 0) + 1
            continue
        if family_counts.get(fid, 0) < max_per_canonical_family:
            selected.append(el)
            family_counts[fid] = family_counts.get(fid, 0) + 1

    # Relaxation pass: fill remaining slots ignoring diversity (but keep ordering)
    if len(selected) < target:
        seen_ids = set(id(x) for x in selected)
        for _, el in ranked:
            if len(selected) >= target:
                break
            if id(el) in seen_ids:
                continue
            selected.append(el)
            seen_ids.add(id(el))

    return selected[:target]


__all__ = [
    "select_elements_v2",
]
