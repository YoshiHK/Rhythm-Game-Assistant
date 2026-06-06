from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, Optional


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _norm_str(x: Any) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip()
    return s if s else None


def _norm_float(x: Any) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def _norm_bool(x: Any) -> Optional[bool]:
    if isinstance(x, bool):
        return x
    return None


def _reason_block(
    *,
    reason_codes: Optional[Iterable[str]] = None,
    primary_reason: Optional[str] = None,
    category: Optional[str] = None,
    layer: Optional[str] = None,
    plane: Optional[str] = None,
    decision_type: Optional[str] = None,
    cause_type: Optional[str] = None,
    signal_type: Optional[str] = None,
) -> Dict[str, Any]:
    codes = [str(x).strip() for x in (reason_codes or []) if str(x).strip()]
    obj = {
        "reason_codes": codes,
        "primary_reason": _norm_str(primary_reason) or (codes[0] if codes else None),
        "category": _norm_str(category),
        "layer": _norm_str(layer),
        "plane": _norm_str(plane),
        "decision_type": _norm_str(decision_type),
        "cause_type": _norm_str(cause_type),
        "signal_type": _norm_str(signal_type),
    }
    return {k: v for k, v in obj.items() if v is not None and v != []}


def build_curator_label(
    *,
    event_id: str,
    provenance_id: str,
    curation_id: str,
    model_reason_codes: Optional[Iterable[str]] = None,
    model_primary_reason: Optional[str] = None,
    model_confidence: Optional[float] = None,
    curator_reason_codes: Optional[Iterable[str]] = None,
    curator_primary_reason: Optional[str] = None,
    category: Optional[str] = None,
    layer: Optional[str] = None,
    plane: Optional[str] = None,
    decision_type: Optional[str] = None,
    cause_type: Optional[str] = None,
    signal_type: Optional[str] = None,
    curator_id: Optional[str] = None,
    is_correct: Optional[bool] = None,
    agreement_type: Optional[str] = None,
    severity: Optional[str] = None,
    notes: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build curator label objects aligned with curator_label.schema.json.
    """

    model_reason = {
        "reason_codes": [str(x).strip() for x in (model_reason_codes or []) if str(x).strip()],
        "primary_reason": _norm_str(model_primary_reason),
        "confidence": _norm_float(model_confidence),
    }
    model_reason = {k: v for k, v in model_reason.items() if v is not None and v != []}

    curator_reason = _reason_block(
        reason_codes=curator_reason_codes,
        primary_reason=curator_primary_reason,
        category=category,
        layer=layer,
        plane=plane,
        decision_type=decision_type,
        cause_type=cause_type,
        signal_type=signal_type,
    )

    judgement = None
    if is_correct is not None or agreement_type or severity:
        judgement = {
            "is_correct": _norm_bool(is_correct),
            "agreement_type": _norm_str(agreement_type),
            "severity": _norm_str(severity),
        }
        judgement = {k: v for k, v in judgement.items() if v is not None}

    obj = {
        "event_id": _norm_str(event_id),
        "provenance_id": _norm_str(provenance_id),
        "curation_id": _norm_str(curation_id),
        "timestamp": timestamp or _now_iso(),
        "curator_id": _norm_str(curator_id),
        "model_reason": model_reason,
        "curator_reason": curator_reason,
        "judgement": judgement,
        "notes": _norm_str(notes),
    }

    return {k: v for k, v in obj.items() if v is not None}


__all__ = ["build_curator_label"]