"""
writers.readers

Data access / retrieval layer.

Responsibilities
----------------
- Retrieve chart pattern data from DB
- Provide stable read interface to bridges and orchestrators
- Remain read-only (no mutation, no write logic)

Design rules
------------
- No business logic
- No normalization
- No conversion
- No persistence
"""

# --------------------------------------------------
# Core pattern reader (Phase 1–3 integration)
# --------------------------------------------------

from .chart_pattern_reader import (
    get_chart_pattern,
)

# --------------------------------------------------
# Optional: future expansion placeholders
# (DO NOT remove - helps prevent circular imports later)
# --------------------------------------------------

# Example future APIs:
# from .chart_asset_reader import get_chart_asset
# from .song_info_reader import get_song_info


__all__ = [
    "get_chart_pattern",
]