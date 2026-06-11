from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


def _result(
    *,
    validator: str,
    errors: List[str],
    warnings: Optional[List[str]] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "validator": validator,
        "passed": len(errors) == 0,
        "errors": errors,
        "warnings": warnings or [],
        "details": details or {},
    }


def _is_nonempty_str(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""


def _require_fields(obj: Dict[str, Any], required: Iterable[str], *, prefix: str = "") -> List[str]:
    errs: List[str] = []
    for name in required:
        if name not in obj or obj.get(name) is None:
            errs.append(f"{prefix}{name} missing")
    return errs


def validate_feedback_event_shape(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the minimal structural requirements of feedback_events.schema.json.

    Required per schema:
    - event_id
    - provenance_id
    - event_type
    - source_type
    - timestamp
    - payload
    """
    errors: List[str] = []

    if not isinstance(event, dict):
        return _result(
            validator="schema_validator.feedback_event",
            errors=["event is not a dict"],
        )

    required = ["event_id", "provenance_id", "event_type", "source_type", "timestamp", "payload"]
    errors.extend(_require_fields(event, required))

    for field in ["event_id", "provenance_id", "event_type", "source_type", "timestamp"]:
        if field in event and not _is_nonempty_str(event.get(field)):
            errors.append(f"{field} must be a non-empty string")

    if "payload" in event and not isinstance(event.get("payload"), dict):
        errors.append("payload must be a dict")

    if "context" in event and event.get("context") is not None and not isinstance(event.get("context"), dict):
        errors.append("context must be a dict when present")

    if "system_context" in event and event.get("system_context") is not None and not isinstance(event.get("system_context"), dict):
        errors.append("system_context must be a dict when present")

    if "experiment" in event and event.get("experiment") is not None and not isinstance(event.get("experiment"), dict):
        errors.append("experiment must be a dict when present")

    if "ingestion_metadata" in event and event.get("ingestion_metadata") is not None and not isinstance(event.get("ingestion_metadata"), dict):
        errors.append("ingestion_metadata must be a dict when present")

    return _result(
        validator="schema_validator.feedback_event",
        errors=errors,
        details={"checked_fields": required},
    )


def validate_curator_label_shape(label: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate the minimal structural requirements of curator_label.schema.json.

    Required per schema:
    - event_id
    - provenance_id
    - curation_id
    - timestamp
    - model_reason
    - curator_reason
    """
    errors: List[str] = []

    if not isinstance(label, dict):
        return _result(
            validator="schema_validator.curator_label",
            errors=["label is not a dict"],
        )

    required = ["event_id", "provenance_id", "curation_id", "timestamp", "model_reason", "curator_reason"]
    errors.extend(_require_fields(label, required))

    for field in ["event_id", "provenance_id", "curation_id", "timestamp"]:
        if field in label and not _is_nonempty_str(label.get(field)):
            errors.append(f"{field} must be a non-empty string")

    if "model_reason" in label and not isinstance(label.get("model_reason"), dict):
        errors.append("model_reason must be a dict")

    if "curator_reason" in label and not isinstance(label.get("curator_reason"), dict):
        errors.append("curator_reason must be a dict")

    if "judgement" in label and label.get("judgement") is not None and not isinstance(label.get("judgement"), dict):
        errors.append("judgement must be a dict when present")

    return _result(
        validator="schema_validator.curator_label",
        errors=errors,
        details={"checked_fields": required},
    )


def validate_structured_event_batch(events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate a batch of entry-layer structured events.

    By default, this applies feedback_event structural validation only when the
    object looks like a feedback event (source_type present). For non-feedback
    events, it validates the shared event envelope:
    - event_id
    - provenance_id
    - event_type
    - timestamp
    """
    errors: List[str] = []
    count = 0
    failed = 0

    for idx, event in enumerate(events):
        count += 1

        if not isinstance(event, dict):
            errors.append(f"events[{idx}] is not a dict")
            failed += 1
            continue

        # feedback events carry source_type / payload
        if "source_type" in event:
            res = validate_feedback_event_shape(event)
            if not res["passed"]:
                failed += 1
                errors.extend([f"events[{idx}]: {e}" for e in res["errors"]])
            continue

        envelope_required = ["event_id", "provenance_id", "event_type", "timestamp"]
        env_errs = _require_fields(event, envelope_required, prefix=f"events[{idx}].")
        if env_errs:
            failed += 1
            errors.extend(env_errs)

    return _result(
        validator="schema_validator.structured_event_batch",
        errors=errors,
        details={
            "checked": count,
            "failed": failed,
        },
    )