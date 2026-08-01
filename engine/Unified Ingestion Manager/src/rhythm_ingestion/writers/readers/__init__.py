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

from .chart_pattern_reader import get_chart_pattern
from .song_info_reader import SongInfoReader
from .chart_asset_reader import ChartAssetReader

__all__ = [
    "get_chart_pattern",
    "SongInfoReader",
    "ChartAssetReader",
]