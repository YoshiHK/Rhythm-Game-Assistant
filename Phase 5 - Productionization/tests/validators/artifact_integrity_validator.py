from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

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


def validate_artifact_file(path: str | Path, *, require_envelope: bool = True) -> Dict[str, Any]:
    """
    Validate a single JSON artifact file:

    - file exists
    - file is parseable JSON
    - optional envelope fields exist
    """
    errors: List[str] = []
    p = Path(path)

    if not p.exists():
        errors.append(f"artifact file missing: {p}")
        return _result(
            validator="artifact_integrity_validator.artifact_file",
            errors=errors,
            details={"path": str(p)},
        )

    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        errors.append(f"artifact JSON parse failed: {e}")
        return _result(
            validator="artifact_integrity_validator.artifact_file",
            errors=errors,
            details={"path": str(p)},
        )

    if require_envelope:
        if not isinstance(obj, dict):
            errors.append("artifact must be a dict when envelope is required")
        else:
            if obj.get("artifact_type") is None:
                errors.append("artifact missing artifact_type")
            if obj.get("payload") is None:
                errors.append("artifact missing payload")

    return _result(
        validator="artifact_integrity_validator.artifact_file",
        errors=errors,
        details={"path": str(p), "require_envelope": require_envelope},
    )


def validate_phase5_artifact_set(
    *,
    artifact_paths: Dict[str, str],
    required_keys: Optional[Iterable[str]] = None,
    require_envelope: bool = True,
) -> Dict[str, Any]:
    """
    Validate a standard Phase 5 artifact set.

    Typical required keys:
    - selector_params
    - training_report
    - evaluation_report
    """
    errors: List[str] = []
    details: Dict[str, Any] = {}
    required = list(required_keys or ("selector_params", "training_report", "evaluation_report"))

    for key in required:
        path = artifact_paths.get(key)
        if path is None or str(path).strip() == "":
            errors.append(f"missing artifact path for key: {key}")
            continue

        res = validate_artifact_file(path, require_envelope=require_envelope)
        details[key] = res
        errors.extend([f"{key}: {e}" for e in res["errors"]])

    return _result(
        validator="artifact_integrity_validator.phase5_artifact_set",
        errors=errors,
        details=details,
    )


def validate_pipeline_result_artifacts(
    pipeline_result: Dict[str, Any],
    *,
    require_envelope: bool = True,
) -> Dict[str, Any]:
    """
    Validate artifacts using the typical pipeline_result shape:

    {
      "result": {
        "paths": {...}
      }
    }

    or directly:
    {
      "paths": {...}
    }
    """
    errors: List[str] = []
    details: Dict[str, Any] = {}

    obj = pipeline_result if isinstance(pipeline_result, dict) else {}
    maybe_paths = None

    if isinstance(obj.get("result"), dict) and isinstance(obj["result"].get("paths"), dict):
        maybe_paths = obj["result"]["paths"]
    elif isinstance(obj.get("paths"), dict):
        maybe_paths = obj["paths"]

    if not isinstance(maybe_paths, dict):
        errors.append("pipeline_result missing paths dict")
        return _result(
            validator="artifact_integrity_validator.pipeline_result",
            errors=errors,
        )

    res = validate_phase5_artifact_set(
        artifact_paths=maybe_paths,
        require_envelope=require_envelope,
    )
    details["artifact_set"] = res
    errors.extend(res["errors"])

    return _result(
        validator="artifact_integrity_validator.pipeline_result",
        errors=errors,
        details=details,
    )
