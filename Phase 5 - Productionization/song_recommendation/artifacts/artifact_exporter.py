from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


# -----------------------------------------------------------------------------
# Utils
# -----------------------------------------------------------------------------

def _stable_json_dumps(obj: Dict[str, Any]) -> str:
    """
    Deterministic JSON serialization for auditability.
    """
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _as_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


# -----------------------------------------------------------------------------
# Minimal validation (safe, non-invasive)
# -----------------------------------------------------------------------------

def _validate_selector_params(params: Dict[str, Any]) -> None:
    """
    Minimal contract enforcement (NOT full schema validation).
    """
    if not isinstance(params, dict):
        raise ValueError("params must be dict")

    if "selector_params" not in params:
        raise ValueError("missing selector_params")

    sp = params.get("selector_params")
    if not isinstance(sp, dict):
        raise ValueError("selector_params must be dict")

    required = ["widen_steps", "top_producers", "rank_decay_alpha"]
    for k in required:
        if k not in sp:
            raise ValueError(f"missing selector_params.{k}")

    if "schema_version" not in params:
        raise ValueError("missing schema_version")


def _wrap_artifact(
    payload: Dict[str, Any],
    *,
    artifact_type: str,
    version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Standard artifact envelope.
    """
    return {
        "artifact_type": artifact_type,
        "artifact_schema_version": version or "v1",
        "payload": payload,
    }


# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class ArtifactPaths:
    """
    Conventional Phase 5 artifact file names (song recommendation).
    """
    root_dir: Path

    selector_params_filename: str = "song_selector_params.json"
    training_report_filename: str = "song_selector_training_report.json"
    evaluation_report_filename: str = "song_selector_evaluation_report.json"
    baseline_metrics_filename: str = "song_selector_baseline_metrics.json"

    def selector_params_path(self) -> Path:
        return self.root_dir / self.selector_params_filename

    def training_report_path(self) -> Path:
        return self.root_dir / self.training_report_filename

    def evaluation_report_path(self) -> Path:
        return self.root_dir / self.evaluation_report_filename

    def baseline_metrics_path(self) -> Path:
        return self.root_dir / self.baseline_metrics_filename


# -----------------------------------------------------------------------------
# Writers (offline only)
# -----------------------------------------------------------------------------

def write_song_selector_params(
    params: Dict[str, Any],
    *,
    paths: ArtifactPaths,
) -> Path:
    """
    Write deployment-safe selector params.

    - Enforces minimal contract
    - Wraps artifact with metadata envelope
    """
    params = _as_dict(params)
    _validate_selector_params(params)

    _ensure_dir(paths.root_dir)

    wrapped = _wrap_artifact(
        params,
        artifact_type="selector_params",
        version=params.get("schema_version"),
    )

    p = paths.selector_params_path()
    p.write_text(_stable_json_dumps(wrapped), encoding="utf-8")
    return p


def write_training_report(
    report: Dict[str, Any],
    *,
    paths: ArtifactPaths,
) -> Path:
    """
    Write training report (QA + audit).
    """
    report = _as_dict(report)

    _ensure_dir(paths.root_dir)

    wrapped = _wrap_artifact(
        report,
        artifact_type="training_report",
    )

    p = paths.training_report_path()
    p.write_text(_stable_json_dumps(wrapped), encoding="utf-8")
    return p


def write_evaluation_report(
    report: Dict[str, Any],
    *,
    paths: ArtifactPaths,
) -> Path:
    """
    Write evaluation report (regression guards + metrics).
    """
    report = _as_dict(report)

    _ensure_dir(paths.root_dir)

    wrapped = _wrap_artifact(
        report,
        artifact_type="evaluation_report",
    )

    p = paths.evaluation_report_path()
    p.write_text(_stable_json_dumps(wrapped), encoding="utf-8")
    return p


def write_baseline_metrics_snapshot(
    metrics: Dict[str, Any],
    *,
    paths: ArtifactPaths,
) -> Path:
    """
    Write baseline snapshot with metadata.

    Used for future regression comparison.
    """
    metrics = _as_dict(metrics)

    _ensure_dir(paths.root_dir)

    wrapped = _wrap_artifact(
        metrics,
        artifact_type="baseline_metrics",
    )

    p = paths.baseline_metrics_path()
    p.write_text(_stable_json_dumps(wrapped), encoding="utf-8")
    return p


# -----------------------------------------------------------------------------
# Loaders (offline only)
# -----------------------------------------------------------------------------

def load_baseline_metrics_snapshot(
    *,
    paths: ArtifactPaths,
) -> Optional[Dict[str, Any]]:
    """
    Load baseline metrics snapshot.

    Returns:
    - payload dict
    - None if missing / invalid
    """
    p = paths.baseline_metrics_path()
    if not p.exists():
        return None

    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            return None

        payload = obj.get("payload")
        return payload if isinstance(payload, dict) else None

    except Exception:
        return None


__all__ = [
    "ArtifactPaths",
    "write_song_selector_params",
    "write_training_report",
    "write_evaluation_report",
    "write_baseline_metrics_snapshot",
    "load_baseline_metrics_snapshot",
]