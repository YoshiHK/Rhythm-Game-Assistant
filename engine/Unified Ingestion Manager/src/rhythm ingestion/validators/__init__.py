from __future__ import annotations

"""
rhythm_ingestion.validators package

v2 compatibility exports (additive, non-breaking).

Supported games (source of truth):
- The authoritative list of supported games is defined in games.json.
- Code in this package MUST NOT hardcode the supported game list for governance.
- Validators should set game_id to a value that matches an entry in games.json.

Goals:
- Provide a single, stable import surface for validators.
- Preserve legacy BaseValidator contract.
- Add v2 standardization helpers (BaseValidatorV2) without forcing migration.
- Provide get_validator(game_id) for orchestration-time lookup.
"""

from importlib import import_module
from typing import Any, Dict

from .base_validator import BaseValidator

try:
    from .base_validator_v2 import BaseValidatorV2, ValidatorIdentity
except Exception:  # pragma: no cover
    BaseValidatorV2 = None  # type: ignore
    ValidatorIdentity = None  # type: ignore

# ---------------------------------------------------------------------
# Canonical game_id -> module path
# ---------------------------------------------------------------------

_VALIDATOR_MODULES: Dict[str, str] = {
    "bandori": "rhythm_ingestion.validators.game_specific_validators.validator_bandori",
    "proseka": "rhythm_ingestion.validators.game_specific_validators.validator_proseka",
    "arcaea": "rhythm_ingestion.validators.game_specific_validators.validator_arcaea",
    "maimai": "rhythm_ingestion.validators.game_specific_validators.validator_maimai",
    "dynamix": "rhythm_ingestion.validators.game_specific_validators.validator_dynamix",
    "chunithm": "rhythm_ingestion.validators.game_specific_validators.validator_chunithm",
    "d4dj": "rhythm_ingestion.validators.game_specific_validators.validator_d4dj",
    "ユメステ": "rhythm_ingestion.validators.game_specific_validators.validator_ユメステ",
    "phigros": "rhythm_ingestion.validators.game_specific_validators.validator_phigros",
    "lanota": "rhythm_ingestion.validators.game_specific_validators.validator_lanota",
    "ongeki": "rhythm_ingestion.validators.game_specific_validators.validator_ongeki",
    "our_notes": "rhythm_ingestion.validators.game_specific_validators.validator_our_notes",
    "sound_voltex": "rhythm_ingestion.validators.game_specific_validators.validator_sound_voltex",
    "cytus_ii": "rhythm_ingestion.validators.game_specific_validators.validator_cytus_ii",
    "groove_coaster": "rhythm_ingestion.validators.game_specific_validators.validator_groove_coaster",
}

# ---------------------------------------------------------------------
# Canonical game_id -> likely validator class names
# ---------------------------------------------------------------------

_VALIDATOR_CLASS_CANDIDATES: Dict[str, list[str]] = {
    "bandori": ["BandoriValidator"],
    "proseka": ["ProsekaValidator"],
    "arcaea": ["ArcaeaValidator"],
    "maimai": ["MaimaiValidator"],
    "dynamix": ["DynamixValidator"],
    "chunithm": ["ChunithmValidator"],
    "d4dj": ["D4DJValidator"],
    "ユメステ": ["ユメステValidator"],
    "phigros": ["PhigrosValidator"],
    "lanota": ["LanotaValidator"],
    "ongeki": ["OngekiValidator"],
    "our_notes": ["OurNotesValidator"],
    "sound_voltex": ["SoundVoltexValidator"],
    "cytus_ii": ["CytusIiValidator", "CytusIIValidator"],
    "groove_coaster": ["GrooveCoasterValidator"],
}


def get_validator(game_id: str) -> Any:
    """
    Return an instantiated validator for the given canonical game_id.

    Raises:
        KeyError      : unsupported game_id
        ImportError   : validator module cannot be imported
        AttributeError: no known validator class found in the module
    """
    if game_id not in _VALIDATOR_MODULES:
        raise KeyError(f"Unsupported game_id for validator lookup: {game_id}")

    module_name = _VALIDATOR_MODULES[game_id]
    mod = import_module(module_name)

    for class_name in _VALIDATOR_CLASS_CANDIDATES.get(game_id, []):
        if hasattr(mod, class_name):
            cls = getattr(mod, class_name)
            return cls()

    raise AttributeError(
        f"No validator class found for game_id={game_id} in module={module_name}"
    )


__all__ = [
    "BaseValidator",
    "BaseValidatorV2",
    "ValidatorIdentity",
    "get_validator",
]