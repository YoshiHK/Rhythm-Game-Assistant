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

from typing import Any


# ---------------------------------------------------------------------
# Lazy wrappers: only import concrete implementations at call time
# ---------------------------------------------------------------------

def build_batch_summary(*args: Any, **kwargs: Any) -> Any:
    """
    Lazy wrapper for the batch summary builder in tips_generator.
    """
    from .tips_generator import build_batch_summary as _impl
    return _impl(*args, **kwargs)


def build_chart_summary(*args: Any, **kwargs: Any) -> Any:
    """
    Lazy wrapper for the chart summary builder in tips_generator.
    """
    from .tips_generator import build_chart_summary as _impl
    return _impl(*args, **kwargs)


def run_for_chart(*args: Any, **kwargs: Any) -> Any:
    """
    Lazy wrapper for chart-level execution in tips_generator.
    """
    from .tips_generator import run_for_chart as _impl
    return _impl(*args, **kwargs)


def run_track_a_proseka(*args: Any, **kwargs: Any) -> Any:
    """
    Lazy wrapper for severity_engine Track A surface.
    """
    from .severity_engine import run_track_a_proseka as _impl
    return _impl(*args, **kwargs)


def build_elements_skeleton(*args: Any, **kwargs: Any) -> Any:
    """
    Lazy wrapper for elements skeleton construction.
    """
    from .severity_engine import build_elements_skeleton as _impl
    return _impl(*args, **kwargs)


def merge_candidate_metadata(*args: Any, **kwargs: Any) -> Any:
    """
    Lazy wrapper for candidate metadata merge.
    """
    from .severity_engine import merge_candidate_metadata as _impl
    return _impl(*args, **kwargs)


def infer_element_candidates(*args: Any, **kwargs: Any) -> Any:
    """
    Lazy wrapper for element candidate inference.
    """
    from .element_inference import infer_element_candidates as _impl
    return _impl(*args, **kwargs)


def attach_candidates_to_payload(*args: Any, **kwargs: Any) -> Any:
    """
    Lazy wrapper for candidate attachment.
    """
    from .element_inference import attach_candidates_to_payload as _impl
    return _impl(*args, **kwargs)


def load_tips_training_mapping(*args: Any, **kwargs: Any) -> Any:
    """
    Lazy wrapper for training mapping loader.
    """
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