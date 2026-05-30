from __future__ import annotations

"""
rhythm_ingestion.adapters package

v2 compatibility exports (additive, non-breaking).

Supported games (source of truth):
- The authoritative list of supported games is defined in games.json.
- Code in this package MUST NOT hardcode the supported game list for governance.
- Adapters should set game_id to a value that matches an entry in games.json.

Goals:
- Provide a single, stable import surface for adapters.
- Preserve legacy BaseAdapter contract.
- Add v2 standardization helpers (BaseAdapterV2) without forcing migration.
- Provide get_adapter(game_id) for orchestration-time lookup.
"""

from importlib import import_module
from typing import Any, Dict

from .base_adapter import BaseAdapter

try:
    from .base_adapter_v2 import BaseAdapterV2, AdapterIdentity
except Exception:  # pragma: no cover
    BaseAdapterV2 = None  # type: ignore
    AdapterIdentity = None  # type: ignore

from .common_adapter_utils import (
    build_internal_metadata,
    canonical_sections_version,
    build_standard_diagnostics,
    attach_if_missing,
)

# ---------------------------------------------------------------------
# Canonical game_id -> module path
# ---------------------------------------------------------------------

_ADAPTER_MODULES: Dict[str, str] = {
    "bandori": "rhythm_ingestion.adapters.game_specific_adapters.adapter_bandori",
    "proseka": "rhythm_ingestion.adapters.game_specific_adapters.adapter_proseka",
    "arcaea": "rhythm_ingestion.adapters.game_specific_adapters.adapter_arcaea",
    "maimai": "rhythm_ingestion.adapters.game_specific_adapters.adapter_maimai",
    "dynamix": "rhythm_ingestion.adapters.game_specific_adapters.adapter_dynamix",
    "chunithm": "rhythm_ingestion.adapters.game_specific_adapters.adapter_chunithm",
    "d4dj": "rhythm_ingestion.adapters.game_specific_adapters.adapter_D4DJ",
    "ユメステ": "rhythm_ingestion.adapters.game_specific_adapters.adapter_ユメステ",
    "phigros": "rhythm_ingestion.adapters.game_specific_adapters.adapter_phigros",
    "lanota": "rhythm_ingestion.adapters.game_specific_adapters.adapter_lanota",
    "ongeki": "rhythm_ingestion.adapters.game_specific_adapters.adapter_ongeki",
    "our_notes": "rhythm_ingestion.adapters.game_specific_adapters.adapter_our_notes",
    "sound_voltex": "rhythm_ingestion.adapters.game_specific_adapters.adapter_sound_voltex",
    "cytus_ii": "rhythm_ingestion.adapters.game_specific_adapters.adapter_cytus_ii",
    "groove_coaster": "rhythm_ingestion.adapters.game_specific_adapters.adapter_groove_coaster",
}

# ---------------------------------------------------------------------
# Canonical game_id -> likely adapter class names
# ---------------------------------------------------------------------

_ADAPTER_CLASS_CANDIDATES: Dict[str, list[str]] = {
    "bandori": ["BandoriAdapter"],
    "proseka": ["ProsekaAdapter"],
    "arcaea": ["ArcaeaAdapter"],
    "maimai": ["MaimaiAdapter"],
    "dynamix": ["DynamixAdapter"],
    "chunithm": ["ChunithmAdapter"],
    "d4dj": ["D4DJAdapter"],
    "ユメステ": ["ユメステAdapter"],
    "phigros": ["PhigrosAdapter"],
    "lanota": ["LanotaAdapter"],
    "ongeki": ["OngekiAdapterAugmented", "OngekiAdapter"],
    "our_notes": ["OurNotesAdapter"],
    "sound_voltex": ["SoundVoltexAdapter"],
    "cytus_ii": ["CytusIiAdapter", "CytusIIAdapter"],
    "groove_coaster": ["GrooveCoasterAdapter"],
}


def get_adapter(game_id: str) -> Any:
    """
    Return an instantiated adapter for the given canonical game_id.

    Raises:
        KeyError      : unsupported game_id
        ImportError   : adapter module cannot be imported
        AttributeError: no known adapter class found in the module
    """
    if game_id not in _ADAPTER_MODULES:
        raise KeyError(f"Unsupported game_id for adapter lookup: {game_id}")

    module_name = _ADAPTER_MODULES[game_id]
    mod = import_module(module_name)

    for class_name in _ADAPTER_CLASS_CANDIDATES.get(game_id, []):
        if hasattr(mod, class_name):
            cls = getattr(mod, class_name)
            return cls()

    raise AttributeError(
        f"No adapter class found for game_id={game_id} in module={module_name}"
    )


__all__ = [
    "BaseAdapter",
    "BaseAdapterV2",
    "AdapterIdentity",
    "build_internal_metadata",
    "canonical_sections_version",
    "build_standard_diagnostics",
    "attach_if_missing",
    "get_adapter",
]