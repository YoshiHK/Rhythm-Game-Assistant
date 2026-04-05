"""
rhythm_ingestion.pipeline.tips

Public exports for the Phase 3 tips pipeline wiring layer.

This package is expected to contain (Phase 3):
- element_inference.py  : Stage 4.2–4.3 (tag -> element candidates)
- severity_engine.py    : Stage 5.1 (Track A wrapper / elements_skeleton)
- tips_generator.py     : Stage 5.2–7 (Track B/C/D + summaries + batch)

Design goals:
- Keep imports lightweight (avoid importing heavy modules at import time)
- Provide a stable import surface for multi_ingest.py and orchestrator.py
"""

from __future__ import annotations

# Lightweight re-exports.
# Import errors are allowed to surface at call time rather than import time,
# which keeps package import fast and avoids circular imports during development.

# Stage 4.2–4.3
from .element_inference import (  # noqa: F401
    ElementCandidate,
    load_tips_training_mapping,
    infer_element_candidates,
    attach_candidates_to_payload,
)

# Stage 5.1 (Track A)
from .severity_engine import (  # noqa: F401
    run_track_a_proseka,
    merge_candidate_metadata,
    build_elements_skeleton,
)

# Stage 5.2–7 (Tracks B/C/D + summaries)
from .tips_generator import (  # noqa: F401
    run_for_chart,
    run_for_batch,
    build_chart_summary,
    build_batch_summary,
)

__all__ = [
    # element_inference
    "ElementCandidate",
    "load_tips_training_mapping",
    "infer_element_candidates",
    "attach_candidates_to_payload",
    # severity_engine
    "run_track_a_proseka",
    "merge_candidate_metadata",
    "build_elements_skeleton",
    # tips_generator
    "run_for_chart",
    "run_for_batch",
    "build_chart_summary",
    "build_batch_summary",
]
