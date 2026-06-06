from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _norm_str(x: Any) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip()
    return s if s else None


def _norm_int(x: Any) -> Optional[int]:
    try:
        if x is None or x == "":
            return None
        return int(x)
    except Exception:
        return None


def _norm_float(x: Any) -> Optional[float]:
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:
        return None


def _build_item(
    *,
    item_id: str,
    rank: Optional[int] = None,
    score: Optional[float] = None,
    primary_reason: Optional[str] = None,
    reason_codes: Optional[Iterable[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    codes = [str(x).strip() for x in (reason_codes or []) if str(x).strip()]

    reason = None
    if primary_reason or codes:
        reason = {
            "primary_reason": _norm_str(primary_reason) or (codes[0] if codes else None),
            "reason_codes": codes,
        }
        reason = {k: v for k, v in reason.items() if v is not None and v != []}

    obj = {
        "item_id": _norm_str(item_id),
        "rank": _norm_int(rank),
        "score": _norm_float(score),
        "reason": reason,
        "metadata": metadata if isinstance(metadata, dict) and metadata else None,
    }

    return {k: v for k, v in obj.items() if v is not None}


def build_recommendation_response(
    *,
    response_id: str,
    request_id: str,
    recommended_items: Iterable[Dict[str, Any]],
    provenance_id: Optional[str] = None,
    generated_at: Optional[str] = None,
    model_version: Optional[str] = None,
    feature_version: Optional[str] = None,
    experiment_id: Optional[str] = None,
    variant: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build recommendation response objects aligned with recommendation_response.schema.json.
    """

    model_info = None
    if model_version or feature_version:
        model_info = {
            "model_version": _norm_str(model_version),
            "feature_version": _norm_str(feature_version),
        }
        model_info = {k: v for k, v in model_info.items() if v is not None}

    experiment = None
    if experiment_id or variant:
        experiment = {
            "experiment_id": _norm_str(experiment_id),
            "variant": _norm_str(variant),
        }

    items: List[Dict[str, Any]] = []
    for raw in recommended_items:
        if not isinstance(raw, dict):
            continue

        raw_reason = raw.get("reason") if isinstance(raw.get("reason"), dict) else {}

        item = _build_item(
            item_id=str(raw.get("item_id") or raw.get("id") or "").strip(),
            rank=raw.get("rank"),
            score=raw.get("score"),
            primary_reason=raw.get("primary_reason") or raw_reason.get("primary_reason"),
            reason_codes=raw.get("reason_codes") or raw_reason.get("reason_codes"),
            metadata=raw.get("metadata"),
        )

        if item.get("item_id"):
            items.append(item)

    obj = {
        "response_id": _norm_str(response_id),
        "request_id": _norm_str(request_id),
        "provenance_id": _norm_str(provenance_id),
        "generated_at": generated_at or _now_iso(),
        "model_info": model_info,
        "recommended_items": items,
        "experiment": experiment,
    }

    return {k: v for k, v in obj.items() if v is not None}


__all__ = ["build_recommendation_response"]