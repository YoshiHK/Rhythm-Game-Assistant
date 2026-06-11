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


def validate_event_coverage(
    events: Iterable[Dict[str, Any]],
    *,
    min_events: int = 1,
    required_event_types: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """
    Validate event-coverage expectations for a single test case.
    """
    errors: List[str] = []
    evs = [e for e in events if isinstance(e, dict)]

    if len(evs) < min_events:
        errors.append(f"structured_events_count {len(evs)} < min_events {min_events}")

    actual_types = [e.get("event_type") for e in evs if e.get("event_type") is not None]
    required = list(required_event_types or [])

    for required_type in required:
        if required_type not in actual_types:
            errors.append(f"missing required event_type: {required_type}")

    return _result(
        validator="coverage_validator.event_coverage",
        errors=errors,
        details={
            "structured_events_count": len(evs),
            "actual_event_types": actual_types,
            "required_event_types": required,
        },
    )


def validate_interpretation_coverage(
    outputs: Iterable[Dict[str, Any]],
    *,
    require_interpretation_output: bool = False,
) -> Dict[str, Any]:
    """
    Validate whether interpretation outputs are present when expected.
    """
    errors: List[str] = []
    outs = [o for o in outputs if isinstance(o, dict)]

    if require_interpretation_output and len(outs) == 0:
        errors.append("interpretation output required but none produced")

    return _result(
        validator="coverage_validator.interpretation_coverage",
        errors=errors,
        details={"interpreted_output_count": len(outs)},
    )


def validate_artifact_coverage(
    *,
    artifact_paths: Dict[str, str],
    required_artifacts: Iterable[str],
) -> Dict[str, Any]:
    """
    Validate that expected artifact path keys are present.
    """
    errors: List[str] = []
    required = list(required_artifacts)

    for key in required:
        value = artifact_paths.get(key)
        if value is None or str(value).strip() == "":
            errors.append(f"missing required artifact path key: {key}")

    return _result(
        validator="coverage_validator.artifact_coverage",
        errors=errors,
        details={"required_artifacts": required},
    )


def validate_coverage_bundle(
    *,
    events: Optional[Iterable[Dict[str, Any]]] = None,
    interpreted_outputs: Optional[Iterable[Dict[str, Any]]] = None,
    artifact_paths: Optional[Dict[str, str]] = None,
    min_events: int = 1,
    required_event_types: Optional[Iterable[str]] = None,
    require_interpretation_output: bool = False,
    required_artifacts: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """
    Aggregate coverage checks into a single report.
    """
    errors: List[str] = []
    details: Dict[str, Any] = {}

    if events is not None:
        res = validate_event_coverage(
            events,
            min_events=min_events,
            required_event_types=required_event_types,
        )
        details["events"] = res
        errors.extend([f"events: {e}" for e in res["errors"]])

    if interpreted_outputs is not None:
        res = validate_interpretation_coverage(
            interpreted_outputs,
            require_interpretation_output=require_interpretation_output,
        )
        details["interpretation"] = res
        errors.extend([f"interpretation: {e}" for e in res["errors"]])

    if artifact_paths is not None and required_artifacts is not None:
        res = validate_artifact_coverage(
            artifact_paths=artifact_paths,
            required_artifacts=required_artifacts,
        )
        details["artifacts"] = res
        errors.extend([f"artifacts: {e}" for e in res["errors"]])

    return _result(
        validator="coverage_validator.bundle",
        errors=errors,
        details=details,
    )