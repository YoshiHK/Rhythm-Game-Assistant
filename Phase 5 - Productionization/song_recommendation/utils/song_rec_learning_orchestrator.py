from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ---------------------------------------------------------------------
# Config / Contracts
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class OrchestratorConfig:
    """
    Offline orchestration config for the Phase 5 song recommendation learning loop.

    This orchestrator is NOT a runtime engine.
    It only runs offline dataflow for:

      feedback -> aggregation -> features -> training -> evaluation -> artifacts

    Design constraints:
    - offline only
    - deterministic
    - deployment-safe
    - no runtime dependencies
    """

    # Input parsing
    allow_jsonl: bool = True          # accept .jsonl / .ndjson
    allow_json_array: bool = True     # accept .json list[dict] or {"events":[...]}

    # Baseline usage
    compare_to_baseline: bool = True
    update_baseline_snapshot: bool = False  # overwrite baseline only after successful guarded run

    # Artifact directory layout
    artifacts_subdir: str = "song_recommendation"

    # Failure handling
    strict: bool = True

    # If True, empty input is treated as failure
    require_nonempty_events: bool = False


# ---------------------------------------------------------------------
# Imports (support both package and flat layouts)
# ---------------------------------------------------------------------

def _imports():
    """
    Import Phase 5 pipeline layers with robust fallback.
    """
    try:
        from phase5.song_recommendation.aggregation import aggregate_song_feedback_events
        from phase5.song_recommendation.features import build_selection_feature_rows
        from phase5.song_recommendation.training import train_song_selector_params
        from phase5.song_recommendation.evaluation import evaluate_selection_quality
        from phase5.song_recommendation.artifacts import (
            ArtifactPaths,
            write_song_selector_params,
            write_training_report,
            write_evaluation_report,
            write_baseline_metrics_snapshot,
            load_baseline_metrics_snapshot,
        )
        return (
            aggregate_song_feedback_events,
            build_selection_feature_rows,
            train_song_selector_params,
            evaluate_selection_quality,
            ArtifactPaths,
            write_song_selector_params,
            write_training_report,
            write_evaluation_report,
            write_baseline_metrics_snapshot,
            load_baseline_metrics_snapshot,
        )
    except Exception:
        # Flat fallback (for notebooks / local runs)
        from aggregate_song_feedback import aggregate_song_feedback_events
        from selection_features import build_selection_feature_rows
        from train_selector_params import train_song_selector_params
        from evaluate_selection_quality import evaluate_selection_quality
        from artifact_exporter import (
            ArtifactPaths,
            write_song_selector_params,
            write_training_report,
            write_evaluation_report,
            write_baseline_metrics_snapshot,
            load_baseline_metrics_snapshot,
        )
        return (
            aggregate_song_feedback_events,
            build_selection_feature_rows,
            train_song_selector_params,
            evaluate_selection_quality,
            ArtifactPaths,
            write_song_selector_params,
            write_training_report,
            write_evaluation_report,
            write_baseline_metrics_snapshot,
            load_baseline_metrics_snapshot,
        )


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _as_event_list(x: Any) -> List[Dict[str, Any]]:
    if x is None:
        return []
    if isinstance(x, list):
        return [e for e in x if isinstance(e, dict)]
    try:
        return [e for e in x if isinstance(e, dict)]
    except Exception:
        return []


def _as_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


# ---------------------------------------------------------------------
# Input loaders (offline convenience)
# ---------------------------------------------------------------------

