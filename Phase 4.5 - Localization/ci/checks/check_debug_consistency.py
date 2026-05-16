#!/usr/bin/env python3
"""
Phase 4.5 Localization — Debug Consistency Check (CI-only, NON-RUNTIME)

Enforces:
- Every supported locale has a debug.json (in one of the supported locations)
- debug.json content is identical across all locales (after canonical JSON normalization)

Supported locations per-locale (checked in order):
1) <locale>/debug/debug.json            (new layered layout)
2) <locale>/_meta/debug.json            (new meta layout)
3) <locale>/variants/debug.json         (legacy layout)

Exit codes:
- 0: pass
- 2: fail

Usage:
  python "Phase 4.5 - Localization/ci/checks/check_debug_consistency.py" \
    --translations-root "Phase 4.5 - Localization/translations"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_json(obj: Dict[str, Any]) -> str:
    # Deterministic serialization (stable ordering)
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def find_translations_root(cli_value: Optional[str]) -> Path:
    if cli_value:
        return Path(cli_value)
    # common fallbacks
    candidates = [
        Path("translations"),
        Path("Phase 4.5 - Localization") / "translations",
        Path("Phase_4.5_Localization") / "translations",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError("Cannot locate translations root (use --translations-root).")


def load_supported_locales(translations_root: Path) -> Tuple[str, List[str]]:
    meta_locales = translations_root / "_meta" / "locales.json"
    if not meta_locales.exists():
        raise FileNotFoundError(f"Missing locales.json at: {meta_locales}")
    obj = read_json(meta_locales)
    base = str(obj.get("base_locale", "en-US"))
    supported = obj.get("supported_locales")
    if not isinstance(supported, list) or not supported:
        raise ValueError("supported_locales missing or invalid in locales.json")
    return base, [str(x) for x in supported]


def locate_debug_file(locale_dir: Path) -> Optional[Path]:
    candidates = [
        locale_dir / "debug" / "debug.json",
        locale_dir / "_meta" / "debug.json",
        locale_dir / "variants" / "debug.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--translations-root", type=str, default=None)
    args = ap.parse_args()

    try:
        translations_root = find_translations_root(args.translations_root)
        base_locale, locales = load_supported_locales(translations_root)
    except Exception as e:
        print(f"ERROR: {e}")
        print("LOCALIZATION_DEBUG_CONSISTENCY errors=1 warnings=0")
        return 2

    errors: List[str] = []

    # Load base debug reference (prefer base locale if present; otherwise first locale)
    base_dir = translations_root / base_locale
    if not base_dir.exists():
        errors.append(f"Missing base locale directory: {base_dir}")
        ref_locale = locales[0]
    else:
        ref_locale = base_locale

    ref_path = locate_debug_file(translations_root / ref_locale)
    if ref_path is None:
        errors.append(f"Missing debug.json for reference locale '{ref_locale}'")
        # still continue to report all missing
        ref_canon = None
    else:
        try:
            ref_canon = canonical_json(read_json(ref_path))
        except Exception as e:
            errors.append(f"Invalid JSON in reference debug.json ({ref_path}): {e}")
            ref_canon = None

    # Validate each locale
    for loc in locales:
        loc_dir = translations_root / loc
        if not loc_dir.exists():
            errors.append(f"[{loc}] Missing locale directory: {loc_dir}")
            continue

        dbg_path = locate_debug_file(loc_dir)
        if dbg_path is None:
            errors.append(f"[{loc}] Missing debug.json (expected in debug/ or _meta/ or variants/)")
            continue

        try:
            canon = canonical_json(read_json(dbg_path))
        except Exception as e:
            errors.append(f"[{loc}] Invalid JSON in debug.json ({dbg_path}): {e}")
            continue

        if ref_canon is not None and canon != ref_canon:
            errors.append(
                f"[{loc}] debug.json differs from reference '{ref_locale}'. "
                f"File={dbg_path}"
            )

    # Print details deterministically
    for msg in sorted(errors):
        print(f"ERROR: {msg}")

    err_count = len(errors)
    print(f"LOCALIZATION_DEBUG_CONSISTENCY errors={err_count} warnings=0")
    return 2 if err_count else 0


if __name__ == "__main__":
    raise SystemExit(main())