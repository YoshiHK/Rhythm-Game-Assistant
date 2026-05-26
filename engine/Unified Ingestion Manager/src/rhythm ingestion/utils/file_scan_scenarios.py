from __future__ import annotations

"""
Deterministic filename scan helper for UMI utils (Phase 3).

Scope:
- Parse and match filename strings to canonical song metadata.
- Cover 17 documented scenarios + additional edge cases (18–24).
- Wiring-safe: does not parse charts, does not validate chart contents, does not mutate gameplay semantics.

Optional wiring:
- Provides helper functions that can call `file_scan_paired_runid.scan_directory/scan_many`
  to scan candidate files and immediately match their filenames.

Song row shape (dict-like), minimal:
{
    "id": 163,
    "title": "Flyer!",
    "aliases": ["飛行員！"],        # optional
    "game_key": "pjsekai",        # optional but recommended for multi-game catalogs
    "bpm": "150" or "129-226" or "186*",   # optional
    "duration": "02:03" or 123,   # optional seconds or mm:ss
    "difficulties": {"master": 29, "expert": 28}  # preferred
}
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union


DEFAULT_DIFFICULTIES = ("easy", "normal", "hard", "expert", "master", "append")

DEFAULT_AUTOMATION_TAGS = (
    "up to date",
    "fixed lfx",
    "fixed sfx",
    "processed",
    "updated",
    "backup",
    "auto",
    "localized",
)

# Common file suffix pollution / stacked extensions
KNOWN_SUFFIXES = {
    ".html", ".htm", ".svg", ".json", ".txt",
    ".png", ".jpg", ".jpeg", ".webp",
    ".zip", ".7z", ".rar",
    ".bak", ".backup", ".old",
}

# System files often appearing in chart folders (scanner-level hygiene; kept here for convenience)
SYSTEM_BASENAMES = {
    "thumbs.db",
    "desktop.ini",
    ".ds_store",
}


class ScanStatus(str, Enum):
    MATCH = "match"
    CONFLICT = "conflict"
    NO_MATCH = "no_match"


class ScenarioType(str, Enum):
    # Phase 1
    CANONICAL_PERFECT_MATCH = "scenario_01_canonical_perfect_match"
    SPACE_PADDING_VARIANCE = "scenario_02_space_padding_variance"
    LANGUAGE_ALIAS_MATCH = "scenario_03_language_cross_translation_alias_match"
    CASING_MUTATION = "scenario_04_casing_mutation"

    # Phase 2
    NON_STANDARD_AFFIX = "scenario_05_non_standard_structural_affixes"
    TYPO_DISTANCE = "scenario_06_typo_character_distance"
    NUMERICAL_LEVEL_OMISSION = "scenario_07_numerical_level_omission"
    TOKEN_TRANSPOSITION = "scenario_08_token_transposition"

    # Phase 3
    WIDE_EXPLODED_SPACING = "scenario_09_wide_exploded_spacing"
    OMITTED_DATABASE_COLUMN_TARGET = "scenario_10_omitted_database_column_target"
    EXPLICIT_SYSTEM_IDENTIFIER = "scenario_11_explicit_system_identifier"
    ZERO_TEXT_STATISTICAL_COLLISION = "scenario_12_zero_text_statistical_collision"

    # Phase 4
    PURE_PUNCTUATION_TITLE = "scenario_13_pure_punctuation_titles"
    FULL_WIDTH_MUTATION = "scenario_14_full_width_character_mutations"
    SUBSTRING_OVERLAP_TRAP = "scenario_15_substring_overlap_trap"
    COMPLEX_VARIABLE_BPM = "scenario_16_complex_variable_bpm_formatting"
    AUTOMATION_TAG_POLLUTION = "scenario_17_system_metric_automation_tag_pollution"

    # Additional (18–24)
    MULTI_EXTENSION_POLLUTION = "scenario_18_multi_extension_pollution"
    HIDDEN_SYSTEM_FILE_POLLUTION = "scenario_19_hidden_system_file_pollution"
    LEGIT_BRACKET_TITLE_CONTENT = "scenario_20_legit_bracket_title_content"
    GAME_SPECIFIC_DIFFICULTY_VOCAB = "scenario_21_game_specific_difficulty_vocab"
    VERSION_PLATFORM_SUFFIX = "scenario_22_version_platform_suffix"
    STYLIZED_LEVEL_ENCODING = "scenario_23_stylized_level_encoding"
    CROSS_GAME_TITLE_COLLISION = "scenario_24_cross_game_title_collision"


@dataclass(frozen=True)
class ParsedFilename:
    original: str
    cleaned_filename: str
    title: str = ""
    title_normalized: str = ""
    title_for_match: str = ""          # optional modified title for matching (e.g., suffix stripped)
    title_for_match_normalized: str = ""
    difficulty: Optional[str] = None
    level: Optional[int] = None
    explicit_id: Optional[int] = None
    bpm_hint: Optional[str] = None
    duration_hint_seconds: Optional[int] = None
    scenario_hits: Tuple[ScenarioType, ...] = ()


@dataclass(frozen=True)
class ScanResult:
    status: ScanStatus
    song: Optional[Mapping[str, Any]] = None
    difficulty: Optional[str] = None
    level: Optional[int] = None
    parsed: Optional[ParsedFilename] = None
    scenario_hits: Tuple[ScenarioType, ...] = ()
    reason: Optional[str] = None
    candidates: Tuple[Mapping[str, Any], ...] = ()


@dataclass
class _Candidate:
    song: Mapping[str, Any]
    score: float
    scenarios: List[ScenarioType] = field(default_factory=list)


_ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}


class FileScanScenarioEngine:
    """
    Deterministic engine that covers the file-scan scenario classes.

    Key design principle:
    - Prefer false-negative over false-positive.
    - If ambiguity remains after deterministic tie-breakers → return CONFLICT.
    """

    def __init__(
        self,
        *,
        alias_map: Optional[Mapping[str, str]] = None,
        automation_tags: Sequence[str] = DEFAULT_AUTOMATION_TAGS,
        difficulty_aliases: Optional[Mapping[str, str]] = None,
        typo_max_distance: int = 2,
        typo_ratio_threshold: float = 0.22,
        # Optional: strip these suffix patterns from titles for matching only
        # e.g. ["-tv size-", "tv size", "short ver", "arcade edit"]
        title_suffix_aliases: Optional[Sequence[str]] = None,
    ) -> None:
        self.alias_map = {self._norm_title(k): v for k, v in (alias_map or {}).items()}
        self.automation_tags = tuple(self._norm_basic(x) for x in automation_tags)

        base_aliases: Dict[str, str] = {
            "ez": "easy",
            "easy": "easy",
            "nm": "normal",
            "normal": "normal",
            "hd": "hard",
            "hard": "hard",
            "ex": "expert",
            "expert": "expert",
            "mas": "master",
            "master": "master",
            "app": "append",
            "append": "append",
        }
        if difficulty_aliases:
            for k, v in difficulty_aliases.items():
                base_aliases[self._norm_basic(k)] = self._norm_basic(v)
        self.difficulty_aliases = base_aliases

        self.typo_max_distance = typo_max_distance
        self.typo_ratio_threshold = typo_ratio_threshold

        self.title_suffix_aliases = tuple(self._norm_basic(s) for s in (title_suffix_aliases or ()))

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def match_filename(
        self,
        filename: Union[str, Path],
        songs: Iterable[Mapping[str, Any]],
        *,
        schema_fallbacks: Optional[Mapping[str, Sequence[str]]] = None,
        game_key: Optional[str] = None,
    ) -> ScanResult:
        songs_list = list(songs)
        parsed = self.parse_filename(filename)

        # Optional: scope by game_key first if catalog is mixed
        if game_key is not None:
            gk = self._norm_basic(game_key)
            scoped = [s for s in songs_list if self._norm_basic(s.get("game_key", "")) == gk]
            if scoped:
                songs_list = scoped

        # Scenario 11: explicit ID bypass
        if parsed.explicit_id is not None:
            for song in songs_list:
                if self._safe_int(song.get("id")) == parsed.explicit_id:
                    difficulty, level, diff_hits = self._resolve_difficulty_level(parsed, song, schema_fallbacks)
                    return ScanResult(
                        status=ScanStatus.MATCH,
                        song=song,
                        difficulty=difficulty,
                        level=level,
                        parsed=parsed,
                        scenario_hits=self._merge_hits(parsed.scenario_hits, diff_hits),
                    )
            return ScanResult(
                status=ScanStatus.NO_MATCH,
                parsed=parsed,
                scenario_hits=parsed.scenario_hits,
                reason=f"Explicit ID {parsed.explicit_id} was not found in songs.",
            )

        # Scenario 12: zero-text statistical collision / property-only parsing
        if not parsed.title_for_match_normalized and (parsed.bpm_hint or parsed.duration_hint_seconds is not None):
            property_matches = [s for s in songs_list if self._song_matches_property_hints(s, parsed)]
            if len(property_matches) == 1:
                song = property_matches[0]
                difficulty, level, diff_hits = self._resolve_difficulty_level(parsed, song, schema_fallbacks)
                return ScanResult(
                    status=ScanStatus.MATCH,
                    song=song,
                    difficulty=difficulty,
                    level=level,
                    parsed=parsed,
                    scenario_hits=self._merge_hits(parsed.scenario_hits, diff_hits),
                )
            if len(property_matches) > 1:
                return ScanResult(
                    status=ScanStatus.CONFLICT,
                    parsed=parsed,
                    scenario_hits=self._merge_hits(parsed.scenario_hits, (ScenarioType.ZERO_TEXT_STATISTICAL_COLLISION,)),
                    reason="Deterministic collision: multiple songs match zero-text property hints.",
                    candidates=tuple(property_matches),
                )

        candidates = self._rank_title_candidates(parsed, songs_list)

        if not candidates:
            return ScanResult(
                status=ScanStatus.NO_MATCH,
                parsed=parsed,
                scenario_hits=parsed.scenario_hits,
                reason="No song candidate matched the normalized filename tokens.",
            )

        top_score = candidates[0].score
        tied = [c for c in candidates if c.score == top_score]

        if len(tied) > 1:
            resolved = self._break_ties(parsed, tied)
            if resolved is None:
                # Scenario 24: cross-game title collision if mixed game_keys present
                if self._tied_spans_multiple_games(tied):
                    extra = (ScenarioType.CROSS_GAME_TITLE_COLLISION,)
                else:
                    extra = (ScenarioType.SUBSTRING_OVERLAP_TRAP,)
                return ScanResult(
                    status=ScanStatus.CONFLICT,
                    parsed=parsed,
                    scenario_hits=self._merge_hits(parsed.scenario_hits, extra),
                    reason="Ambiguous tie after deterministic ranking.",
                    candidates=tuple(c.song for c in tied),
                )
            chosen = resolved
        else:
            chosen = tied[0]

        difficulty, level, diff_hits = self._resolve_difficulty_level(parsed, chosen.song, schema_fallbacks)

        return ScanResult(
            status=ScanStatus.MATCH,
            song=chosen.song,
            difficulty=difficulty,
            level=level,
            parsed=parsed,
            scenario_hits=self._merge_hits(parsed.scenario_hits, tuple(chosen.scenarios), diff_hits),
        )

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    def parse_filename(self, filename: Union[str, Path]) -> ParsedFilename:
        hits: List[ScenarioType] = []
        original = str(filename)

        # quick system-file detection (usually filtered earlier by scanner)
        base_name = Path(original).name
        if base_name.casefold() in SYSTEM_BASENAMES or base_name.startswith("._"):
            hits.append(ScenarioType.HIDDEN_SYSTEM_FILE_POLLUTION)

        text, multi_ext_hit = self._strip_path_and_extensions(original)
        if multi_ext_hit:
            hits.append(ScenarioType.MULTI_EXTENSION_POLLUTION)

        # Scenario 14: full-width / IME normalization
        nfkc = unicodedata.normalize("NFKC", text)
        if nfkc != text:
            hits.append(ScenarioType.FULL_WIDTH_MUTATION)
        text = nfkc

        # Scenario 17: remove automation tags at the end only
        stripped = self._strip_automation_tags(text)
        if stripped != text:
            hits.append(ScenarioType.AUTOMATION_TAG_POLLUTION)
        text = stripped

        # Scenario 2: normalize spacing
        normalized_spaces = self._normalize_spaces(text)
        if normalized_spaces != text:
            hits.append(ScenarioType.SPACE_PADDING_VARIANCE)
        text = normalized_spaces

        # Scenario 9: collapse exploded title spacing, preserving (...) block
        collapsed = self._collapse_exploded_spacing(text)
        if collapsed != text:
            hits.append(ScenarioType.WIDE_EXPLODED_SPACING)
        text = collapsed

        # Scenario 11: explicit ID
        explicit_id = self._extract_explicit_id(text)
        if explicit_id is not None:
            hits.append(ScenarioType.EXPLICIT_SYSTEM_IDENTIFIER)

        # Scenario 16: property hints
        bpm_hint = self._extract_bpm_hint(text)
        duration_hint_seconds = self._extract_duration_hint_seconds(text)
        if bpm_hint and self._is_complex_bpm_string(bpm_hint):
            hits.append(ScenarioType.COMPLEX_VARIABLE_BPM)

        title, difficulty, level, local_hits = self._extract_title_diff_level(text)
        hits.extend(local_hits)

        # Scenario 20: title contains legitimate bracket content (not trailing automation tags)
        if title and re.search(r"[\[\(].+[\]\)]", title):
            hits.append(ScenarioType.LEGIT_BRACKET_TITLE_CONTENT)

        # Scenario 3: alias remap
        canonical_title = title
        title_norm = self._norm_title(title)
        if title_norm in self.alias_map:
            canonical_title = self.alias_map[title_norm]
            title_norm = self._norm_title(canonical_title)
            hits.append(ScenarioType.LANGUAGE_ALIAS_MATCH)

        # Scenario 22: optional suffix stripping for matching only
        title_for_match = canonical_title
        title_for_match_norm = title_norm
        if self.title_suffix_aliases and title_for_match:
            stripped_title = self._strip_title_suffix_aliases(title_for_match)
            if stripped_title != title_for_match:
                title_for_match = stripped_title
                title_for_match_norm = self._norm_title(stripped_title)
                hits.append(ScenarioType.VERSION_PLATFORM_SUFFIX)

        # Scenario 13: punctuation-only title
        if canonical_title and not self._contains_word_or_digit(canonical_title):
            hits.append(ScenarioType.PURE_PUNCTUATION_TITLE)

        # Scenario 4: casing mutation
        if title and title != title.lower():
            if self._norm_title(title) == self._norm_title(title.lower()):
                hits.append(ScenarioType.CASING_MUTATION)

        # Scenario 21: game-specific difficulty vocab (if non-default and recognized via alias_map)
        if difficulty and difficulty not in DEFAULT_DIFFICULTIES:
            hits.append(ScenarioType.GAME_SPECIFIC_DIFFICULTY_VOCAB)

        # Scenario 1: canonical clean structure
        if canonical_title and difficulty and level is not None:
            canonical_form = f"{canonical_title} ({difficulty.title()} {level})"
            if text == canonical_form:
                hits.append(ScenarioType.CANONICAL_PERFECT_MATCH)

        return ParsedFilename(
            original=original,
            cleaned_filename=text,
            title=canonical_title,
            title_normalized=title_norm,
            title_for_match=title_for_match,
            title_for_match_normalized=title_for_match_norm,
            difficulty=difficulty,
            level=level,
            explicit_id=explicit_id,
            bpm_hint=bpm_hint,
            duration_hint_seconds=duration_hint_seconds,
            scenario_hits=self._dedupe_hits(hits),
        )

    def _extract_title_diff_level(self, text: str) -> Tuple[str, Optional[str], Optional[int], List[ScenarioType]]:
        hits: List[ScenarioType] = []

        # general structure: <title> (<meta>) where last (...) is meta
        m = re.match(r"^(?P<title>.*?)(?:\((?P<meta>[^()]*)\))?$", text.strip())
        if not m:
            return text.strip(), None, None, hits

        title = (m.group("title") or "").strip()
        meta = (m.group("meta") or "").strip()

        # Scenario 5: strip leading bracket affixes like [Internal]
        affix_stripped = re.sub(r"^(?:\[[^\]]+\]\s*)+", "", title).strip()
        if affix_stripped != title:
            title = affix_stripped
            hits.append(ScenarioType.NON_STANDARD_AFFIX)

        difficulty: Optional[str] = None
        level: Optional[int] = None
        if meta:
            difficulty, level, meta_hits = self._parse_meta_block(meta)
            hits.extend(meta_hits)

        return title, difficulty, level, self._dedupe_hits(hits)

    def _parse_meta_block(self, meta: str) -> Tuple[Optional[str], Optional[int], List[ScenarioType]]:
        hits: List[ScenarioType] = []
        meta = self._normalize_spaces(meta)

        tokens = [t for t in re.split(r"[\s/_-]+", meta) if t]
        difficulty: Optional[str] = None
        level: Optional[int] = None

        for token in tokens:
            norm = self._norm_basic(token)

            # difficulty token
            if difficulty is None and norm in self.difficulty_aliases:
                difficulty = self.difficulty_aliases[norm]
                if difficulty not in DEFAULT_DIFFICULTIES:
                    hits.append(ScenarioType.GAME_SPECIFIC_DIFFICULTY_VOCAB)
                continue

            # plain digits
            if level is None and token.isdigit():
                level = int(token)
                continue

            # Scenario 23: stylized levels: ★29 / Lv.29 / Level29 / LEVEL 29
            if level is None:
                m = re.search(r"(?:^|[^a-z])(?:lv|level)\.?\s*[★☆]?\s*(\d{1,2})(?:$|[^0-9])", token, flags=re.IGNORECASE)
                if m:
                    level = int(m.group(1))
                    hits.append(ScenarioType.STYLIZED_LEVEL_ENCODING)
                    continue

                m2 = re.search(r"[★☆]\s*(\d{1,2})", token)
                if m2:
                    level = int(m2.group(1))
                    hits.append(ScenarioType.STYLIZED_LEVEL_ENCODING)
                    continue

                roman = self._roman_to_int(token)
                if roman is not None:
                    level = roman
                    hits.append(ScenarioType.STYLIZED_LEVEL_ENCODING)
                    continue

        # Scenario 8: token transposition ("29 Expert")
        if len(tokens) >= 2 and tokens[0].isdigit():
            second_norm = self._norm_basic(tokens[1])
            if second_norm in self.difficulty_aliases:
                hits.append(ScenarioType.TOKEN_TRANSPOSITION)

        # Scenario 7: difficulty present but level omitted
        if difficulty and level is None:
            hits.append(ScenarioType.NUMERICAL_LEVEL_OMISSION)

        return difficulty, level, self._dedupe_hits(hits)

    # ------------------------------------------------------------------
    # Ranking / matching
    # ------------------------------------------------------------------
    def _rank_title_candidates(self, parsed: ParsedFilename, songs: Sequence[Mapping[str, Any]]) -> List[_Candidate]:
        if not parsed.title_for_match_normalized:
            return []

        candidates: List[_Candidate] = []
        q = parsed.title_for_match_normalized

        for song in songs:
            variants = self._song_title_variants(song)
            best_score = 0.0
            best_hits: List[ScenarioType] = []

            for variant in variants:
                vnorm = self._norm_title(variant)
                if not vnorm:
                    continue

                # Scenario 1: exact normalized title match
                if q == vnorm:
                    score = 100.0
                    hits = [ScenarioType.CANONICAL_PERFECT_MATCH]

                # Scenario 5/15: containment / overlap
                elif (q in vnorm) or (vnorm in q):
                    score = 88.0 - abs(len(q) - len(vnorm)) * 0.2
                    hits = [ScenarioType.NON_STANDARD_AFFIX]
                    if q != vnorm:
                        hits.append(ScenarioType.SUBSTRING_OVERLAP_TRAP)

                # Scenario 6: typo / edit distance (bounded)
                else:
                    dist = self._levenshtein(q, vnorm)
                    max_len = max(len(q), len(vnorm), 1)
                    ratio = dist / max_len
                    if dist <= self.typo_max_distance and ratio <= self.typo_ratio_threshold:
                        score = 80.0 - dist * 3.0
                        hits = [ScenarioType.TYPO_DISTANCE]
                    else:
                        continue

                if score > best_score:
                    best_score = round(score, 3)
                    best_hits = hits

            if best_score > 0:
                candidates.append(_Candidate(song=song, score=best_score, scenarios=best_hits))

        candidates.sort(key=lambda c: (-c.score, self._song_sort_key(c.song)))
        return candidates

    def _break_ties(self, parsed: ParsedFilename, tied: Sequence[_Candidate]) -> Optional[_Candidate]:
        """
        Scenario 15 tie-break:
        - Prefer closest title length parity (against song['title'])
        - Then stable sort key
        - If still tied, return None → deterministic CONFLICT
        """
        if len(tied) <= 1:
            return tied[0] if tied else None

        q_len = len(parsed.title_for_match_normalized)

        ranked = sorted(
            tied,
            key=lambda c: (
                abs(len(self._norm_title(c.song.get("title", ""))) - q_len),
                self._song_sort_key(c.song),
            ),
        )

        if len(ranked) >= 2:
            d0 = abs(len(self._norm_title(ranked[0].song.get("title", ""))) - q_len)
            d1 = abs(len(self._norm_title(ranked[1].song.get("title", ""))) - q_len)
            if d0 == d1:
                return None

        ranked[0].scenarios.append(ScenarioType.SUBSTRING_OVERLAP_TRAP)
        return ranked[0]

    def _tied_spans_multiple_games(self, tied: Sequence[_Candidate]) -> bool:
        gks = set()
        for c in tied:
            gk = self._norm_basic(c.song.get("game_key", ""))
            if gk:
                gks.add(gk)
        return len(gks) > 1

    # ------------------------------------------------------------------
    # Difficulty / level resolution
    # ------------------------------------------------------------------
    def _resolve_difficulty_level(
        self,
        parsed: ParsedFilename,
        song: Mapping[str, Any],
        schema_fallbacks: Optional[Mapping[str, Sequence[str]]] = None,
    ) -> Tuple[Optional[str], Optional[int], Tuple[ScenarioType, ...]]:
        hits: List[ScenarioType] = []
        difficulties = self._song_difficulties(song)

        if parsed.difficulty:
            diff = parsed.difficulty

            if diff in difficulties:
                return diff, self._safe_int(difficulties.get(diff)), self._dedupe_hits(hits)

            # Scenario 10: schema fallback if expected column absent
            if schema_fallbacks and diff in schema_fallbacks:
                for fallback in schema_fallbacks[diff]:
                    fb = self._norm_basic(fallback)
                    if fb in difficulties:
                        hits.append(ScenarioType.OMITTED_DATABASE_COLUMN_TARGET)
                        return fb, self._safe_int(difficulties.get(fb)), self._dedupe_hits(hits)

            # difficulty known from filename but not found in row/schema
            return diff, parsed.level, self._dedupe_hits(hits)

        # Scenario 7 secondary inference: level only -> infer difficulty if unique
        if parsed.level is not None:
            matched = [
                (name, self._safe_int(value))
                for name, value in difficulties.items()
                if self._safe_int(value) == parsed.level
            ]
            if len(matched) == 1:
                hits.append(ScenarioType.NUMERICAL_LEVEL_OMISSION)
                return matched[0][0], matched[0][1], self._dedupe_hits(hits)

        return None, parsed.level, self._dedupe_hits(hits)

    # ------------------------------------------------------------------
    # Property-only matching (Scenario 12 + 16)
    # ------------------------------------------------------------------
    def _song_matches_property_hints(self, song: Mapping[str, Any], parsed: ParsedFilename) -> bool:
        if parsed.bpm_hint:
            if not self._bpm_hint_matches_song(parsed.bpm_hint, song.get("bpm")):
                return False
        if parsed.duration_hint_seconds is not None:
            song_duration = self._parse_duration_seconds(song.get("duration"))
            if song_duration != parsed.duration_hint_seconds:
                return False
        return True

    def _bpm_hint_matches_song(self, bpm_hint: str, song_bpm: Any) -> bool:
        target = self._parse_bpm_range(bpm_hint)
        actual = self._parse_bpm_range(song_bpm)
        if target is None or actual is None:
            return False
        return target[0] >= actual[0] and target[1] <= actual[1]

    # ------------------------------------------------------------------
    # Song metadata helpers
    # ------------------------------------------------------------------
    def _song_title_variants(self, song: Mapping[str, Any]) -> List[str]:
        values: List[str] = []
        for key in ("title", "title_en", "title_jp"):
            v = song.get(key)
            if isinstance(v, str) and v.strip():
                values.append(v.strip())

        aliases = song.get("aliases") or ()
        if isinstance(aliases, (list, tuple, set)):
            for a in aliases:
                a = str(a).strip()
                if a:
                    values.append(a)

        # optional: allow per-song alias_map style via dict
        alias_map = song.get("alias_map")
        if isinstance(alias_map, Mapping):
            for k in alias_map.keys():
                kk = str(k).strip()
                if kk:
                    values.append(kk)

        return list(dict.fromkeys(values))

    def _song_difficulties(self, song: Mapping[str, Any]) -> Dict[str, Any]:
        nested = song.get("difficulties")
        if isinstance(nested, Mapping):
            return {self._norm_basic(k): v for k, v in nested.items()}

        direct: Dict[str, Any] = {}
        for key in DEFAULT_DIFFICULTIES:
            if key in song:
                direct[key] = song[key]
        return direct

    def _song_sort_key(self, song: Mapping[str, Any]) -> Tuple[Any, ...]:
        song_id = self._safe_int(song.get("id"))
        title = self._norm_title(song.get("title", ""))
        return (song_id if song_id is not None else 10**9, title)

    # ------------------------------------------------------------------
    # Normalization helpers
    # ------------------------------------------------------------------
    def _strip_path_and_extensions(self, text: str) -> Tuple[str, bool]:
        """
        Scenario 18: allow stripping multiple stacked extensions.
        Returns (base_name, multi_ext_hit).
        """
        name = Path(text).name.strip()
        hit = False
        while True:
            lower = name.lower()
            dot = lower.rfind(".")
            if dot == -1:
                break
            suffix = lower[dot:]
            if suffix in KNOWN_SUFFIXES:
                name = name[:dot]
                hit = True
                continue
            # generic short extension fallback (1-8 chars)
            if re.fullmatch(r"\.[a-z0-9]{1,8}", suffix) and suffix in {".json", ".txt", ".svg", ".htm", ".html"}:
                name = name[:dot]
                hit = True
                continue
            break
        return name.strip(), hit

    def _strip_automation_tags(self, text: str) -> str:
        """
        Scenario 17: only strip trailing [...] tags if they match known automation tags.
        """
        out = text
        changed = True
        while changed:
            changed = False
            m = re.search(r"\[(.*?)\]\s*$", out)
            if not m:
                break
            inner = self._norm_basic(m.group(1))
            if inner in self.automation_tags:
                out = out[: m.start()].rstrip()
                changed = True
        return out

    def _normalize_spaces(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text.strip())
        text = re.sub(r"\(\s+", "(", text)
        text = re.sub(r"\s+\)", ")", text)
        text = re.sub(r"\s+\(", " (", text)
        text = re.sub(r"\s+,", ",", text)
        text = re.sub(r",\s+", ", ", text)
        return text.strip()

    def _collapse_exploded_spacing(self, text: str) -> str:
        """
        Scenario 9: collapse segments like 'F l y e r !' while leaving '(Master 29)' intact.
        """
        def collapse(segment: str) -> str:
            tokens = [t for t in segment.split(" ") if t != ""]
            if len(tokens) >= 3 and all(len(tok) == 1 for tok in tokens):
                return "".join(tokens)
            return segment

        parts = re.split(r"(\([^)]*\))", text)
        parts = [collapse(p) if not p.startswith("(") else p for p in parts]
        return "".join(parts)

    def _strip_title_suffix_aliases(self, title: str) -> str:
        """
        Scenario 22: strip known suffix aliases from title for matching only.
        Conservative: only strips if suffix appears at end in bracket or after dash.
        """
        t = title.strip()
        norm = self._norm_basic(t)
        for sfx in self.title_suffix_aliases:
            if not sfx:
                continue
            # patterns: "Title - TV Size", "Title (TV Size)", "Title [TV Size]"
            if norm.endswith(" - " + sfx) or norm.endswith("-" + sfx):
                # remove trailing dash segment
                idx = t.lower().rfind("-")
                if idx != -1:
                    return t[:idx].strip()
            if norm.endswith("(" + sfx + ")") or norm.endswith("[" + sfx + "]"):
                # remove trailing bracketed suffix
                t2 = re.sub(r"\s*[\(\[]\s*" + re.escape(sfx) + r"\s*[\)\]]\s*$", "", t, flags=re.IGNORECASE)
                return t2.strip()
        return t

    def _extract_explicit_id(self, text: str) -> Optional[int]:
        m = re.search(r"\bID\s*:\s*(\d+)\b", text, flags=re.IGNORECASE)
        return int(m.group(1)) if m else None

    def _extract_bpm_hint(self, text: str) -> Optional[str]:
        for token in re.findall(r"\[(.*?)\]", text):
            if self._looks_like_bpm(token):
                return token.strip()
        return None

    def _extract_duration_hint_seconds(self, text: str) -> Optional[int]:
        for token in re.findall(r"\[(.*?)\]", text):
            if self._looks_like_duration(token):
                return self._parse_duration_seconds(token)
        return None

    def _norm_basic(self, value: Any) -> str:
        return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(value or "")).strip().lower())

    def _norm_title(self, value: Any) -> str:
        return self._norm_basic(value)

    def _contains_word_or_digit(self, text: str) -> bool:
        return bool(re.search(r"[\w\u3040-\u30ff\u4e00-\u9fff]", text))

    # ------------------------------------------------------------------
    # Numeric parsing helpers
    # ------------------------------------------------------------------
    def _looks_like_bpm(self, text: str) -> bool:
        return bool(re.fullmatch(r"\d+(?:\s*-\s*\d+)?\*?", text.strip()))

    def _looks_like_duration(self, text: str) -> bool:
        return bool(re.fullmatch(r"\d{1,2}:\d{2}", text.strip()))

    def _is_complex_bpm_string(self, text: str) -> bool:
        t = str(text).strip()
        return "-" in t or t.endswith("*")

    def _parse_bpm_range(self, value: Any) -> Optional[Tuple[int, int]]:
        if value is None:
            return None
        text = unicodedata.normalize("NFKC", str(value)).strip().replace(" ", "")
        text = text.rstrip("*")
        if "-" in text:
            left, right = text.split("-", 1)
            if left.isdigit() and right.isdigit():
                a, b = int(left), int(right)
                return (min(a, b), max(a, b))
            return None
        if text.isdigit():
            bpm = int(text)
            return (bpm, bpm)
        return None

    def _parse_duration_seconds(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return int(round(float(value)))
        text = unicodedata.normalize("NFKC", str(value)).strip()
        if re.fullmatch(r"\d{1,2}:\d{2}", text):
            minutes, seconds = text.split(":", 1)
            return int(minutes) * 60 + int(seconds)
        # Excel fractional day support
        try:
            numeric = float(text)
        except Exception:
            return None
        if 0 < numeric < 1:
            return int(round(numeric * 24 * 60 * 60))
        return int(round(numeric))

    def _safe_int(self, value: Any) -> Optional[int]:
        try:
            if value is None or value == "":
                return None
            return int(float(value))
        except Exception:
            return None

    def _roman_to_int(self, s: str) -> Optional[int]:
        s2 = self._norm_basic(s).replace(".", "").strip()
        if not s2 or not re.fullmatch(r"[ivxlcdm]+", s2):
            return None
        total = 0
        prev = 0
        for ch in reversed(s2):
            v = _ROMAN[ch]
            if v < prev:
                total -= v
            else:
                total += v
                prev = v
        return total if total > 0 else None

    # ------------------------------------------------------------------
    # Distance metric (bounded levenshtein)
    # ------------------------------------------------------------------
    def _levenshtein(self, left: str, right: str) -> int:
        if left == right:
            return 0
        if not left:
            return len(right)
        if not right:
            return len(left)

        prev = list(range(len(right) + 1))
        for i, ch_l in enumerate(left, start=1):
            curr = [i]
            for j, ch_r in enumerate(right, start=1):
                insert_cost = curr[j - 1] + 1
                delete_cost = prev[j] + 1
                replace_cost = prev[j - 1] + (0 if ch_l == ch_r else 1)
                curr.append(min(insert_cost, delete_cost, replace_cost))
            prev = curr
        return prev[-1]

    # ------------------------------------------------------------------
    # Hit helpers
    # ------------------------------------------------------------------
    def _dedupe_hits(self, hits: Sequence[ScenarioType]) -> Tuple[ScenarioType, ...]:
        seen: List[ScenarioType] = []
        for h in hits:
            if h not in seen:
                seen.append(h)
        return tuple(seen)

    def _merge_hits(self, *groups: Sequence[ScenarioType]) -> Tuple[ScenarioType, ...]:
        merged: List[ScenarioType] = []
        for g in groups:
            for item in g:
                if item not in merged:
                    merged.append(item)
        return tuple(merged)


# ----------------------------------------------------------------------
# Wiring helpers (optional): integrate with file_scan_paired_runid scanner
# ----------------------------------------------------------------------

def scan_directory_and_match(
    root: Union[str, Path],
    *,
    songs: Sequence[Mapping[str, Any]],
    engine: Optional[FileScanScenarioEngine] = None,
    schema_fallbacks: Optional[Mapping[str, Sequence[str]]] = None,
    allowed_extensions: Optional[Sequence[str]] = None,
    ignore_hidden: bool = True,
    follow_symlinks: bool = False,
    game_key: Optional[str] = None,
    drop_system_files: bool = True,
) -> List[ScanResult]:
    """
    Convenience wrapper:
    - Calls Phase-3 scanner (file_scan_paired_runid.scan_directory)
    - Then matches each candidate file path using FileScanScenarioEngine
    - Returns list of ScanResult in deterministic candidate order
    """
    engine = engine or FileScanScenarioEngine()

    # Import inside function to avoid circular dependency / optional wiring
    from . import file_scan_paired_runid as scanner  # type: ignore

    root_p = Path(root)
    candidates = scanner.scan_directory(
        root_p,
        allowed_extensions=allowed_extensions,
        ignore_hidden=ignore_hidden,
        follow_symlinks=follow_symlinks,
    )

    if drop_system_files:
        candidates = [p for p in candidates if p.name.casefold() not in SYSTEM_BASENAMES and not p.name.startswith("._")]

    results: List[ScanResult] = []
    for p in candidates:
        results.append(
            engine.match_filename(
                p,
                songs,
                schema_fallbacks=schema_fallbacks,
                game_key=game_key,
            )
        )
    return results


def scan_many_and_match(
    roots: Sequence[Union[str, Path]],
    *,
    songs: Sequence[Mapping[str, Any]],
    engine: Optional[FileScanScenarioEngine] = None,
    schema_fallbacks: Optional[Mapping[str, Sequence[str]]] = None,
    allowed_extensions: Optional[Sequence[str]] = None,
    ignore_hidden: bool = True,
    follow_symlinks: bool = False,
    game_key: Optional[str] = None,
    drop_system_files: bool = True,
) -> List[ScanResult]:
    """
    Like scan_directory_and_match, but for multiple roots.
    """
    engine = engine or FileScanScenarioEngine()
    from . import file_scan_paired_runid as scanner  # type: ignore

    roots_p = [Path(r) for r in roots]
    candidates = scanner.scan_many(
        roots_p,
        allowed_extensions=allowed_extensions,
        ignore_hidden=ignore_hidden,
        follow_symlinks=follow_symlinks,
    )

    if drop_system_files:
        candidates = [p for p in candidates if p.name.casefold() not in SYSTEM_BASENAMES and not p.name.startswith("._")]

    results: List[ScanResult] = []
    for p in candidates:
        results.append(
            engine.match_filename(
                p,
                songs,
                schema_fallbacks=schema_fallbacks,
                game_key=game_key,
            )
        )
    return results


__all__ = [
    "DEFAULT_AUTOMATION_TAGS",
    "DEFAULT_DIFFICULTIES",
    "KNOWN_SUFFIXES",
    "SYSTEM_BASENAMES",
    "FileScanScenarioEngine",
    "ParsedFilename",
    "ScanResult",
    "ScanStatus",
    "ScenarioType",
    "scan_directory_and_match",
    "scan_many_and_match",
]