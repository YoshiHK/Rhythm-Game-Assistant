#!/usr/bin/env python3
"""
Phase 4.5 Localization — Template Parity & Schema Check (CI-only, NON-RUNTIME)

Checks:
- Every supported locale contains the same set of template files (by template_id), as defined in
  translations/_meta/template_registry.json
- Each required template file conforms to Narrative v3 schema:
  - template_id (str)
  - version == "v3"
  - strings is dict
  - strings.default.text exists (str)
  - placeholders is list if present
- Variants (keys under strings) must match base locale (en-US) per template_id

Exit codes:
- 0: pass
- 2: fail
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


LAYER_DIRS = ["chart_level", "element_level", "section_level", "guidance_framing", "tone"]


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
    New layout:
      <locale>/<layer>/*.json where each file contains template_id
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
                if tid not in out or str(f) < str(out[tid]):
                    out[tid] = f
    return out


def validate_schema(locale: str, tid: str, path: Path) -> Dict[str, Any]:
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

    # placeholders must be list if present
    for vk, vv in strings.items():
        if not isinstance(vv, dict):
            fail(f"[{locale}] {tid}:{vk} must be an object in {path}")
        if "placeholders" in vv and not isinstance(vv.get("placeholders"), list):
            fail(f"[{locale}] {tid}:{vk} placeholders must be a list in {path}")

    return obj


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

    # Load base locale as reference for variant parity
    base_dir = translations_root / base_locale
    if not base_dir.exists():
        fail(f"Base locale directory missing: {base_dir}")

    base_map = discover_templates_by_id(base_dir)
    for tid in required_ids:
        if tid not in base_map:
            fail(f"[{base_locale}] Missing required template {tid} (file not found under layer folders)")
    base_objs = {tid: validate_schema(base_locale, tid, base_map[tid]) for tid in required_ids}

    # Validate each locale for file-set parity + variant parity
    for loc in locales:
        loc_dir = translations_root / loc
        if not loc_dir.exists():
            fail(f"[{loc}] Missing locale directory: {loc_dir}")

        loc_map = discover_templates_by_id(loc_dir)

        # Required templates must exist
        missing = [tid for tid in required_ids if tid not in loc_map]
        if missing:
            fail(f"[{loc}] Missing templates: {missing}")

        # Schema + variant parity
        for tid in required_ids:
            obj = validate_schema(loc, tid, loc_map[tid])

            b_strings = base_objs[tid].get("strings", {})
            c_strings = obj.get("strings", {})
            if set(c_strings.keys()) != set(b_strings.keys()):
                missing_vk = sorted(set(b_strings.keys()) - set(c_strings.keys()))
                extra_vk = sorted(set(c_strings.keys()) - set(b_strings.keys()))
                if missing_vk:
                    fail(f"[{loc}] {tid} missing variant(s) {missing_vk} (base has it)")
                if extra_vk:
                    fail(f"[{loc}] {tid} has extra variant(s) {extra_vk} (not in base)")
            # placeholders parity is handled by check_placeholder_integrity.py (separate check)

        # Warn on extra templates not in registry
        extra = sorted(set(loc_map.keys()) - set(required_ids))
        if extra:
            print(f"WARN[{loc}]: Extra templates not in registry: {extra}")

    print("PASS: check_template_parity.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())