"""
CI Test — Game Capability Fixtures Validity

Ensures fixture JSON files are valid and resolvable by game_capability_resolver.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest


def _imports():
    try:
        from phase6.song_recommendation.game_capability_resolver import resolve_game_capability
        return resolve_game_capability
    except Exception:
        from game_capability_resolver import resolve_game_capability
        return resolve_game_capability


def test_game_capability_fixtures_load_and_validate():
    resolve_game_capability = _imports()

    root = Path(__file__).parent / "fixtures" / "game_capability"
    proseka = json.loads((root / "proseka.json").read_text(encoding="utf-8"))
    arcaea = json.loads((root / "arcaea.json").read_text(encoding="utf-8"))

    cap_map = {
        proseka["game_id"]: proseka,
        arcaea["game_id"]: arcaea,
    }

    assert resolve_game_capability("proseka", capabilities=cap_map).game_id == "proseka"
    assert resolve_game_capability("arcaea", capabilities=cap_map).game_id == "arcaea"