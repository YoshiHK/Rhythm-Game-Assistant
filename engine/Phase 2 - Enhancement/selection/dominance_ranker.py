from __future__ import annotations
from typing import Any, Dict, List, Tuple

SEVERITY_ORDER = ["slight", "light", "mild", "moderate", "dense", "complex", "demanding"]
SEV_INDEX = {s: i for i, s in enumerate(SEVERITY_ORDER)}


def _f(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _sev_idx(sev: Any) -> int:
    if isinstance(sev, str):
        return SEV_INDEX.get(sev, SEV_INDEX["moderate"])
    return SEV_INDEX["moderate"]


def dominance_score(e: Dict[str, Any]) -> float:
    """Default dominance score = score * section_coverage (bounded)."""
    s = _f(e.get("score"), 0.0)
    c = _f(e.get("section_coverage"), 0.0)
    s = max(0.0, min(1.0, s))
    c = max(0.0, min(1.0, c))
    return s * c


def rank_by_dominance(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deterministic ranking:
    1) dominance_score desc
    2) score desc
    3) severity desc
    4) coverage desc
    5) name asc (stable tie-break)
    """
    def key(e: Dict[str, Any]) -> Tuple[float, float, int, float, str]:
        dom = dominance_score(e)
        score = _f(e.get("score"), 0.0)
        sev = _sev_idx(e.get("severity"))
        cov = _f(e.get("section_coverage"), 0.0)
        name = str(e.get("name") or e.get("element_name") or "")
        return (-dom, -score, -sev, -cov, name)

    return sorted([e for e in elements if isinstance(e, dict)], key=key)


__all__ = ["rank_by_dominance", "dominance_score"]