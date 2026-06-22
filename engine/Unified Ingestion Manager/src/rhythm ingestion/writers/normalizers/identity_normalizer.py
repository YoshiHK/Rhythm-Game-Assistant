from __future__ import annotations

"""
identity_normalizer.py

Canonical identity normalization layer.

Responsibilities
----------------
- Normalize game / difficulty / level from folder hierarchy
- Validate compatibility between canonical game and canonical difficulty
- Surface issues non-destructively (do NOT invent semantics)
- Remain pure, deterministic, and side-effect free

Scope
-----
This module is for folder / hierarchy normalization only.
Filename parsing belongs to file_scan_scenarios.py.
Song semantic matching belongs to song_identity_resolver.py.
"""

import re
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------
# Canonical game → supported difficulty tiers
# (PRODUCTION-COMPLETE VERSION)
# ---------------------------------------------------------------------

GAME_DIFFICULTY_CAPABILITIES: Dict[str, List[str]] = {
    "bandori": ["easy", "normal", "hard", "expert", "special"],
    "proseka": ["easy", "normal", "hard", "expert", "master", "append"],   
    "chunithm": ["basic", "advanced", "expert", "master", "ultima"],    
    "ongeki": ["basic", "advanced", "expert", "master", "lunatic"],
    "yumesute": ["normal", "hard", "extra", "stella", "olivier"],
    "arcaea": ["past", "present", "future", "beyond"],
    "maimai": ["basic", "advanced", "expert", "master", "remaster"],
    "dynamix": ["casual", "normal", "hard", "mega"],
    "d4dj": ["easy", "normal", "hard", "expert"],
    "phigros": ["easy", "hard", "insane", "another"],
    "lanota": ["whisper", "acoustic", "ultra", "master"],
    "sound_voltex": ["novice", "advanced", "exhaust", "infinite"],
    "groove_coaster": ["simple", "normal", "hard", "extra"],
    "cytus": ["easy", "hard", "chaos", "glitch"],
    "cytus_ii": ["easy", "hard", "chaos", "glitch"],
    "deemo": ["easy", "normal", "hard"],
    "voez": ["easy", "hard", "expert"],
    "muse_dash": ["easy", "hard", "master"],
    "taiko": ["easy", "normal", "hard", "expert", "master"],
    "osu": ["easy", "normal", "hard", "expert"],
    "ensemble_stars": ["easy", "normal", "hard", "expert"],
    "idolmaster": ["easy", "normal", "hard", "expert"],
    "kalpa": ["easy", "normal", "hard", "expert"],
    "our_notes": ["easy", "normal", "hard"],

}
# ---------------------------------------------------------------------
# Game aliases (PRODUCTION-COMPLETE VERSION)
# ---------------------------------------------------------------------

GAME_ALIASES: Dict[str, str] = {

    # --------------------------------------------------
    # Project Sekai / Proseka
    # --------------------------------------------------
    "project sekai": "proseka",
    "project sekai colorful stage": "proseka",
    "proseka": "proseka",
    "proseka": "project_sekai",
    "pjsekai": "proseka",
    "pj sekai": "proseka",
    "colorful stage": "proseka",

    # --------------------------------------------------
    # BanG Dream / Bandori
    # --------------------------------------------------
    "bang dream": "bandori",
    "bangdream": "bandori",
    "ban g dream": "bandori",
    "bandori": "bandori",
    "garupa": "bandori",

    # --------------------------------------------------
    # World Dai Star / Yumesute
    # --------------------------------------------------
    "world dai star": "yumesute",
    "worlddaistar": "yumesute",
    "yumesute": "yumesute",
    "ユメステ": "yumesute",
    "wds": "yumesute",

    # --------------------------------------------------
    # CHUNITHM
    # --------------------------------------------------
    "chunithm": "chunithm",

    # --------------------------------------------------
    # Ongeki
    # --------------------------------------------------
    "ongeki": "ongeki",

    # --------------------------------------------------
    # maimai
    # --------------------------------------------------
    "maimai": "maimai",

    # --------------------------------------------------
    # Arcaea (fix typo too)
    # --------------------------------------------------
    "arcaea": "arcaea",
    "arceaea": "arcaea",

    # --------------------------------------------------
    # Cytus (series)
    # --------------------------------------------------
    "cytus": "cytus",
    "cytus ii": "cytus_ii",
    "cytus2": "cytus_ii",
    "cytus (series)": "cytus",

    # --------------------------------------------------
    # Deemo (series)
    # --------------------------------------------------
    "deemo": "deemo",
    "deemo (series)": "deemo",

    # --------------------------------------------------
    # Dynamix
    # --------------------------------------------------
    "dynamix": "dynamix",

    # --------------------------------------------------
    # D4DJ
    # --------------------------------------------------
    "d4dj": "d4dj",

    # --------------------------------------------------
    # Ensemble Stars
    # --------------------------------------------------
    "ensemble stars": "ensemble_stars",
    "ensemble star": "ensemble_stars",
    "enstars": "ensemble_stars",

    # --------------------------------------------------
    # Groove Coaster
    # --------------------------------------------------
    "groove coaster": "groove_coaster",
    "groove_coaster": "groove_coaster",

    # --------------------------------------------------
    # Idolmaster (series)
    # --------------------------------------------------
    "idolmaster": "idolmaster",
    "idolmaster (series)": "idolmaster",
    "im@s": "idolmaster",

    # --------------------------------------------------
    # KALPA
    # --------------------------------------------------
    "kalpa": "kalpa",

    # --------------------------------------------------
    # Lanota
    # --------------------------------------------------
    "lanota": "lanota",

    # --------------------------------------------------
    # Muse Dash
    # --------------------------------------------------
    "muse dash": "muse_dash",
    "musedash": "muse_dash",

    # --------------------------------------------------
    # osu!
    # --------------------------------------------------
    "osu": "osu",
    "osu!": "osu",

    # --------------------------------------------------
    # Our Notes
    # --------------------------------------------------
    "our notes": "our_notes",
    "ournotes": "our_notes",

    # --------------------------------------------------
    # Phigros
    # --------------------------------------------------
    "phigros": "phigros",

    # --------------------------------------------------
    # Sound Voltex
    # --------------------------------------------------
    "sound voltex": "sound_voltex",
    "sound_voltex": "sound_voltex",
    "sdvx": "sound_voltex",

    # --------------------------------------------------
    # Taiko no Tatsujin
    # --------------------------------------------------
    "taiko no tatsujin": "taiko",
    "taiko": "taiko",

    # --------------------------------------------------
    # VOEZ
    # --------------------------------------------------
    "voez": "voez",
}



