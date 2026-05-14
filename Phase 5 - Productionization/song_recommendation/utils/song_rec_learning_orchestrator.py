from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class OrchestratorConfig:
    """
    Offline orchestration config for the Phase 5 song recommendation learning loop.

    This orchestrator is NOT a runtime engine. It only runs offline dataflow. [1](https://onedrive.live.com/?id=1e428acc-4a68-416e-9d6d-c8692b153f2c&cid=d5d62a1ef303ba22&web=1)
    """
    # Input parsing
    allow_jsonl: bool = True  # if True, accept .jsonl (one JSON object per line)
    allow_json_array: bool = True  # if True, accept .json containing list[dict]

    # Baseline usage
    compare_to_baseline: bool = True
    update_baseline_snapshot: bool = False  # if True, overwrite baseline snapshot after a successful run

    # Artifact directory layout (passed to artifacts layer)
    artifacts_subdir: str = "song_recommendation"

    # If True, raise on pipeline failures; else return failure status
    strict: bool = True


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
        from phase5.song_recommendation.eval import evaluate_selection_quality
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
        # flat fallback (for notebooks / local runs)
        from aggregation import aggregate_song_feedback_events
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
# Input loaders (offline convenience)
# ---------------------------------------------------------------------

def load_feedback_events(path: str | Path, *, config: OrchestratorConfig = OrchestratorConfig()) -> List[Dict[str, Any]]:
    """
    Load Phase 6 forward-only song recommendation feedback events from disk.

    Supported formats:
    - JSONL: one JSON object per line
    - JSON: an array of objects

    This is Phase 5 offline I/O only. It MUST NOT be used by runtime. [2](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!sb2f7c783c4344d509f43af7f127b6c89)
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"feedback events file not found: {p}")

    text = p.read_text(encoding="utf-8").strip()
    if not text:
        return []

    # JSONL
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

    # JSON array
    if config.allow_json_array:
        obj = json.loads(text)
        if isinstance(obj, list):
            return [x for x in obj if isinstance(x, dict)]
        if isinstance(obj, dict):
            # accept {"events":[...]} convenience
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

    Returns a dict containing:
    - paths to written artifacts
    - training report summary
    - evaluation guard result

    This function is offline-only and deterministic given identical inputs. [2](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!sb2f7c783c4344d509f43af7f127b6c89)
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

    root = Path(artifact_root_dir) / config.artifacts_subdir
    paths = ArtifactPaths(root_dir=root)

    # 1) Aggregate
    agg_out = aggregate_song_feedback_events(list(events))
    agg_rows = agg_out.get("rows", [])
    agg_summary = agg_out.get("summary", {})

    # 2) Features
    feat_out = build_selection_feature_rows(agg_rows)
    feat_rows = feat_out.get("rows", [])
    feat_summary = feat_out.get("summary", {})

    # 3) Train (calibrate static selector params)
    train_out = train_song_selector_params(feat_rows)
    params = train_out.get("params", {})
    train_report = train_out.get("report", {})

    # 4) Evaluate (compare to baseline snapshot if enabled and present)
    baseline_metrics = None
    if config.compare_to_baseline:
        baseline_metrics = load_baseline_metrics_snapshot(paths=paths)

    eval_out = evaluate_selection_quality(feat_rows, baseline_metrics=baseline_metrics)
    eval_report = (eval_out.get("report") or {})
    guard_pass = bool(eval_report.get("guard_pass", True))

    # 5) Write artifacts (deployment-only)
    params_path = write_song_selector_params(params, paths=paths)
    train_report_path = write_training_report({"aggregation": agg_summary, "features": feat_summary, "training": train_report}, paths=paths)
    eval_report_path = write_evaluation_report(eval_report, paths=paths)

    # Optional: update baseline snapshot
    baseline_path = None
    if config.update_baseline_snapshot:
        # Only update baseline if guards pass (avoid baking regressions)
        if guard_pass:
            baseline_path = write_baseline_metrics_snapshot(eval_report.get("metrics", {}), paths=paths)
        else:
            baseline_path = None

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
            "features": feat_summary,
            "training": {
                "used_defaults": train_report.get("used_defaults"),
                "learned_fields": train_report.get("learned_fields"),
                "metrics": train_report.get("metrics"),
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
        raise RuntimeError(f"Evaluation regression guard failed: {eval_report.get('guard_fail_reasons')}")

    return result