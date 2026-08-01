from __future__ import annotations

"""
rhythm_ingestion.validators package

v2 compatibility exports (additive, non-breaking).
"""

from importlib import import_module
from typing import Any, Dict

from .base_validator import BaseValidator

try:
    from .base_validator_v2 import BaseValidatorV2, ValidatorIdentity
except Exception:  # pragma: no cover
    BaseValidatorV2 = None  # type: ignore
    ValidatorIdentity = None  # type: ignore

try:
    from .common_validator_utils import (
        safe_int,
        safe_float,
        build_validation_ok,
        build_validation_fail,
        compute_delta,
        is_within_threshold,
        values_equal,
        numeric_equal,
        compute_phase4_gate_state,
    )
except Exception:  # pragma: no cover
    pass

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
    "yumesute": "rhythm_ingestion.validators.game_specific_validators.validator_yumesute",
    "phigros": "rhythm_ingestion.validators.game_specific_validators.validator_phigros",
    "lanota": "rhythm_ingestion.validators.game_specific_validators.validator_lanota",
    "ongeki": "rhythm_ingestion.validators.game_specific_validators.validator_ongeki",
    "our_notes": "rhythm_ingestion.validators.game_specific_validators.validator_our_notes",
    "sound_voltex": "rhythm_ingestion.validators.game_specific_validators.validator_sound_voltex",
    "cytus_ii": "rhythm_ingestion.validators.game_specific_validators.validator_cytus_ii",
    "groove_coaster": "rhythm_ingestion.validators.game_specific_validators.validator_groove_coaster",
}


_VALIDATOR_CLASS_CANDIDATES: Dict[str, list[str]] = {
    "bandori": ["BandoriValidator"],
    "proseka": ["ProsekaValidator"],
    "arcaea": ["ArcaeaValidator"],
    "maimai": ["MaimaiValidator"],
    "dynamix": ["DynamixValidator"],
    "chunithm": ["ChunithmValidator"],
    "d4dj": ["D4DJValidator"],
    "yumesute": ["YumesuteValidator"],
    "phigros": ["PhigrosValidator"],
    "lanota": ["LanotaValidator"],
    "ongeki": ["OngekiValidator"],
    "our_notes": ["OurNotesValidator"],
    "sound_voltex": ["SoundVoltexValidator"],
    "cytus_ii": ["CytusIiValidator", "CytusIIValidator"],
    "groove_coaster": ["GrooveCoasterValidator"],
}

def _resolve_validator_class(game_id: str):
    module_name = _VALIDATOR_MODULES[game_id]
    mod = import_module(module_name)

    for class_name in _VALIDATOR_CLASS_CANDIDATES.get(game_id, []):
        if hasattr(mod, class_name):
            return getattr(mod, class_name)

    raise AttributeError(
        f"No validator class found for game_id={game_id} in module={module_name}"
    )

def get_validator(game_id: str) -> Any:
    """
    Return an instantiated validator for the given canonical game_id.
    """
    if game_id not in _VALIDATOR_MODULES:
        raise KeyError(f"Unsupported game_id for validator lookup: {game_id}")

    cls = _resolve_validator_class(game_id)
    return cls()

__all__ = [
    "BaseValidator",
    "BaseValidatorV2",
    "ValidatorIdentity",
    "get_validator",
    "safe_int",
    "safe_float",
    "build_validation_ok",
    "build_validation_fail",
    "compute_delta",
    "is_within_threshold",
    "values_equal",
    "numeric_equal",
    "compute_phase4_gate_state",
]