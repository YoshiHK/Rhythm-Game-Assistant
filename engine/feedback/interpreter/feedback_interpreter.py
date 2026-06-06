"""
feedback_interpreter.py

Phase 5 – Feedback Interpretation Layer

Purpose:
- Convert runtime signals -> standardized reason taxonomy labels
- Align with reason_taxonomy_v1.json
- PURE, deterministic, non-blocking

Non-goals:
- No mutation of runtime output
- No model updates
- No I/O or database interaction
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# -----------------------------------------------------------------------------
# Core interpreter
# -----------------------------------------------------------------------------

def interpret_feedback(
    *,
    trigger: Dict[str, Any],
    request: Dict[str, Any],
    run_result: Optional[Dict[str, Any]],
    diagnostics: Optional[Dict[str, Any]],
    tips_payload: Optional[Dict[str, Any]],
    personalization_context: Optional[Dict[str, Any]],
    localization_context: Optional[Dict[str, Any]],
    provenance_id: Optional[str],
    rationale: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Main interpretation entrypoint.

    Returns:
    {
        "reason_codes": [...],
        "primary_reason": "...",
        "confidence": float,
        "signals": {...}
    }
    """

    reason_codes: List[str] = []

    # -------------------------------------------------------------------------
    # 1) Raw signals
    # -------------------------------------------------------------------------
    execution_ok = isinstance(run_result, dict)
    has_diagnostics_error = isinstance(diagnostics, dict) and bool(diagnostics.get("error"))
    tips_missing = tips_payload is None

    trigger_surface = _as_str(trigger.get("surface")) if isinstance(trigger, dict) else ""
    request_mode = _as_str(request.get("mode")) if isinstance(request, dict) else ""

    # Personalization
    pers_source = _get(personalization_context, "decision_source")
    capability_tier = _get(personalization_context, "capability_tier")
    recommended_focus = _get(personalization_context, "recommended_focus")

    # Localization
    loc_meta = localization_context.get("meta") if isinstance(localization_context, dict) else {}
    locale_fallback = bool(_get(loc_meta, "fallback_used", False))
    localization_error = _as_str(_get(loc_meta, "error"))

    # Rationale
    normalized_rationale = _normalize_rationale_dict(rationale)
    primary_rationale = _as_str(normalized_rationale.get("primary_reason"))

    # -------------------------------------------------------------------------
    # 2) Rule mapping
    # -------------------------------------------------------------------------

    # Execution
    if not execution_ok or has_diagnostics_error:
        _safe_add(reason_codes, "EXEC_FAILURE")

    # Partial / missing output
    if execution_ok and tips_missing and request_mode == "song":
        _safe_add(reason_codes, "PAYLOAD_EXTRACTION_FAIL")

    if execution_ok and _selected_count_zero(diagnostics):
        _safe_add(reason_codes, "PARTIAL_OUTPUT")

    # Selection / fallback
    if _selector_fallback_used(diagnostics):
        _safe_add(reason_codes, "SELECTOR_FALLBACK_USED")

    # Personalization
    if pers_source == "recommend_api_legacy_fallback":
        _safe_add(reason_codes, "PERS_FALLBACK_LEGACY")

    if _capability_mismatch(capability_tier, recommended_focus):
        _safe_add(reason_codes, "CAPABILITY_MISCLASSIFIED")

    # Localization
    if locale_fallback:
        _safe_add(reason_codes, "LOCALE_FALLBACK_USED")

    if localization_error:
        _safe_add(reason_codes, "LOCALIZATION_ENGINE_FAIL")

    # Rationale / API
    if primary_rationale == "orchestrator_default":
        _safe_add(reason_codes, "RATIONALE_DEFAULT_USED")

    if trigger_surface and request_mode:
        if trigger_surface == "recommend_api" and request_mode not in {"song", "game"}:
            _safe_add(reason_codes, "REQUEST_NORMALIZATION_ERROR")

    if _resource_resolution_fail(diagnostics):
        _safe_add(reason_codes, "RESOURCE_RESOLUTION_FAIL")

    # Control / degraded mode
    if _degraded_mode_triggered(
        diagnostics=diagnostics,
        personalization_context=personalization_context,
        localization_context=localization_context,
    ):
        _safe_add(reason_codes, "DEGRADED_MODE_TRIGGERED")

    fallback_count = sum(1 for code in reason_codes if "FALLBACK" in code)
    if fallback_count >= 3:
        _safe_add(reason_codes, "FALLBACK_OVERUSE")

    # -------------------------------------------------------------------------
    # 3) Normalize output
    # -------------------------------------------------------------------------
    if not reason_codes:
        reason_codes = ["UNKNOWN"]

    primary_reason = _choose_primary_reason(reason_codes)
    confidence = _estimate_confidence(
        reason_codes=reason_codes,
        has_diagnostics_error=has_diagnostics_error,
        tips_missing=tips_missing,
    )

    signals = {
        "execution_ok": execution_ok,
        "has_diagnostics_error": has_diagnostics_error,
        "tips_missing": tips_missing,
        "trigger_surface": trigger_surface,
        "request_mode": request_mode,
        "pers_source": pers_source,
        "capability_tier": capability_tier,
        "recommended_focus": recommended_focus,
        "locale_fallback": locale_fallback,
        "localization_error": localization_error,
        "primary_rationale": primary_rationale,
        "has_provenance": bool(provenance_id),
    }

    return {
        "reason_codes": reason_codes,
        "primary_reason": primary_reason,
        "confidence": confidence,
        "signals": signals,
    }


