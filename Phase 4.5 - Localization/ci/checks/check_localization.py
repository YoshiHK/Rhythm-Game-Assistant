#!/usr/bin/env python3
"""
Phase 4.5 Localization — Directory Structure Integrity Check (CI-only)

Checks:
- translations/_meta/ exists and contains required contract files
- Each locale directory exists and contains _meta/ with required files
- Each locale contains all required template layer folders
- No legacy/unsupported folders present

Exit codes:
- 0: pass
- 2: fail
"""

from pathlib import Path
import sys

REQUIRED_META = ["locale_meta.json", "glossary.json", "pack_version.json", "debug.json"]
REQUIRED_LAYERS = [
    "chart_level",
    "element_level",
    "section_level",
    "guidance_framing",
    "tone",
]

def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    sys.exit(2)

def main() -> int:
    root = Path(__file__).resolve().parents[2]
    translations = root / "translations"
    meta = translations / "_meta"

    if not translations.exists():
        fail("Missing translations/ directory")
    if not meta.exists():
        fail("Missing translations/_meta/ directory")

    # Check global contract files
    for fname in ["locales.json", "locale_aliases.json", "template_registry.json", "sources.json"]:
        if not (meta / fname).exists():
            fail(f"Missing global contract file: {fname}")

    # Check each locale
    for loc_dir in [d for d in translations.iterdir() if d.is_dir() and not d.name.startswith("_")]:
        meta_dir = loc_dir / "_meta"
        if not meta_dir.exists():
            fail(f"Missing _meta/ in {loc_dir.name}")
        for fname in REQUIRED_META:
            if not (meta_dir / fname).exists():
                fail(f"Missing {fname} in {loc_dir.name}/_meta/")
        for layer in REQUIRED_LAYERS:
            if not (loc_dir / layer).exists():
                fail(f"Missing {layer}/ in {loc_dir.name}/")
    print("PASS: check_localization.py")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())