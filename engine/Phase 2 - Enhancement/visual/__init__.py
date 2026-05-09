"""
Phase 2 Visual Layer (Stage 2–4.1)

Wiring-only wrappers for:
- Visual detection
- SectionMetrics extraction
- Pattern-signal tag extraction

Hard rules:
- Deterministic
- No mutation of Phase 1 artifacts (additive only)
- No orchestration responsibilities (Phase 2 runtime / Phase 3 orchestrator owns flow)
"""

from .visual_detector import attach_visual_outputs, run_visual_detection
from .section_metrics_builder import extract_sections
from .pattern_signal_extractor import extract_detected_tags

__all__ = [
    "run_visual_detection",
    "attach_visual_outputs",
    "extract_sections",
    "extract_detected_tags",
]