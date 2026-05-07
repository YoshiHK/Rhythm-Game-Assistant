"""
Phase 4 — Events Layer (observational only).

This package contains helpers for building:
- Phase 4 event log records
- Phase 4 feedback capture records

Hard rules:
- No persistence
- No PII (player identifiers must be hashed upstream)
- No raw canonical payload stored
- Must NOT affect runtime personalization behavior
"""

from .event_logger import (
    PHASE4_EVENT_TYPES,
    build_phase4_event_log_entry,
    build_phase4_feedback_event,
)

from .feedback_capture import (
    build_phase4_feedback_capture_record,
)

__all__ = [
    # event logging
    "PHASE4_EVENT_TYPES",
    "build_phase4_event_log_entry",
    "build_phase4_feedback_event",
    # feedback capture
    "build_phase4_feedback_capture_record",
]