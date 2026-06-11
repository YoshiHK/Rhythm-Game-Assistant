from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


def _stable_json_dumps(obj: Dict[str, Any]) -> str:
    """
    Deterministic JSON serialization for auditability.
    """
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class ArtifactPaths:
    """
    Conventional Phase 5 artifact file names (song recommendation).

    You can point these into your build/output folder.
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


# ---------------------------------------------------------------------
# Writers (offline only)
# ---------------------------------------------------------------------

def write_song_selector_params(params: Dict[str, Any], *, paths: ArtifactPaths) -> Path:
    """
    Write deployment-safe static selector parameters.

    NOTE:
    - Phase 6 runtime MUST NOT load artifacts dynamically.
    - This file is meant for deployment pipelines (build-time integration).
    """
    _ensure_dir(paths.root_dir)
    p = paths.selector_params_path()
    p.write_text(_stable_json_dumps(params), encoding="utf-8")
    return p


def write_training_report(report: Dict[str, Any], *, paths: ArtifactPaths) -> Path:
    """
    Write training/calibration report (offline QA + audit).
    """
    _ensure_dir(paths.root_dir)
    p = paths.training_report_path()
    p.write_text(_stable_json_dumps(report), encoding="utf-8")
    return p


def write_evaluation_report(report: Dict[str, Any], *, paths: ArtifactPaths) -> Path:
    """
    Write evaluation report (offline QA + regression guards).
    """
    _ensure_dir(paths.root_dir)
    p = paths.evaluation_report_path()
    p.write_text(_stable_json_dumps(report), encoding="utf-8")
    return p


def write_baseline_metrics_snapshot(metrics: Dict[str, Any], *, paths: ArtifactPaths) -> Path:
    """
    Write baseline metrics snapshot for future delta comparisons.

    This snapshot is used offline only to compare:
    - accept/play/completion deltas
    - regression guard thresholds
    """
    _ensure_dir(paths.root_dir)
    p = paths.baseline_metrics_path()
    p.write_text(_stable_json_dumps(metrics), encoding="utf-8")
    return p


# ---------------------------------------------------------------------
# Loaders (offline only)
# ---------------------------------------------------------------------

def load_baseline_metrics_snapshot(*, paths: ArtifactPaths) -> Optional[Dict[str, Any]]:
    """
    Load baseline metrics snapshot if present.

    Returns None if missing or invalid.
    """
    p = paths.baseline_metrics_path()
    if not p.exists():
        return None
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None