def attach_feedback_reason(
    *,
    payload: Dict[str, Any],
    reason: Dict[str, Any],
    key: str = "feedback_reason",
) -> Dict[str, Any]:
    """
    Non-breaking helper to attach interpreter output to payload.

    Intended for API / payload annotation only.
    """
    if isinstance(payload, dict):
        payload[key] = reason
    return payload


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _safe_add(lst: List[str], value: str) -> None:
    if value not in lst:
        lst.append(value)


def _get(obj: Optional[Dict[str, Any]], key: str, default: Any = None) -> Any:
    if not isinstance(obj, dict):
        return default
    return obj.get(key, default)


def _as_str(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _selector_fallback_used(diagnostics: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(diagnostics, dict):
        return False

    selector = _as_str(diagnostics.get("selector"))
    if "fallback" in selector.lower():
        return True

    degraded_reasons = diagnostics.get("degraded_reasons")
    if isinstance(degraded_reasons, list):
        joined = " ".join(str(x) for x in degraded_reasons)
        if "fallback" in joined.lower():
            return True

    return "fallback" in str(diagnostics).lower()


def _selected_count_zero(diagnostics: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(diagnostics, dict):
        return False
    try:
        return int(diagnostics.get("selected_count")) == 0
    except Exception:
        return False


def _capability_mismatch(capability: Optional[str], focus: Optional[str]) -> bool:
    """
    Detect mismatch between inferred capability and recommended focus.
    Conservative deterministic rules only.
    """
    capability_norm = _as_str(capability).lower()
    focus_norm = _as_str(focus).lower()

    if not capability_norm or not focus_norm:
        return False

    if capability_norm == "beginner" and "top_tier" in focus_norm:
        return True

    if capability_norm == "advanced" and "clear_stability" in focus_norm:
        return True

    return False


def _normalize_rationale_dict(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Normalize rationale payload into:
    {
        "reason_codes": [...],
        "primary_reason": "..."
    }
    """
    if not isinstance(raw, dict):
        return {
            "reason_codes": ["unknown"],
            "primary_reason": "unknown",
        }

    reason_codes = raw.get("reason_codes")
    if isinstance(reason_codes, list) and reason_codes:
        primary = raw.get("primary_reason") or reason_codes[0]
        return {
            "reason_codes": [str(x) for x in reason_codes],
            "primary_reason": str(primary),
        }

    if isinstance(raw.get("reason"), str):
        return {
            "reason_codes": [raw["reason"]],
            "primary_reason": raw["reason"],
        }

    primary = raw.get("primary_reason")
    if isinstance(primary, str) and primary:
        return {
            "reason_codes": [primary],
            "primary_reason": primary,
        }

    return {
        "reason_codes": ["unknown"],
        "primary_reason": "unknown",
    }


def _resource_resolution_fail(diagnostics: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(diagnostics, dict):
        return False

    stage = _as_str(diagnostics.get("stage")).lower()
    error = _as_str(diagnostics.get("error")).lower()

    if "resolve" in stage:
        return True

    if "chart_ref" in error:
        return True

    return False


def _degraded_mode_triggered(
    *,
    diagnostics: Optional[Dict[str, Any]],
    personalization_context: Optional[Dict[str, Any]],
    localization_context: Optional[Dict[str, Any]],
) -> bool:
    """
    Best-effort degraded-mode detection.
    """
    if isinstance(diagnostics, dict):
        if bool(diagnostics.get("degraded_mode")):
            return True
        reasons = diagnostics.get("degraded_reasons")
        if isinstance(reasons, list) and len(reasons) > 0:
            return True

    if isinstance(personalization_context, dict):
        diag = personalization_context.get("diagnostics")
        if isinstance(diag, dict) and diag.get("error"):
            return True

    if isinstance(localization_context, dict):
        meta = localization_context.get("meta")
        if isinstance(meta, dict) and meta.get("fallback_used"):
            return True

    return False


def _choose_primary_reason(reason_codes: List[str]) -> str:
    """
    Stable priority ordering for primary_reason selection.
    """
    priority = [
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
    ]

    for code in priority:
        if code in reason_codes:
            return code

    return reason_codes[0] if reason_codes else "UNKNOWN"


def _estimate_confidence(
    *,
    reason_codes: List[str],
    has_diagnostics_error: bool,
    tips_missing: bool,
) -> float:
    """
    Simple deterministic confidence estimation.
    """
    if "EXEC_FAILURE" in reason_codes and has_diagnostics_error:
        return 0.95

    if "PAYLOAD_EXTRACTION_FAIL" in reason_codes and tips_missing:
        return 0.90

    if len(reason_codes) >= 3:
        return 0.80

    if len(reason_codes) == 2:
        return 0.70

    return 0.60


__all__ = [
    "interpret_feedback",
    "attach_feedback_reason",
]