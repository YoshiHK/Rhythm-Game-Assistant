"""
tips_meta_builder.py

Purpose:
- Build a pipeline-aware tips_meta artifact
- Align with song_db_meta (validation layer)
- Use canonical rows (Phase 3 output)
- Reflect real Phase 2 inference results

DO NOT modify Phase 1/2 logic
Only builds metadata (safe layer)
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Tuple


def _extract_game_id_and_row(item: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Accept either:
    1) orchestrator row shape:
       {"game_id": "...", "canonical_row": {...}}
    2) raw canonical row shape:
       {"game_id": "...", ...}
    """
    if not isinstance(item, dict):
        return "unknown", {}

    if isinstance(item.get("canonical_row"), dict):
        return str(item.get("game_id") or "unknown"), item["canonical_row"]

    return str(item.get("game_id") or "unknown"), item


def _is_missing(value: Any) -> bool:
    return value is None or value == ""


def build_tips_meta(
    *,
    rows: List[Dict[str, Any]],
    run_id: str,
    report_date: str,
    tips_mode: str = "production",
) -> Dict[str, Any]:
    """
    Build a full tips_meta artifact from canonical rows.

    rows:
        Output from orchestrator ingestion (preferred shape:
        {"game_id": ..., "canonical_row": {...}})
    """

    from rhythm_ingestion.pipeline.tips import build_batch_summary

    total = len(rows)

    # ------------------------------------------------------------
    # Phase 2 output (safe wrapper around existing inference summary)
    # ------------------------------------------------------------
    pipeline_output: Dict[str, Any]
    inference_failures = 0
    pipeline_output_error = None

    try:
        pipeline_output = build_batch_summary(rows, tips_mode=tips_mode)
    except Exception as e:
        pipeline_output = {}
        pipeline_output_error = str(e)
        inference_failures = total

    # ------------------------------------------------------------
    # Per-row analysis for metrics
    # ------------------------------------------------------------
    by_game_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"success": 0, "failed": 0})
    difficulty_counter: Counter[str] = Counter()

    rows_with_bpm = 0
    rows_with_duration_ms = 0
    rows_with_note_total_chart = 0

    missing_name = 0
    missing_difficulty = 0
    missing_chart_path = 0
    missing_bpm = 0
    missing_duration_ms = 0
    missing_note_total_chart = 0

    bpm_values: List[float] = []

    for item in rows:
        game_id, canonical = _extract_game_id_and_row(item)

        by_game_counts[game_id]["success"] += 1

        difficulty = canonical.get("difficulty_code") or canonical.get("difficulty_label") or "UNKNOWN"
        difficulty_counter[str(difficulty)] += 1

        if _is_missing(canonical.get("name")):
            missing_name += 1

        if _is_missing(canonical.get("difficulty_code")) and _is_missing(canonical.get("difficulty_label")):
            missing_difficulty += 1

        if _is_missing(canonical.get("chart_path")):
            missing_chart_path += 1

        bpm = canonical.get("bpm")
        if _is_missing(bpm):
            missing_bpm += 1
        else:
            rows_with_bpm += 1
            try:
                bpm_values.append(float(bpm))
            except Exception:
                pass

        duration_ms = canonical.get("duration_ms")
        if _is_missing(duration_ms):
            missing_duration_ms += 1
        else:
            rows_with_duration_ms += 1

        note_total_chart = canonical.get("note_total_chart")
        if _is_missing(note_total_chart):
            missing_note_total_chart += 1
        else:
            rows_with_note_total_chart += 1

    # ------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------
    success = total - inference_failures
    failed = inference_failures
    success_rate = (success / total) if total > 0 else 0.0

    summary = {
        "total_charts": total,
        "success": success,
        "failed": failed,
        "success_rate": success_rate,
    }

    # ------------------------------------------------------------
    # By-game
    # ------------------------------------------------------------
    by_game: Dict[str, Dict[str, Any]] = {}
    for gid, counts in by_game_counts.items():
        game_total = counts["success"] + counts["failed"]
        by_game[gid] = {
            "success": counts["success"],
            "failed": counts["failed"],
            "success_rate": (counts["success"] / game_total) if game_total > 0 else 0.0,
        }

    # ------------------------------------------------------------
    # Coverage
    # ------------------------------------------------------------
    charts_with_tips = success
    charts_missing_tips = total - charts_with_tips
    coverage = {
        "charts_with_tips": charts_with_tips,
        "charts_missing_tips": charts_missing_tips,
        "coverage_rate": (charts_with_tips / total) if total > 0 else 0.0,
    }

    # ------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------
    validation = {
        "inference_failures": inference_failures,
        "empty_pipeline_output": 1 if not pipeline_output else 0,
        "invalid_rows": 0,  # reserved for future row-shape validation
    }

    if pipeline_output_error is not None:
        validation["pipeline_output_error"] = pipeline_output_error

    # ------------------------------------------------------------
    # Pipeline metrics
    # ------------------------------------------------------------
    pipeline_metrics = {
        "tips_mode": tips_mode,
        "total_rows": total,
        "games_count": len(by_game),
    }

    # If build_batch_summary already emits equivalent fields, prefer the actual output
    if isinstance(pipeline_output, dict):
        if "tips_mode" in pipeline_output:
            pipeline_metrics["tips_mode"] = pipeline_output.get("tips_mode")
        if "total_rows" in pipeline_output:
            pipeline_metrics["total_rows"] = pipeline_output.get("total_rows")
        if "games" in pipeline_output and isinstance(pipeline_output["games"], dict):
            pipeline_metrics["games_count"] = len(pipeline_output["games"])

    # ------------------------------------------------------------
    # Difficulty metrics
    # ------------------------------------------------------------
    difficulty_metrics = {
        "by_difficulty": dict(difficulty_counter)
    }

    # ------------------------------------------------------------
    # Chart-level completeness metrics
    # ------------------------------------------------------------
    chart_metrics: Dict[str, Any] = {
        "rows_with_bpm": rows_with_bpm,
        "rows_with_duration_ms": rows_with_duration_ms,
        "rows_with_note_total_chart": rows_with_note_total_chart,
        "missing_name": missing_name,
        "missing_difficulty": missing_difficulty,
        "missing_chart_path": missing_chart_path,
        "missing_bpm": missing_bpm,
        "missing_duration_ms": missing_duration_ms,
        "missing_note_total_chart": missing_note_total_chart,
    }

    if bpm_values:
        chart_metrics["avg_bpm"] = sum(bpm_values) / len(bpm_values)
        chart_metrics["min_bpm"] = min(bpm_values)
        chart_metrics["max_bpm"] = max(bpm_values)

    # ------------------------------------------------------------
    # Final payload
    # ------------------------------------------------------------
    meta = {
        "report_type": "tips_meta",
        "run_id": run_id,
        "report_date": report_date,
        "generated_at": datetime.utcnow().isoformat(),

        "summary": summary,
        "by_game": by_game,
        "coverage": coverage,
        "validation": validation,

        "pipeline_metrics": pipeline_metrics,
        "difficulty_metrics": difficulty_metrics,
        "chart_metrics": chart_metrics,

        # Real Phase 2 output
        "pipeline_output": pipeline_output,

        "integrity": {
            "schema_version": 3,
            "source_layer": "phase2_from_phase3_rows"
        }
    }

    return meta