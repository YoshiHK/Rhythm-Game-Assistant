#!/usr/bin/env python3
"""
Phase 4.5 Localization — Locale Pack Integrity Check (CI-only, NON-RUNTIME)

Scope (Pack completeness, not semantics):
- translations/_meta/locales.json must exist
- translations/_meta/template_registry.json must exist
- Each locale directory must exist
- Each locale must contain _meta/{locale_meta.json, glossary.json, pack_version.json, debug.json}
- Each locale must contain every template_id listed in template_registry.json
- Each template must satisfy minimal Narrative v3 schema:
  - template_id (str)
  - version == "v3"
  - strings.default.text (str)

Non-goals:
- Placeholder parity (handled by check_placeholder_integrity.py)
- Variant parity (handled by check_template_parity.py)
- Token/word budgets (handled by other checks)

Exit codes:
- 0 pass
- 2 fail
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


LAYER_DIRS = ["chart_level", "element_level", "section_level", "guidance_framing", "tone"]
REQUIRED_LOCALE_META_FILES = ["locale_meta.json", "glossary.json", "pack_version.json", "debug.json"]


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


def load_registry(translations_root: Path) -> Dict[str, List[str]]:
    p = translations_root / "_meta" / "template_registry.json"
    if not p.exists():
        fail(f"Missing template_registry.json at {p}")
    obj = read_json(p)
    reg: Dict[str, List[str]] = {}
    for k in ["chart_level", "element_level", "section_level", "guidance_framing", "tone"]:
        v = obj.get(k, [])
        reg[k] = [str(x) for x in v] if isinstance(v, list) else []
    return reg


def discover_templates_by_id(locale_dir: Path) -> Dict[str, Path]:
    """
    New layout: <locale>/<layer>/*.json with template_id inside.
    """
    out: Dict[str, Path] = {}
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
            if isinstance(tid, str) and tid:
                # deterministic pick if duplicates
                if tid not in out or str(f) < str(out[tid]):
                    out[tid] = f
    return out


def validate_template_schema(locale: str, tid: str, path: Path) -> None:
    try:
        obj = read_json(path)
    except Exception as e:
        fail(f"[{locale}] Invalid JSON for {tid}: {path} ({e})")

    if obj.get("template_id") != tid:
        fail(f"[{locale}] template_id mismatch in {path}: {obj.get('template_id')} != {tid}")

    if obj.get("version") != "v3":
        fail(f"[{locale}] {tid} version must be 'v3' in {path}")

    strings = obj.get("strings")
    if not isinstance(strings, dict) or "default" not in strings:
        fail(f"[{locale}] {tid} missing strings.default in {path}")

    default = strings.get("default", {})
    if not isinstance(default, dict) or not isinstance(default.get("text"), str):
        fail(f"[{locale}] {tid} strings.default.text missing/invalid in {path}")


def validate_locale_meta(locale: str, locale_dir: Path) -> None:
    meta_dir = locale_dir / "_meta"
    if not meta_dir.exists():
        fail(f"[{locale}] Missing _meta/ directory: {meta_dir}")
    for fname in REQUIRED_LOCALE_META_FILES:
        if not (meta_dir / fname).exists():
            fail(f"[{locale}] Missing {fname} in {meta_dir}")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--translations-root", type=str, default=None)
    args = ap.parse_args(argv)

    translations_root = find_translations_root(args.translations_root)
    base_locale, locales = load_locales(translations_root)
    registry = load_registry(translations_root)

    required_ids: List[str] = (
        registry["chart_level"]
        + registry["element_level"]
        + registry["section_level"]
        + registry["guidance_framing"]
        + registry["tone"]
    )

    # base locale existence
    base_dir = translations_root / base_locale
    if not base_dir.exists():
        fail(f"Base locale directory missing: {base_dir}")

    # Validate each locale
    for loc in locales:
        loc_dir = translations_root / loc
        if not loc_dir.exists():
            fail(f"[{loc}] Missing locale directory: {loc_dir}")

        validate_locale_meta(loc, loc_dir)

        found = discover_templates_by_id(loc_dir)
        missing = [tid for tid in required_ids if tid not in found]
        if missing:
            fail(f"[{loc}] Missing templates: {missing}")

        # schema sanity on required templates
        for tid in required_ids:
            validate_template_schema(loc, tid, found[tid])

    print("PASS: check_pack_integrity.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())