from __future__ import annotations

"""
rhythm_ingestion.pipeline.tips

Public exports for the Phase 3 tips pipeline wiring layer.

This package is expected to contain (Phase 3):
- element_inference.py  : Stage 4.2–4.3
- severity_engine.py    : Stage 5.1
- tips_generator.py     : Stage 5.2–7

Design goals:
- Keep imports lightweight
- Avoid importing heavy modules at import time
- Provide a stable import surface for orchestrator.py and related callers
"""

from typing import Any, Dict, List


def _group_rows_by_game(rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows or []:
        row = row or {}
        game_id = str(row.get("game_id") or "unknown")
        grouped.setdefault(game_id, []).append(row)
    return grouped


def build_batch_summary(rows: List[Dict[str, Any]], tips_mode: str = "default", **kwargs: Any) -> Dict[str, Any]:
    """
    Compatibility shim for orchestrator wiring.

    If tips_generator.build_batch_summary exists, delegate to it.
    Otherwise, return a lightweight batch summary shape based on the rows
    already produced by the orchestration layer.

    NOTE:
    This fallback structure is a practical compatibility patch suggestion.
    It is not explicitly defined by the source snippets you shared.
    """
    try:
        from .tips_generator import build_batch_summary as _impl
        return _impl(rows, tips_mode=tips_mode, **kwargs)
    except Exception:
        grouped = _group_rows_by_game(rows)
        return {
            "tips_mode": tips_mode,
            "total_rows": len(rows or []),
            "games": {gid: {"rows": len(items)} for gid, items in grouped.items()},
        }


def build_chart_summary(*args: Any, **kwargs: Any) -> Any:
    from .tips_generator import build_chart_summary as _impl
    return _impl(*args, **kwargs)


def run_for_chart(*args: Any, **kwargs: Any) -> Any:
    from .tips_generator import run_for_chart as _impl
    return _impl(*args, **kwargs)


def run_track_a_proseka(*args: Any, **kwargs: Any) -> Any:
    from .severity_engine import run_track_a_proseka as _impl
    return _impl(*args, **kwargs)


def build_elements_skeleton(*args: Any, **kwargs: Any) -> Any:
    from .severity_engine import build_elements_skeleton as _impl
    return _impl(*args, **kwargs)


def merge_candidate_metadata(*args: Any, **kwargs: Any) -> Any:
    from .severity_engine import merge_candidate_metadata as _impl
    return _impl(*args, **kwargs)


def infer_element_candidates(*args: Any, **kwargs: Any) -> Any:
    from .element_inference import infer_element_candidates as _impl
    return _impl(*args, **kwargs)


def attach_candidates_to_payload(*args: Any, **kwargs: Any) -> Any:
    from .element_inference import attach_candidates_to_payload as _impl
    return _impl(*args, **kwargs)


def load_tips_training_mapping(*args: Any, **kwargs: Any) -> Any:
    from .element_inference import load_tips_training_mapping as _impl
    return _impl(*args, **kwargs)


__all__ = [
    "build_batch_summary",
    "build_chart_summary",
    "run_for_chart",
    "run_track_a_proseka",
    "build_elements_skeleton",
    "merge_candidate_metadata",
    "infer_element_candidates",
    "attach_candidates_to_payload",
    "load_tips_training_mapping",
]