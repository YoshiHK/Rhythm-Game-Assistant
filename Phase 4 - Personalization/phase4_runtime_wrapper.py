
#!/usr/bin/env python3
"""phase4_runtime_wrapper.py

Phase 4 Shim Wrapper

Goal:
- Provide a single import surface for the app runtime.
- Re-export Phase 4 runtime shim entrypoint and event builders.

This wrapper does NOT change any Phase 1–3 behavior.
It only aggregates Phase 4 modules:
- phase4_personalization_runtime.py
- phase4_event_builders.py

Recommended usage:
    from phase4_runtime_wrapper import (
        run_phase4_personalization,
        build_phase4_event_log_entry,
        build_phase4_feedback_event,
        build_phase4_provenance,
        Phase4RuntimeConfig,
    )

"""

from __future__ import annotations

# Runtime shim
from phase4_personalization_runtime import (  # noqa: F401
    Phase4RuntimeConfig,
    build_phase4_provenance,
    build_phase4_event_log_entry,
    run_phase4_personalization,
)

# Event builders (includes feedback helper)
from phase4_event_builders import (  # noqa: F401
    build_phase4_feedback_event,
)

__all__ = [
    "Phase4RuntimeConfig",
    "build_phase4_provenance",
    "build_phase4_event_log_entry",
    "build_phase4_feedback_event",
    "run_phase4_personalization",
]
