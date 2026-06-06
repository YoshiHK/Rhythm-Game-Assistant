from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional


# -----------------------------------------------------------------------------
# Summary models
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class ReasonAlignmentSummary:
    total_items: int
    exact_match_count: int
    partial_match_count: int
    mismatch_count: int
    primary_reason_match_count: int
    primary_reason_match_rate: float
    exact_match_rate: float
    partial_match_rate: float
    mismatch_rate: float
    avg_reason_code_overlap: float
    high_confidence_mismatch_count: int
    low_confidence_exact_count: int
    by_category: Dict[str, int]
    by_layer: Dict[str, int]
    by_plane: Dict[str, int]
    by_decision_type: Dict[str, int]
    by_cause_type: Dict[str, int]
    by_signal_type: Dict[str, int]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _as_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _as_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def _norm_str(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()


def _norm_float(x: Any) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def _reason_codes(obj: Dict[str, Any]) -> List[str]:
    return [str(x).strip() for x in _as_list(obj.get("reason_codes")) if str(x).strip()]


def _primary_reason(obj: Dict[str, Any]) -> Optional[str]:
    val = _norm_str(obj.get("primary_reason"))
    if val:
        return val
    codes = _reason_codes(obj)
    return codes[0] if codes else None


def _agreement_type(item: Dict[str, Any]) -> Optional[str]:
    judgement = _as_dict(item.get("judgement"))
    val = _norm_str(judgement.get("agreement_type"))
    return val if val else None


def _overlap_ratio(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _bump(counter: Dict[str, int], key: Optional[str]) -> None:
    k = _norm_str(key)
    if not k:
        return
    counter[k] = counter.get(k, 0) + 1


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def evaluate_reason_alignment(items: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluate model_reason vs curator_reason alignment.

    Expected item shape (aligned to curator_label.schema.json):
    - model_reason.reason_codes / primary_reason / confidence
    - curator_reason.reason_codes / primary_reason / category / layer / plane /
      decision_type / cause_type / signal_type
    - judgement.agreement_type
    """

    total_items = 0
    exact_match_count = 0
    partial_match_count = 0
    mismatch_count = 0
    primary_reason_match_count = 0
    overlap_sum = 0.0

    high_confidence_mismatch_count = 0
    low_confidence_exact_count = 0

    by_category: Dict[str, int] = {}
    by_layer: Dict[str, int] = {}
    by_plane: Dict[str, int] = {}
    by_decision_type: Dict[str, int] = {}
    by_cause_type: Dict[str, int] = {}
    by_signal_type: Dict[str, int] = {}

    for item in items:
        if not isinstance(item, dict):
            continue

        total_items += 1

        model_reason = _as_dict(item.get("model_reason"))
        curator_reason = _as_dict(item.get("curator_reason"))
        agreement = _agreement_type(item)

        model_codes = _reason_codes(model_reason)
        curator_codes = _reason_codes(curator_reason)

        model_primary = _primary_reason(model_reason)
        curator_primary = _primary_reason(curator_reason)

        confidence = _norm_float(model_reason.get("confidence"))

        if agreement == "exact_match":
            exact_match_count += 1
        elif agreement == "partial_match":
            partial_match_count += 1
        elif agreement == "mismatch":
            mismatch_count += 1

        if model_primary and curator_primary and model_primary == curator_primary:
            primary_reason_match_count += 1

        overlap_sum += _overlap_ratio(model_codes, curator_codes)

        if confidence is not None:
            if confidence >= 0.8 and agreement == "mismatch":
                high_confidence_mismatch_count += 1
            if confidence <= 0.5 and agreement == "exact_match":
                low_confidence_exact_count += 1

        _bump(by_category, curator_reason.get("category"))
        _bump(by_layer, curator_reason.get("layer"))
        _bump(by_plane, curator_reason.get("plane"))
        _bump(by_decision_type, curator_reason.get("decision_type"))
        _bump(by_cause_type, curator_reason.get("cause_type"))
        _bump(by_signal_type, curator_reason.get("signal_type"))

    def _rate(n: int) -> float:
        return (n / total_items) if total_items > 0 else 0.0

    report = ReasonAlignmentSummary(
        total_items=total_items,
        exact_match_count=exact_match_count,
        partial_match_count=partial_match_count,
        mismatch_count=mismatch_count,
        primary_reason_match_count=primary_reason_match_count,
        primary_reason_match_rate=_rate(primary_reason_match_count),
        exact_match_rate=_rate(exact_match_count),
        partial_match_rate=_rate(partial_match_count),
        mismatch_rate=_rate(mismatch_count),
        avg_reason_code_overlap=(overlap_sum / total_items) if total_items > 0 else 0.0,
        high_confidence_mismatch_count=high_confidence_mismatch_count,
        low_confidence_exact_count=low_confidence_exact_count,
        by_category=by_category,
        by_layer=by_layer,
        by_plane=by_plane,
        by_decision_type=by_decision_type,
        by_cause_type=by_cause_type,
        by_signal_type=by_signal_type,
    )

    return {
        "report": asdict(report)
    }


__all__ = [
    "ReasonAlignmentSummary",
    "evaluate_reason_alignment",
]