"""
engine.feedback.interpreter

Feedback interpretation layer.

Purpose:
- Convert runtime signals into structured reason codes
- Align outputs with reason_taxonomy_v1

Key API:
- interpret_feedback

Design Constraints:
- Pure function (no side effects)
- Deterministic
- No I/O
- No model updates
"""

from .feedback_interpreter import (
    interpret_feedback,
    attach_feedback_reason,
)

__all__ = [
    "interpret_feedback",
    "attach_feedback_reason",
]