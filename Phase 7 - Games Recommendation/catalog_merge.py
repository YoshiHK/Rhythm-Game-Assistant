from pathlib import Path

pkg = Path('rhythm_recommendation/phase7')
pkg.mkdir(parents=True, exist_ok=True)

code = '''from __future__ import annotations

"""catalog_merge.py

Phase 7 — Catalog Merge (games.json + catalog.json)

Purpose
-------
Provide a single *display-ready* view by merging:
- <File>games.json</File> (authoritative identity + status; Phase 3/7 source of truth)
- catalog.json (optional, additive UI metadata; icons/links/display overrides)

This module is intentionally **wiring + presentation only**:
- It MUST NOT make recommendation decisions or ranking.
- It MUST NOT mutate registry semantics.
- It MUST remain downstream-only (no imports from completed phase logic).

Localized display name support
------------------------------
If catalog.json contains:
  display: {
    default: "...",
    i18n: { "en": "...", "ja": "...", ... }
  }
then locale resolution will prefer:
  i18n[exact_locale] -> i18n[base_language] -> display.default -> games.json display_name

"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .registry import GameInfo, GameRegistry
from .game_catalog import CatalogItem
from .registry_loader import load_registry_config, get_all_games
from .catalog_loader import load_catalog_config_optional, get_all_catalog_entries


# ----------------------------
# Merged display contract
# ----------------------------

@dataclass(frozen=True)
class MergedCatalogItem:
    """Merged, display-ready game entry.

    Fields:
    - `display_name` is the resolved name for the requested locale.
    - `registry_display_name` is the raw name from games.json.
    - `catalog_display_default` is the optional display.default from catalog.json.

    Any additional catalog metadata is attached under `catalog_meta`.
    """

    game_id: str
    status: str

    display_name: str
    registry_display_name: str
    catalog_display_default: Optional[str]

    # Optional registry extras (if present in registry.py GameInfo)
    platforms: Optional[List[str]]
    locales: Optional[List[str]]
    tags: Optional[List[str]]

    # Optional UI metadata (icons, links, etc.)
    catalog_meta: Dict[str, Any]


# ----------------------------
# Merge utilities
# ----------------------------

def merge_catalogs(
    *,
    registry: GameRegistry,
    catalog_entries: Dict[str, Dict[str, Any]],
    locale: str = 'en',
    include_statuses: Optional[Sequence[str]] = None,
) -> List[MergedCatalogItem]:
    """Merge registry + catalog entries into display-ready items.

    Parameters
    ----------
    registry:
        Phase 7 GameRegistry (authoritative games list)
    catalog_entries:
        Dict keyed by game_id loaded from catalog.json (optional)
    locale:
        Desired locale string (e.g., 'en', 'en-US', 'zh-Hant')
    include_statuses:
        If provided, only games whose registry status is included will be returned.

    Returns
    -------
    List[MergedCatalogItem]
        Sorted by display_name then game_id.
    """
    loc = str(locale or 'en')
    allowed = {str(s) for s in include_statuses} if include_statuses else None

    out: List[MergedCatalogItem] = []
    for gid in registry.list_game_ids():
        info = registry.get(gid)
        if info is None:
            continue
        if allowed is not None and info.status not in allowed:
            continue

        cat = catalog_entries.get(gid) if isinstance(catalog_entries, dict) else None
        cat = cat if isinstance(cat, dict) else {}

        disp = _safe_dict(cat.get('display'))
        resolved = resolve_display_name_from_merge(
            registry_name=info.display_name,
            display_node=disp,
            locale=loc,
        )

        out.append(
            MergedCatalogItem(
                game_id=info.game_id,
                status=info.status,
                display_name=resolved,
                registry_display_name=info.display_name,
                catalog_display_default=_safe_str(disp.get('default')),
                platforms=list(info.platforms) if info.platforms else None,
                locales=list(info.locales) if info.locales else None,
                tags=list(info.tags) if info.tags else None,
                catalog_meta=_strip_display_node(cat),
            )
        )

    return sorted(out, key=lambda x: (x.display_name.lower(), x.game_id))


def resolve_display_name_from_merge(
    *,
    registry_name: str,
    display_node: Dict[str, Any],
    locale: str,
    locale_aliases: Optional[Dict[str, str]] = None,
) -> str:
    """Resolve display name with locale alias + fallback chain.

    Order:
      1) i18n[locale_fallback_chain(normalized_locale)]
      2) display.default
      3) registry display_name
    """
    i18n = _safe_dict(display_node.get("i18n"))

    norm = normalize_locale(locale, aliases=locale_aliases)

    for key in locale_fallback_chain(norm, aliases=locale_aliases):
        hit = _safe_str(i18n.get(key))
        if hit:
            return hit

    dflt = _safe_str(display_node.get("default"))
    if dflt:
        return dflt

    return str(registry_name)


def to_catalog_items(merged: Sequence[MergedCatalogItem]) -> List[CatalogItem]:
    """Convert merged items into the simpler CatalogItem contract used by GameCatalog."""
    out: List[CatalogItem] = []
    for m in merged:
        out.append(
            CatalogItem(
                game_id=m.game_id,
                status=m.status,
                display_name=m.display_name,
                registry_display_name=m.registry_display_name,
                platforms=list(m.platforms) if m.platforms else None,
                locales=list(m.locales) if m.locales else None,
                tags=list(m.tags) if m.tags else None,
            )
        )
    return out


# ----------------------------
# Convenience: load + merge
# ----------------------------

def load_and_merge(
    *,
    games_json_path: str | None = None,
    catalog_json_path: str | None = None,
    locale: str = 'en',
    include_statuses: Optional[Sequence[str]] = None,
) -> List[MergedCatalogItem]:
    """Convenience wrapper that loads configs from disk and returns merged items.

    Notes:
    - Uses the Phase 7 loader style (normalization) under the hood.
    - catalog.json is optional; missing file yields an empty catalog.
    """
    # Load games.json via loader (normalized dict form)
    reg_cfg = load_registry_config(games_json_path) if games_json_path else load_registry_config()
    games = get_all_games(reg_cfg)

    # Build a GameRegistry from normalized dict without depending on Phase 3 loaders.
    registry = _build_registry_from_normalized_games(games)

    cat_cfg = load_catalog_config_optional(catalog_json_path) if catalog_json_path else load_catalog_config_optional()
    catalog_entries = get_all_catalog_entries(cat_cfg)

    return merge_catalogs(
        registry=registry,
        catalog_entries=catalog_entries,
        locale=locale,
        include_statuses=include_statuses,
    )


# ----------------------------
# Internal helpers
# ----------------------------

from pathlib import Path
import json
from typing import Dict, Optional, List, Set

def load_locale_aliases(path: str | Path = "locale_aliases.json") -> Dict[str, str]:
    """Load locale alias mapping from locale_aliases.json.

    File format:
    {
      "aliases": { "zh-hk": "zh-Hant-HK", ... },
      "notes": "Keys are lowercased before lookup..."
    }

    Returns empty dict if missing or malformed.
    """
    p = Path(path)
    if not p.exists():
        return {}
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {}
    aliases = raw.get("aliases")
    if not isinstance(aliases, dict):
        return {}
    return {str(k).lower(): str(v) for k, v in aliases.items()}

def normalize_locale(locale: str, *, aliases: Optional[Dict[str, str]] = None) -> str:
    """Normalize locale using alias map (presentation-only).

    - Lowercase key lookup
    - '_' normalized to '-'
    - If no mapping exists, return normalized input.
    """
    loc = str(locale or "").strip()
    if not loc:
        return ""
    norm = loc.replace("_", "-")
    amap = aliases or {}
    mapped = amap.get(norm.lower())
    return str(mapped) if mapped else norm

def locale_fallback_chain(locale: str, *, aliases: Optional[Dict[str, str]] = None) -> List[str]:
    """Return locale fallback chain from most-specific to least-specific.

    Includes alias-normalized and raw variants (deduplicated).
    Example:
      input 'zh-hk' with alias map -> normalize -> 'zh-Hant-HK'
      chain -> ['zh-Hant-HK', 'zh-Hant', 'zh']
    """
    raw = str(locale or "").strip()
    if not raw:
        return []

    norm = normalize_locale(raw, aliases=aliases)
    candidates: List[str] = []
    for base in [norm, raw.replace("_", "-")]:
        if base and base not in candidates:
            candidates.append(base)

    chain: List[str] = []
    for loc in candidates:
        parts = [p for p in loc.split("-") if p]
        for i in range(len(parts), 0, -1):
            chain.append("-".join(parts[:i]))
        if parts:
            chain.append(parts[0])  # defensive base language

    seen: Set[str] = set()
    out: List[str] = []
    for x in chain:
        if x and x not in seen:
            out.append(x)
            seen.add(x)
    return out

def _safe_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _safe_str(x: Any) -> Optional[str]:
    return str(x) if isinstance(x, str) and x.strip() else None


def _base_lang(locale: str) -> str:
    loc = str(locale or '').strip()
    if not loc:
        return ''
    # split en-US / zh-Hant-HK etc.
    for sep in ('-', '_'):
        if sep in loc:
            return loc.split(sep, 1)[0]
    return loc

def _locale_fallback_chain(locale: str) -> List[str]:
    """Return a locale fallback chain from most-specific to least-specific.

    Examples:
        'en-US' -> ['en-US', 'en']
        'zh-Hant-HK' -> ['zh-Hant-HK', 'zh-Hant', 'zh']
        'pt_BR' -> ['pt_BR', 'pt']
        '' -> []
    """
    loc = str(locale or '').strip()
    if not loc:
        return []

    # Normalize separator to '-'
    norm = loc.replace('_', '-')
    parts = [p for p in norm.split('-') if p]

    chain: List[str] = []
    # Build progressively less-specific locales: full -> drop rightmost each time
    for i in range(len(parts), 0, -1):
        chain.append('-'.join(parts[:i]))

    # Also include original form if it differed (e.g., user passed underscore form)
    # This helps if your i18n keys use underscores for some reason.
    if loc != norm and loc not in chain:
        chain.insert(0, loc)

    # Deduplicate while preserving order
    seen = set()
    out: List[str] = []
    for x in chain:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out

    # ----------------------------------------
    # Validation snippet for locale fallback
    # ----------------------------------------

    def _test_locale_fallback():
        # Simulated catalog display node
        display_node = {
            "default": "Project SEKAI",
            "i18n": {
                "en": "Project SEKAI (EN)",
                "en-GB": "Project SEKAI (UK)",
                "ja": "プロジェクトセカイ",
                "zh": "世界計畫",
                "zh-Hant": "世界計畫（繁體）",
            }
        }

        registry_name = "Project SEKAI (Registry)"

        tests = [
            # (locale, expected_result)
            ("en-US", "Project SEKAI (EN)"),        # en-US -> en
            ("en-GB", "Project SEKAI (UK)"),        # exact match
            ("en", "Project SEKAI (EN)"),           # exact match
            ("ja-JP", "プロジェクトセカイ"),        # ja-JP -> ja
            ("zh-Hant-HK", "世界計畫（繁體）"),     # zh-Hant-HK -> zh-Hant
            ("zh-CN", "世界計畫"),                  # zh-CN -> zh
            ("fr-FR", "Project SEKAI"),             # fallback to display.default
            ("", "Project SEKAI"),                  # empty locale -> default
            (None, "Project SEKAI"),                # None -> default
        ]

        print("Locale fallback validation results:\n")

        for locale, expected in tests:
            result = resolve_display_name_from_merge(
                registry_name=registry_name,
                display_node=display_node,
                locale=locale or "",
            )
            status = "✅ PASS" if result == expected else "❌ FAIL"
            print(f"[{status}] locale={locale!r:12} -> {result!r}")

            if result != expected:
                print(f"    Expected: {expected!r}")

        print("\nValidation complete.")


    # Run manually if desired
    if __name__ == "__main__":
        _test_locale_fallback()

    # ----------------------------------------
    # Validation snippet: locale alias support
    # ----------------------------------------

    def _test_locale_alias_fallback():
        # Simulated catalog display node with i18n entries
        display_node = {
            "default": "Project SEKAI",
            "i18n": {
                # English
                "en": "Project SEKAI (EN)",
                "en-GB": "Project SEKAI (UK)",

                # Japanese
                "ja": "プロジェクトセカイ",

                # Chinese
                "zh": "世界計畫",
                "zh-Hans": "世界计划（简体）",
                "zh-Hant": "世界計畫（繁體）",
                "zh-Hant-HK": "世界計畫（香港）",
            }
        }

        registry_name = "Project SEKAI (Registry)"

        # Alias table example (mirrors locale_aliases.json behavior)
        # Keys are lowercased before lookup
        locale_aliases = {
            "en": "en-US",
            "en-us": "en-US",
            "en-gb": "en-GB",
            "zh": "zh-Hans",
            "zh-cn": "zh-Hans",
            "zh-sg": "zh-Hans",
            "zh-hk": "zh-Hant-HK",
            "zh-hant-hk": "zh-Hant-HK",
            "zh-tw": "zh-Hant-TW",
            "zh-hant": "zh-Hant-TW",
            "ja": "ja-JP",
            "ja-jp": "ja-JP",
        }

        tests = [
            # (input_locale, expected_display_name)
            ("en", "Project SEKAI (EN)"),                 # en -> alias en-US -> en
            ("en-US", "Project SEKAI (EN)"),              # en-US -> en
            ("en-GB", "Project SEKAI (UK)"),              # exact
            ("ja", "プロジェクトセカイ"),                  # ja -> ja-JP -> ja
            ("ja-JP", "プロジェクトセカイ"),               # base fallback
            ("zh", "世界计划（简体）"),                    # zh -> zh-Hans
            ("zh-CN", "世界计划（简体）"),                 # zh-CN -> zh-Hans
            ("zh-HK", "世界計畫（香港）"),                 # zh-HK -> zh-Hant-HK
            ("zh-Hant-HK", "世界計畫（香港）"),            # exact
            ("fr-FR", "Project SEKAI"),                   # fallback to display.default
            ("", "Project SEKAI"),                        # empty -> default
        ]

        print("Locale alias + fallback validation:\n")

        for locale, expected in tests:
            result = resolve_display_name_from_merge(
                registry_name=registry_name,
                display_node=display_node,
                locale=locale,
                locale_aliases=locale_aliases,
            )
            status = "✅ PASS" if result == expected else "❌ FAIL"
            print(f"[{status}] locale={locale!r:12} -> {result!r}")
            if result != expected:
                print(f"    Expected: {expected!r}")

        print("\nValidation complete.")


    if __name__ == "__main__":
        _test_locale_alias_fallback()




def _strip_display_node(cat_entry: Dict[str, Any]) -> Dict[str, Any]:
    """Return a shallow copy of catalog metadata excluding the 'display' node."""
    if not isinstance(cat_entry, dict):
        return {}
    out = dict(cat_entry)
    out.pop('display', None)
    return out


def _build_registry_from_normalized_games(games: Dict[str, Dict[str, Any]]) -> GameRegistry:
    """Build GameRegistry from normalized games dict.

    This is a small wiring helper so merge can be used even without registry.py loaders.
    """
    infos: List[GameInfo] = []
    for gid, meta in (games or {}).items():
        if not isinstance(meta, dict):
            continue
        game_id = meta.get('game_id') or gid
        display_name = meta.get('display_name')
        status = meta.get('status')
        if not isinstance(game_id, str) or not game_id:
            continue
        if not isinstance(display_name, str) or not display_name:
            display_name = str(game_id)
        if not isinstance(status, str) or not status:
            status = 'disabled'
        infos.append(GameInfo(game_id=str(game_id), display_name=str(display_name), status=str(status)))
    return GameRegistry(games=infos)  # type: ignore[arg-type]


__all__ = [
    'MergedCatalogItem',
    'merge_catalogs',
    'resolve_display_name_from_merge',
    'to_catalog_items',
    'load_and_merge',
]
'''

(pkg / 'catalog_merge.py').write_text(code, encoding='utf-8')

# Export from __init__.py (additive)
init_path = pkg / '__init__.py'
init_txt = init_path.read_text(encoding='utf-8') if init_path.exists() else ''
if 'catalog_merge' not in init_txt:
    init_txt += "\nfrom .catalog_merge import (\n    MergedCatalogItem,\n    merge_catalogs,\n    resolve_display_name_from_merge,\n    to_catalog_items,\n    load_and_merge,\n)\n"
    init_path.write_text(init_txt, encoding='utf-8')

print('Created rhythm_recommendation/phase7/catalog_merge.py')
