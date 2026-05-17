#!/usr/bin/env python3
"""
Phase 4.5 Localization — Word/Unit Budget Check (CI-only, NON-RUNTIME)

Checks that localized template strings do not exceed per-variant budgets.

Template discovery (new layout):
- <locale>/chart_level/*.json
- <locale>/element_level/*.json
- <locale>/section_level/*.json
- <locale>/guidance_framing/*.json
- <locale>/tone/*.json

Budgets:
- Prefer per-locale budgets in <locale>/_meta/pack_version.json under:
    {
      "word_budgets": { "<variant>": <int>, ... },
      "unit_budgets": { "<variant>": <int>, ... }
    }
- If missing, fall back to deterministic defaults:
    - default: 40
    - other variants: 50
  (CJK/no-space languages use unit_budgets; others use word_budgets)

Exit codes:
- 0: pass
- 2: fail
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


LAYER_DIRS = ["chart_level", "element_level", "section_level", "guidance_framing", "tone"]

# basic punctuation removal for unit counting
PUNCT_RE = re.compile(r"[\s\u200b\u3000.,!?;:\-—–()\[\]{}<>\"'“”‘’、。！，？；：·…～~]+")


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    raise SystemExit(2)


def read_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def find_translations_root(cli_value: Optional[str]) -> Path:
    if cli_value:
        return Path(cli_value)
    candidates = [
        Path("translations"),
        Path("Phase 4.5 - Localization") / "translations",
        Path("Phase_4.5_Localization") / "translations",
    ]
    for c in candidates:
        if c.exists():
            return c
    fail("Cannot locate translations root (use --translations-root)")
    return Path(".")  # unreachable


def load_locales(translations_root: Path) -> Tuple[str, List[str]]:
    p = translations_root / "_meta" / "locales.json"
    if not p.exists():
        fail(f"Missing locales.json at {p}")
    obj = read_json(p)
    base = str(obj.get("base_locale", "en-US"))
    supported = obj.get("supported_locales", [])
    if not isinstance(supported, list) or not supported:
        fail("locales.json supported_locales missing/invalid")
    return base, [str(x) for x in supported]


def is_cjk_locale(locale: str) -> bool:
    # deterministic heuristic based on locale code
    return locale.startswith("zh") or locale.startswith("ja") or locale.startswith("ko")


def count_words(text: str) -> int:
    if not isinstance(text, str):
        return 0
    s = text.strip()
    if not s:
        return 0
    # whitespace token count
    tokens = [t for t in s.split() if t]
    return len(tokens)


def count_units(text: str) -> int:
    if not isinstance(text, str):
        return 0
    s = text.strip()
    if not s:
        return 0
    compact = PUNCT_RE.sub("", s)
    return len(compact)


def default_budget(variant: str, *, cjk: bool) -> int:
    # conservative defaults; adjust later if you introduce explicit budgets
    if variant == "default":
        return 40 if not cjk else 60
    return 50 if not cjk else 80


def load_budgets(locale_dir: Path) -> Tuple[Dict[str, int], Dict[str, int]]:
    """
    Returns (word_budgets, unit_budgets).
    Optional; if absent returns empty dicts.
    """
    pv = locale_dir / "_meta" / "pack_version.json"
    if not pv.exists():
        return {}, {}
    try:
        obj = read_json(pv)
    except Exception:
        return {}, {}
    wb = obj.get("word_budgets", {})
    ub = obj.get("unit_budgets", {})
    word_budgets = {str(k): int(v) for k, v in wb.items()} if isinstance(wb, dict) else {}
    unit_budgets = {str(k): int(v) for k, v in ub.items()} if isinstance(ub, dict) else {}
    return word_budgets, unit_budgets


def iter_templates(locale_dir: Path) -> List[Path]:
    files: List[Path] = []
    for layer in LAYER_DIRS:
        d = locale_dir / layer
        if d.exists():
            files.extend(sorted(d.glob("*.json"), key=lambda p: str(p)))
    return files


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--translations-root", type=str, default=None)
    args = ap.parse_args(argv)

    translations_root = find_translations_root(args.translations_root)
    _, locales = load_locales(translations_root)

    errors: List[str] = []

    for loc in locales:
        loc_dir = translations_root / loc
        if not loc_dir.exists():
            errors.append(f"[{loc}] Missing locale directory: {loc_dir}")
            continue

        cjk = is_cjk_locale(loc)
        word_budgets, unit_budgets = load_budgets(loc_dir)

        for f in iter_templates(loc_dir):
            try:
                obj = read_json(f)
            except Exception as e:
                errors.append(f"[{loc}] Invalid JSON: {f} ({e})")
                continue

            strings = obj.get("strings", {})
            if not isinstance(strings, dict):
                continue

            for variant, entry in strings.items():
                if not isinstance(entry, dict):
                    continue
                text = entry.get("text", "")
                if not isinstance(text, str):
                    continue

                if cjk:
                    budget = unit_budgets.get(variant, default_budget(variant, cjk=True))
                    units = count_units(text)
                    if units > budget:
                        errors.append(
                            f"[{loc}] {obj.get('template_id')}:{variant} exceeds unit budget "
                            f"{units}>{budget} file={f.name}"
                        )
                else:
                    budget = word_budgets.get(variant, default_budget(variant, cjk=False))
                    wc = count_words(text)
                    if wc > budget:
                        errors.append(
                            f"[{loc}] {obj.get('template_id')}:{variant} exceeds word budget "
                            f"{wc}>{budget} file={f.name}"
                        )

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        print(f"LOCALIZATION_WORD_BUDGET errors={len(errors)} warnings=0")
        return 2

    print("PASS: check_word_budget.py")
    print("LOCALIZATION_WORD_BUDGET errors=0 warnings=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())