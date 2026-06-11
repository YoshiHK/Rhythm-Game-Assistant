from __future__ import annotations

import json
from pathlib import Path
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


def _normalize_jsonable(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate_object_pair(a: Any, b: Any, *, label: str = "object_pair") -> Dict[str, Any]:
    """
    Validate that two JSON-serializable objects are identical after normalization.
    """
    errors: List[str] = []

    try:
        na = _normalize_jsonable(a)
        nb = _normalize_jsonable(b)
        if na != nb:
            errors.append(f"{label} mismatch")
    except Exception as e:
        errors.append(f"{label} normalization failed: {e}")

    return _result(
        validator="determinism_validator.object_pair",
        errors=errors,
        details={"label": label},
    )


def validate_json_file_pair(path_a: str | Path, path_b: str | Path, *, label: str = "json_file_pair") -> Dict[str, Any]:
    """
    Validate that two JSON files are identical after normalized parse/serialize.
    """
    errors: List[str] = []

    pa = Path(path_a)
    pb = Path(path_b)

    if not pa.exists():
        errors.append(f"{label}: file missing: {pa}")
    if not pb.exists():
        errors.append(f"{label}: file missing: {pb}")

    if errors:
        return _result(
            validator="determinism_validator.json_file_pair",
            errors=errors,
            details={"label": label},
        )

    try:
        a = json.loads(pa.read_text(encoding="utf-8"))
        b = json.loads(pb.read_text(encoding="utf-8"))
        na = _normalize_jsonable(a)
        nb = _normalize_jsonable(b)
        if na != nb:
            errors.append(f"{label} mismatch between {pa} and {pb}")
    except Exception as e:
        errors.append(f"{label} read/normalize failed: {e}")

    return _result(
        validator="determinism_validator.json_file_pair",
        errors=errors,
        details={"label": label, "path_a": str(pa), "path_b": str(pb)},
    )


def validate_named_artifact_pairs(pairs: Iterable[Dict[str, str]]) -> Dict[str, Any]:
    """
    Validate multiple named JSON artifact pairs.

    Each pair item should look like:
    {
      "label": "...",
      "path_a": "...",
      "path_b": "..."
    }
    """
    errors: List[str] = []
    details: Dict[str, Any] = {}

    for idx, pair in enumerate(pairs):
        label = pair.get("label", f"pair_{idx}")
        res = validate_json_file_pair(pair["path_a"], pair["path_b"], label=label)
        details[label] = res
        errors.extend([f"{label}: {e}" for e in res["errors"]])

    return _result(
        validator="determinism_validator.named_artifact_pairs",
        errors=errors,
        details=details,
    )
