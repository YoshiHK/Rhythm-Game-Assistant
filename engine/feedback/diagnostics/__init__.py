"""
engine.feedback.diagnostics

Runtime debugging and trace utilities for feedback system.

Purpose:
- Help developers understand feedback interpretation results
- Provide traceability across the feedback pipeline
- Compare machine reasoning vs curator ground truth

Modules:
- reason_debugger:
    Reason-level inspection and comparison

- trace_utils:
    End-to-end feedback lineage tracing

Constraints:
- No mutation of data
- No I/O side effects
- Debugging only (not part of production decision flow)
"""

from .reason_debugger import (
    explain_reason,
    compare_model_vs_curator,
    debug_payload_reason,
)

from .trace_utils import (
    build_feedback_trace,
    trace_reason_path,
)

__all__ = [
    # Reason debugging
    "explain_reason",
    "compare_model_vs_curator",
    "debug_payload_reason",

    # Tracing
    "build_feedback_trace",
    "trace_reason_path",
]