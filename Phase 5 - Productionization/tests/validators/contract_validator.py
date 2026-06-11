from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


_FORBIDDEN_ENTRY_REASON_FIELDS = {
    "reason",
    "reason_codes",
    "primary_reason",
    "curator_reason",
    "model_reason",
    "judgement",
}


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


def validate_entry_event_contract(events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate entry-layer contract rules:

    - all entry events must include provenance_id
    - no semantic reason fields may appear in raw entry events
    """
    errors: List[str] = []
    checked = 0

    for idx, event in enumerate(events):
        checked += 1

        if not isinstance(event, dict):
            errors.append(f"events[{idx}] is not a dict")
            continue

        provenance_id = event.get("provenance_id")
        if not _is_nonempty_str(provenance_id):
            errors.append(f"events[{idx}] missing non-empty provenance_id")

        leaked = sorted(_FORBIDDEN_ENTRY_REASON_FIELDS.intersection(set(event.keys())))
        if leaked:
            errors.append(f"events[{idx}] leaked forbidden semantic fields: {', '.join(leaked)}")

    return _result(
        validator="contract_validator.entry_event",
        errors=errors,
        details={"checked": checked},
    )


def validate_interpreted_output_contract(outputs: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate interpretation bridge contract:

    - interpreted outputs must preserve raw event separately
    - derived_reason must not replace raw event
    """
    errors: List[str] = []
    checked = 0

    for idx, item in enumerate(outputs):
        checked += 1

        if not isinstance(item, dict):
            errors.append(f"outputs[{idx}] is not a dict")
            continue

        if "raw_event" in item:
            raw_event = item.get("raw_event")
            derived_reason = item.get("derived_reason")

            if not isinstance(raw_event, dict):
                errors.append(f"outputs[{idx}].raw_event must be a dict")
            else:
                provenance_id = raw_event.get("provenance_id")
                if not _is_nonempty_str(provenance_id):
                    errors.append(f"outputs[{idx}].raw_event missing provenance_id")

            if derived_reason is None:
                errors.append(f"outputs[{idx}] missing derived_reason")
        else:
            # tolerate alternate enriched output shape, but require some reason payload
            if item.get("derived_reason") is None and item.get("feedback_reason") is None and item.get("output") is None:
                errors.append(f"outputs[{idx}] missing interpreted reason payload")

    return _result(
        validator="contract_validator.interpreted_output",
        errors=errors,
        details={"checked": checked},
    )


def validate_curator_truth_contract(labels: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate curator-layer contract:

    - model_reason and curator_reason must both exist
    - provenance identity must be preserved
    """
    errors: List[str] = []
    checked = 0

    for idx, label in enumerate(labels):
        checked += 1

        if not isinstance(label, dict):
            errors.append(f"labels[{idx}] is not a dict")
            continue

        if not _is_nonempty_str(label.get("provenance_id")):
            errors.append(f"labels[{idx}] missing provenance_id")

        if not isinstance(label.get("model_reason"), dict):
            errors.append(f"labels[{idx}] missing model_reason dict")

        if not isinstance(label.get("curator_reason"), dict):
            errors.append(f"labels[{idx}] missing curator_reason dict")

    return _result(
        validator="contract_validator.curator_truth",
        errors=errors,
        details={"checked": checked},
    )


def validate_contract_bundle(
    *,
    entry_events: Optional[Iterable[Dict[str, Any]]] = None,
    interpreted_outputs: Optional[Iterable[Dict[str, Any]]] = None,
    curator_labels: Optional[Iterable[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Run all applicable contract checks and aggregate results.
    """
    errors: List[str] = []
    details: Dict[str, Any] = {}

    if entry_events is not None:
        res = validate_entry_event_contract(entry_events)
        details["entry_event"] = res
        errors.extend([f"entry_event: {e}" for e in res["errors"]])

    if interpreted_outputs is not None:
        res = validate_interpreted_output_contract(interpreted_outputs)
        details["interpreted_output"] = res
        errors.extend([f"interpreted_output: {e}" for e in res["errors"]])

    if curator_labels is not None:
        res = validate_curator_truth_contract(curator_labels)
        details["curator_truth"] = res
        errors.extend([f"curator_truth: {e}" for e in res["errors"]])

    return _result(
        validator="contract_validator.bundle",
        errors=errors,
        details=details,
    )