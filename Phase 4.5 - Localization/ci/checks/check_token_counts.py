#!/usr/bin/env python3
"""
Phase 4.5 Localization — Token Count Integrity Check (CI-only, NON-RUNTIME)

Purpose:
- Assert that placeholder token COUNTS do not drift across locales
- Coarse-grained: aggregates token counts per template across all variants

Tokens counted (as written in text):
- {name}
- {{name}}

Non-goals:
- Translation quality
- Word budget (handled by check_word_budget.py)
- Per-string parity (handled by check_token_parity_per_string.py)

Exit codes:
- 0: pass
- 2: fail
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


LAYER_DIRS = ["chart_level", "element_level", "section_level", "guidance_framing", "tone"]

RE_CURLY = re.compile(r"\{[A-Za-z0-9_.:-]+\}")
RE_DBL_CURLY = re.compile(r"\{\{\s*[A-Za-z0-9_.:-]+\s*\}\}")


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


def token_counter(text: str) -> Counter:
    c = Counter()
    c.update(RE_CURLY.findall(text or ""))
    c.update(RE_DBL_CURLY.findall(text or ""))
    return c


def collect_template_token_counts(locale_dir: Path) -> Dict[str, Counter]:
    """
    Returns:
    { template_id: Counter(token->count aggregated across all variants) }
    """
    out: Dict[str, Counter] = {}

    for layer in LAYER_DIRS:
        d = locale_dir / layer
        if not d.exists():
            continue
        for f in d.glob("*.json"):
            try:
                obj = read_json(f)
            except Exception:
                continue
            tid = obj.get("template_id")
            if not isinstance(tid, str) or not tid:
                continue
            strings = obj.get("strings", {})
            if not isinstance(strings, dict):
                continue

            agg = Counter()
            for _, entry in strings.items():
                if isinstance(entry, dict):
                    txt = entry.get("text", "")
                    if isinstance(txt, str):
                        agg += token_counter(txt)

            out[tid] = out.get(tid, Counter()) + agg

    return out


def diff_counters(base: Counter, other: Counter) -> Dict[str, Tuple[int, int]]:
    """
    Return tokens whose counts differ: {token: (base_count, other_count)}
    """
    out: Dict[str, Tuple[int, int]] = {}
    keys = set(base.keys()) | set(other.keys())
    for k in sorted(keys):
        bc = int(base.get(k, 0))
        oc = int(other.get(k, 0))
        if bc != oc:
            out[k] = (bc, oc)
    return out


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--translations-root", type=str, default=None)
    args = ap.parse_args(argv)

    translations_root = find_translations_root(args.translations_root)
    base_locale, locales = load_locales(translations_root)

    base_dir = translations_root / base_locale
    if not base_dir.exists():
        fail(f"Base locale directory missing: {base_dir}")

    base_counts = collect_template_token_counts(base_dir)

    errors: List[str] = []
    for loc in locales:
        loc_dir = translations_root / loc
        if not loc_dir.exists():
            errors.append(f"[{loc}] Missing locale directory: {loc_dir}")
            continue

        cur_counts = collect_template_token_counts(loc_dir)

        # compare only templates present in base (parity handled elsewhere)
        for tid, bc in base_counts.items():
            oc = cur_counts.get(tid, Counter())
            diffs = diff_counters(bc, oc)
            if diffs:
                errors.append(f"[{loc}] Token count drift in template '{tid}': {diffs}")

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        print(f"LOCALIZATION_TOKEN_COUNTS errors={len(errors)} warnings=0")
        return 2

    print("PASS: check_token_counts.py")
    print("LOCALIZATION_TOKEN_COUNTS errors=0 warnings=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())