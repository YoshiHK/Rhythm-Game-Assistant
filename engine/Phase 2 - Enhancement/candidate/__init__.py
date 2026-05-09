"""
Phase 2 Candidate Layer (Stage 4.2)

Responsibilities:
- Normalize detected pattern tags
- Resolve training-mapping artifacts
- Infer element candidates in a deterministic, additive way

Hard rules:
- No modification of Phase 1 logic
- No scoring, severity, or selection here
- Output must conform to Phase 2 interfaces and schemas
"""

from .tag_normalization import normalize_detected_tags
from .mapping_resolver import resolve_training_mapping
from .element_inference import infer_element_candidates

__all__ = [
    "normalize_detected_tags",
    "resolve_training_mapping",
    "infer_element_candidates",
]