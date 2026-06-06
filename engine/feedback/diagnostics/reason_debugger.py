"""
reason_debugger.py

engine/feedback/diagnostics/

Purpose:
- Provide deterministic debugging helpers for feedback_reason outputs
- Explain why a primary reason was chosen from interpreter output
- Compare machine reason vs curator reason without mutating data

Non-goals:
- No runtime mutations
- No I/O
- No model updates
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


_PRIMARY_PRIORITY = [
    "EXEC_FAILURE",
    "PAYLOAD_EXTRACTION_FAIL",
    "PARTIAL_OUTPUT",
    "SELECTOR_FALLBACK_USED",
    "PERS_FALLBACK_LEGACY",
    "CAPABILITY_MISCLASSIFIED",
    "LOCALE_FALLBACK_USED",
    "LOCALIZATION_ENGINE_FAIL",
    "RATIONALE_DEFAULT_USED",
    "REQUEST_NORMALIZATION_ERROR",
    "RESOURCE_RESOLUTION_FAIL",
    "DEGRADED_MODE_TRIGGERED",
    "FALLBACK_OVERUSE",
    "UNKNOWN",
]


def explain_reason(reason: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a feedback_reason block into a debugger-friendly explanation.

    Expected input shape:
    {
        "reason_codes": [...],
        "primary_reason": "...",
        "confidence": 0.8,
        "signals": {...}
    }
    """
    if not isinstance(reason, dict):
        return {
            "primary_reason": "UNKNOWN",
            "reason_codes": ["UNKNOWN"],
            "confidence": None,
            "signals": {},
            "priority_explanation": "invalid_reason_object",
        }

    reason_codes = [str(x).strip() for x in (reason.get("reason_codes") or []) if str(x).strip()]
    primary_reason = str(reason.get("primary_reason") or (reason_codes[0] if reason_codes else "UNKNOWN")).strip()
    confidence = reason.get("confidence")
    signals = reason.get("signals") if isinstance(reason.get("signals"), dict) else {}

    return {
        "primary_reason": primary_reason,
        "reason_codes": reason_codes or ["UNKNOWN"],
        "confidence": confidence,
        "signals": signals,
        "priority_explanation": _describe_priority(primary_reason, reason_codes),
    }


def compare_model_vs_curator(
    *,
    model_reason: Dict[str, Any],
    curator_reason: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compare machine hypothesis with human-labeled ground truth.
    """
    m_codes = _reason_codes(model_reason)
    c_codes = _reason_codes(curator_reason)
    m_primary = _primary_reason(model_reason)
    c_primary = _primary_reason(curator_reason)

    overlap = sorted(set(m_codes) & set(c_codes))
    union = sorted(set(m_codes) | set(c_codes))
    overlap_ratio = (len(overlap) / len(union)) if union else 1.0

    agreement_type = _agreement_type(m_primary, c_primary, overlap_ratio)

    return {
        "model_primary": m_primary,
        "curator_primary": c_primary,
        "model_reason_codes": m_codes,
        "curator_reason_codes": c_codes,
        "overlap_reason_codes": overlap,
        "overlap_ratio": overlap_ratio,
        "agreement_type": agreement_type,
    }


def debug_payload_reason(payload: Dict[str, Any], *, key: str = "feedback_reason") -> Dict[str, Any]:
    """
    Convenience helper for runtime payloads that already contain feedback_reason.
    """
    if not isinstance(payload, dict):
        return explain_reason({})
    return explain_reason(payload.get(key) if isinstance(payload.get(key), dict) else {})


def _reason_codes(reason: Dict[str, Any]) -> List[str]:
    if not isinstance(reason, dict):
        return []
    return [str(x).strip() for x in (reason.get("reason_codes") or []) if str(x).strip()]


def _primary_reason(reason: Dict[str, Any]) -> Optional[str]:
    if not isinstance(reason, dict):
        return None
    primary = str(reason.get("primary_reason") or "").strip()
    if primary:
        return primary
    codes = _reason_codes(reason)
    return codes[0] if codes else None


def _agreement_type(m_primary: Optional[str], c_primary: Optional[str], overlap_ratio: float) -> str:
    if m_primary and c_primary and m_primary == c_primary:
        return "exact_match"
    if overlap_ratio > 0.0:
        return "partial_match"
    return "mismatch"


def _describe_priority(primary_reason: str, reason_codes: List[str]) -> str:
    if not reason_codes:
        return "no_reason_codes"
    try:
        idx = _PRIMARY_PRIORITY.index(primary_reason)
        return f"primary_reason_selected_by_priority_index:{idx}"
    except ValueError:
        return "primary_reason_not_in_priority_table"


__all__ = [
    "explain_reason",
    "compare_model_vs_curator",
    "debug_payload_reason",
]