# ---------------------------------------------------------------------
# Difficulty aliases (PRODUCTION-COMPLETE VERSION)
# ---------------------------------------------------------------------

DIFFICULTY_ALIASES: Dict[str, str] = {

    # --------------------------------------------------
    # Generic (global)
    # --------------------------------------------------
    "easy": "easy",
    "ez": "easy",

    "normal": "normal",
    "nm": "normal",

    "hard": "hard",

    "expert": "expert",
    "ex": "expert",
    "exp": "expert",

    "master": "master",
    "mas": "master",

    # --------------------------------------------------
    # Project Sekai
    # --------------------------------------------------
    "append": "append",
    "app": "append",

    # --------------------------------------------------
    # BanG Dream
    # --------------------------------------------------
    "special": "special",
    "sp": "special",

    # --------------------------------------------------
    # CHUNITHM
    # --------------------------------------------------
    "basic": "basic",
    "advance": "advanced",
    "advanced": "advanced",
    "adv": "advanced",
    "master": "master",
    "ultima": "ultima",
    "ult": "ultima",

    # --------------------------------------------------
    # maimai
    # --------------------------------------------------
    "basic": "basic",
    "advanced": "advanced",
    "expert": "expert",
    "master": "master",

    "remaster": "remaster",
    "re:master": "remaster",
    "re master": "remaster",

    # --------------------------------------------------
    # Arcaea
    # --------------------------------------------------
    "past": "past",
    "present": "present",
    "future": "future",
    "beyond": "beyond",

    # --------------------------------------------------
    # Phigros (convert to human-readable)
    # --------------------------------------------------
    "hd": "hard",
    "in": "insane",
    "at": "another",

    # --------------------------------------------------
    # Dynamix
    # --------------------------------------------------
    "casual": "casual",
    "normal": "normal",
    "hard": "hard",
    "mega": "mega",

    # --------------------------------------------------
    # Lanota
    # --------------------------------------------------
    "whisper": "whisper",
    "acoustic": "acoustic",
    "ultra": "ultra",
    "master": "master",

    # --------------------------------------------------
    # ONGEKI
    # --------------------------------------------------
    "basic": "basic",
    "advanced": "advanced",
    "expert": "expert",
    "master": "master",
    "lunatic": "lunatic",

    # --------------------------------------------------
    # Sound Voltex
    # --------------------------------------------------
    "novice": "novice",
    "nov": "novice",

    "advanced": "advanced",
    "adv": "advanced",

    "exhaust": "exhaust",
    "exh": "exhaust",

    "infinite": "infinite",
    "inf": "infinite",

    # --------------------------------------------------
    # Cytus / Cytus II
    # --------------------------------------------------
    "easy": "easy",
    "hard": "hard",
    "chaos": "chaos",
    "glitch": "glitch",

    # --------------------------------------------------
    # Groove Coaster
    # --------------------------------------------------
    "simple": "simple",
    "normal": "normal",
    "hard": "hard",
    "extra": "extra",

    # --------------------------------------------------
    # Taiko no Tatsujin
    # --------------------------------------------------
    "kantan": "easy",
    "futsuu": "normal",
    "muzukashii": "hard",
    "oni": "expert",
    "ura": "master",

    # --------------------------------------------------
    # Muse Dash
    # --------------------------------------------------
    "easy": "easy",
    "hard": "hard",
    "master": "master",

    # --------------------------------------------------
    # Deemo / VOEZ / general Rayark
    # --------------------------------------------------
    "easy": "easy",
    "normal": "normal",
    "hard": "hard",

    # --------------------------------------------------
    # Yumesute (World Dai Star)
    # --------------------------------------------------
    "normal": "normal",
    "hard": "hard",
    "extra": "extra",
    "stella": "stella",
    "olivier": "olivier",
}