def load_feedback_events(
    path: str | Path,
    *,
    config: OrchestratorConfig = OrchestratorConfig(),
) -> List[Dict[str, Any]]:
    """
    Load Phase 6 forward-only song recommendation feedback events from disk.

    Supported formats:
    - JSONL / NDJSON: one JSON object per line
    - JSON list of objects
    - JSON convenience wrapper: {"events": [...]}

    This is Phase 5 offline I/O only and MUST NOT be used by runtime.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"feedback events file not found: {p}")

    text = p.read_text(encoding="utf-8").strip()
    if not text:
        return []

    # JSONL / NDJSON
    if config.allow_jsonl and p.suffix.lower() in {".jsonl", ".ndjson"}:
        out: List[Dict[str, Any]] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                out.append(obj)
        return out

    # JSON list / wrapper
    if config.allow_json_array:
        obj = json.loads(text)

        if isinstance(obj, list):
            return [x for x in obj if isinstance(x, dict)]

        if isinstance(obj, dict):
            node = obj.get("events")
            if isinstance(node, list):
                return [x for x in node if isinstance(x, dict)]

    raise ValueError(f"Unsupported feedback events format: {p}")


# ---------------------------------------------------------------------
# Orchestrator entrypoint (offline only)
# ---------------------------------------------------------------------

def run_song_rec_learning_pipeline(
    *,
    events: Iterable[Dict[str, Any]],
    artifact_root_dir: str | Path,
    config: OrchestratorConfig = OrchestratorConfig(),
) -> Dict[str, Any]:
    """
    Run the full offline Song Recommendation learning pipeline:

      feedback events
        -> aggregation (selection-level)
        -> features (selection-level)
        -> training (heuristic calibration)
        -> evaluation (metrics + regression guards)
        -> artifact writeout (deployment-only outputs)

    Returns:
    {
      "status": "OK" | "GUARD_FAIL" | "NO_DATA",
      "artifact_dir": "...",
      "paths": {...},
      "summary": {...}
    }

    This function is deterministic given identical inputs.
    """
    (
        aggregate_song_feedback_events,
        build_selection_feature_rows,
        train_song_selector_params,
        evaluate_selection_quality,
        ArtifactPaths,
        write_song_selector_params,
        write_training_report,
        write_evaluation_report,
        write_baseline_metrics_snapshot,
        load_baseline_metrics_snapshot,
    ) = _imports()

    event_list = _as_event_list(events)

    if config.require_nonempty_events and not event_list:
        msg = "No feedback events provided"
        if config.strict:
            raise ValueError(msg)
        return {
            "status": "NO_DATA",
            "message": msg,
        }

    root = Path(artifact_root_dir) / config.artifacts_subdir
    paths = ArtifactPaths(root_dir=root)

    # 1) Aggregate
    agg_out = _as_dict(aggregate_song_feedback_events(event_list))
    agg_rows = agg_out.get("rows") if isinstance(agg_out.get("rows"), list) else []
    agg_summary = _as_dict(agg_out.get("summary"))

    # 2) Features
    feat_out = _as_dict(build_selection_feature_rows(agg_rows))
    feat_rows = feat_out.get("rows") if isinstance(feat_out.get("rows"), list) else []
    feat_summary = _as_dict(feat_out.get("summary"))
    feature_schema_version = feat_out.get("feature_schema_version")

    # 3) Train (calibrate static selector params)
    # Pass wrapper so training layer can see feature_schema_version if supported.
    train_input = feat_out if feat_out else feat_rows
    train_out = _as_dict(train_song_selector_params(train_input))
    params = _as_dict(train_out.get("params"))
    train_report = _as_dict(train_out.get("report"))

    # 4) Evaluate (compare to baseline snapshot if enabled and present)
    baseline_metrics = None
    if config.compare_to_baseline:
        loaded = load_baseline_metrics_snapshot(paths=paths)
        baseline_metrics = loaded if isinstance(loaded, dict) and loaded else None

    eval_out = _as_dict(evaluate_selection_quality(feat_rows, baseline_metrics=baseline_metrics))
    eval_report = _as_dict(eval_out.get("report"))
    guard_pass = bool(eval_report.get("guard_pass", True))

    # 5) Write artifacts (deployment-only)
    params_path = write_song_selector_params(params, paths=paths)

    training_payload = {
        "aggregation": agg_summary,
        "features": {
            **feat_summary,
            "feature_schema_version": feature_schema_version,
        },
        "training": train_report,
    }
    train_report_path = write_training_report(training_payload, paths=paths)

    eval_report_path = write_evaluation_report(eval_report, paths=paths)

    # Optional: update baseline snapshot only when guards pass
    baseline_path = None
    if config.update_baseline_snapshot and guard_pass:
        baseline_path = write_baseline_metrics_snapshot(
            _as_dict(eval_report.get("metrics")),
            paths=paths,
        )

    result = {
        "status": "OK" if guard_pass else "GUARD_FAIL",
        "artifact_dir": str(root),
        "paths": {
            "selector_params": str(params_path),
            "training_report": str(train_report_path),
            "evaluation_report": str(eval_report_path),
            "baseline_metrics": str(baseline_path) if baseline_path is not None else None,
        },
        "summary": {
            "aggregation": agg_summary,
            "features": {
                **feat_summary,
                "feature_schema_version": feature_schema_version,
            },
            "training": {
                "used_defaults": train_report.get("used_defaults"),
                "learned_fields": train_report.get("learned_fields"),
                "metrics": train_report.get("metrics"),
                "feature_schema_version": train_report.get("feature_schema_version"),
                "training_schema_version": train_report.get("training_schema_version"),
            },
            "evaluation": {
                "guard_pass": eval_report.get("guard_pass"),
                "guard_fail_reasons": eval_report.get("guard_fail_reasons"),
                "metrics": eval_report.get("metrics"),
                "deltas": eval_report.get("deltas"),
            },
        },
    }

    if config.strict and not guard_pass:
        raise RuntimeError(
            f"Evaluation regression guard failed: {eval_report.get('guard_fail_reasons')}"
        )

    return result


__all__ = [
    "OrchestratorConfig",
    "load_feedback_events",
    "run_song_rec_learning_pipeline",
]