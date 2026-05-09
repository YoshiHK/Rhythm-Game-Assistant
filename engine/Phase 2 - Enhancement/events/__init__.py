"""
Phase 2 Events Layer (Observational Only)

This package provides observational hooks for Phase 2 execution.

Hard rules:
- No mutation of payloads
- No control flow influence
- No dependency on Phase 1 internals
- Safe to disable entirely without changing behavior
"""

from .phase2_event_logger import log_phase2_event
from .diagnostics_collector import collect_diagnostics

__all__ = [
    "log_phase2_event",
    "collect_diagnostics",
]