# ---------------------------------------------------------------------
# Level normalization
# ---------------------------------------------------------------------

ROMAN_MAP: Dict[str, int] = {
    "i": 1,
    "ii": 2,
    "iii": 3,
    "iv": 4,
    "v": 5,
    "vi": 6,
    "vii": 7,
    "viii": 8,
    "ix": 9,
    "x": 10,
    "xi": 11,
    "xii": 12,
    "xiii": 13,
    "xiv": 14,
    "xv": 15,
    "xvi": 16,
    "xvii": 17,
    "xviii": 18,
    "xix": 19,
    "xx": 20,
}

ROMAN_SUFFIX_PATTERN = r"\b(i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii|xiii|xiv|xv)\b"

# ---------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------

def _norm_str(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _norm_token(value: Any) -> str:
    """
    Canonical token normalization for folder-derived identity strings.

    Goals:
    - lowercase
    - collapse spaces
    - normalize punctuation / separators
    - remove obvious container punctuation ((), [], !, :, etc.)
    - keep content semantic, not presentation-driven
    """
    s = _norm_str(value).casefold()

    # Normalize common separators / punctuation
    s = s.replace("_", " ")
    s = s.replace("-", " ")
    s = s.replace("　", " ")   # full-width space
    s = s.replace("!", "")
    s = s.replace(":", " ")
    s = s.replace("/", " ")
    s = s.replace("\\", " ")

    # Remove bracket wrappers but keep inner content
    s = re.sub(r"[\(\)\[\]\{\}]", " ", s)

    # Collapse whitespace
    s = re.sub(r"\s+", " ", s)

    return s.strip()


def _canonicalize_game_token(token: str) -> str:
    """
    Final canonical form for game token if it is not directly aliased.
    """
    return token.replace(" ", "_")


def normalize_game(value: Optional[str]) -> Optional[str]:
    """
    Normalize a game folder into canonical game_id.

    Behavior:
    - first use GAME_ALIASES
    - then allow exact capability keys
    - otherwise return normalized snake_case token
      (caller should decide whether that token is supported)
    """
    if not value:
        return None

    token = _norm_token(value)

    if token in GAME_ALIASES:
        return GAME_ALIASES[token]

    canonical = token.replace(" ", "_")

    if canonical in GAME_DIFFICULTY_CAPABILITIES:
        return canonical

    return None

def normalize_difficulty(value: Optional[str]) -> Optional[str]:
    """
    Normalize difficulty folder labels.

    Handles:
    - [MASTER]
    - Ultima Lv 16
    - MASTER 32
    - Expert IV
    - Re:MASTER
    - level suffixes / roman suffixes
    """
    if not value:
        return None

    token = _norm_token(value)

    # Remove full-wrapper brackets again defensively
    token = re.sub(r"^\s*[\[\(\{]\s*(.+?)\s*[\]\)\}]\s*$", r"\1", token).strip()

    # Remove obvious level suffixes:
    #   "master lv 16" -> "master"
    #   "expert 32"    -> "expert"
    #   "expert iv"    -> "expert"
    token = re.sub(r"\b(lv|level)\s*\d+(\+)?(\.\d+)?\b.*$", "", token).strip()
    token = re.sub(r"\b\d+(\+)?(\.\d+)?\b$", "", token).strip()
    token = re.sub(r"\b(i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii|xiii|xiv|xv)\b$", "", token).strip()

    # Final alias lookup
    return DIFFICULTY_ALIASES.get(token, token or None)


def normalize_level(value: Optional[str]) -> Optional[int]:
    """
    Normalize level folder labels to integer level.

    Notes:
    - keeps Phase-safe integer behavior
    - for forms like "12+" / "12.7", extracts the leading integer
    """
    if not value:
        return None

    s = _norm_token(value)

    # "Lv 16" / "Level 16" / "Lv 12+"
    m = re.search(r"(lv|level)\s*(\d+)", s)
    if m:
        return int(m.group(2))

    # pure numeric or numeric with + / decimal
    m = re.fullmatch(r"(\d+)(\+)?(\.\d+)?", s)
    if m:
        return int(m.group(1))

    # bracketed numeric
    m = re.search(r"\[(\d+)\]", s)
    if m:
        return int(m.group(1))

    # roman numeral only
    if s in ROMAN_MAP:
        return ROMAN_MAP[s]

    return None


def _extract_combined_difficulty_and_level(
    difficulty_folder: Optional[str],
    level_folder: Optional[str],
) -> Dict[str, Optional[Any]]:
    """
    Support combined folder forms such as:
    - 'Ultima Lv 16'
    - 'MASTER 32'
    - 'Expert IV'
    - '[MASTER]'
    """
    difficulty = normalize_difficulty(difficulty_folder)
    level = normalize_level(level_folder)

    if difficulty is not None and level is not None:
        return {"difficulty": difficulty, "level": level}

    raw = _norm_token(difficulty_folder)
    if not raw:
        return {"difficulty": difficulty, "level": level}

    # infer level from difficulty folder if level folder missing
    inferred_level = normalize_level(raw)
    if level is None and inferred_level is not None:
        level = inferred_level

    # infer difficulty from same raw token
    inferred_difficulty = normalize_difficulty(raw)
    if difficulty is None and inferred_difficulty is not None:
        difficulty = inferred_difficulty

    return {"difficulty": difficulty, "level": level}


def validate_game_difficulty(
    game: Optional[str],
    difficulty: Optional[str],
) -> Optional[str]:
    """
    Validate whether the canonical difficulty is supported by the canonical game.

    Returns an issue code or None.
    """
    if game is None or difficulty is None:
        return None

    allowed = GAME_DIFFICULTY_CAPABILITIES.get(game)
    if not allowed:
        return "unsupported_game_folder"

    if difficulty not in allowed:
        return "difficulty_not_supported_by_game"

    return None


# ---------------------------------------------------------------------
# Public combined folder normalization
# ---------------------------------------------------------------------

def normalize_folder_identity(
    *,
    game_folder: Optional[str],
    difficulty_folder: Optional[str],
    level_folder: Optional[str],
) -> Dict[str, Optional[object]]:
    """
    Normalize identity from folder structure:

        Chart File/{game}/{difficulty}/{level}/{file}

    Handles:
    - skipped layer (e.g. proseka/lv 32/{file})
    - invalid folder names
    - mismatch directory (e.g. BanG Dream/Append/lv 25/{file})
    - combined difficulty+level folder
    - Roman numeral levels
    - post-launch / unsupported games (surfaced as issues)

    Output:
    {
        "game_raw": ...,
        "difficulty_raw": ...,
        "level_raw": ...,
        "game": ...,
        "difficulty": ...,
        "level": ...,
        "issues": [...]
    }
    """
    issues: List[str] = []

    game = normalize_game(game_folder)

    if not game_folder:
        issues.append("missing_game_folder")
    elif game not in GAME_DIFFICULTY_CAPABILITIES:
        issues.append("unknown_or_unsupported_game_folder")

    parsed = _extract_combined_difficulty_and_level(difficulty_folder, level_folder)
    difficulty = parsed.get("difficulty")
    level = parsed.get("level")

    # Difficulty folder present but not understood
    if difficulty_folder and difficulty is None:
        # special case: skipped layout like game / lv 32 / file
        if normalize_level(difficulty_folder) is not None and level_folder is None:
            issues.append("missing_difficulty_layer")
            level = level or normalize_level(difficulty_folder)
        else:
            issues.append("unknown_difficulty_folder")

    # Level folder present but not understood
    if level_folder and level is None:
        issues.append("unknown_level_folder")

    # Validate compatibility only if game / difficulty both exist
    mismatch_issue = validate_game_difficulty(game, difficulty)
    if mismatch_issue:
        issues.append(mismatch_issue)

    return {
        "game_raw": game_folder,
        "difficulty_raw": difficulty_folder,
        "level_raw": level_folder,
        "game": game,
        "difficulty": difficulty,
        "level": level,
        "issues": issues,
    }


__all__ = [
    "GAME_DIFFICULTY_CAPABILITIES",
    "GAME_ALIASES",
    "DIFFICULTY_ALIASES",
    "ROMAN_MAP",
    "normalize_game",
    "normalize_difficulty",
    "normalize_level",
    "validate_game_difficulty",
    "normalize_folder_identity",
]