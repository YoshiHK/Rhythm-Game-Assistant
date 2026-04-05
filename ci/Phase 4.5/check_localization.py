
"""
CI Check: Localization Integrity (Phase 4.5)

This script validates that the translations/ folder is structurally
sound and compliant with Phase 4.5 localization rules.

Fail conditions are explicit and deterministic.
"""

import sys
from pathlib import Path
import json

ROOT = Path("translations")
META = ROOT / "_meta"

REQUIRED_META_FILES = [
    "locales.json",
    "locale_aliases.json",
    "sources.json",
]

REQUIRED_LOCALE_FILES = [
    "glossary.json",
    "locale_meta.json",
]

REQUIRED_VARIANTS = [
    "casual.json",
    "expert.json",
    "debug.json",
]

REQUIRED_TEMPLATE_DIRS = [
    "templates/narrative_v3/elements",
    "templates/narrative_v3/difficulty",
    "templates/narrative_v3/summaries",
]


def fail(msg: str):
    print(f"CI FAIL: {msg}")
    sys.exit(1)


# 1. README must exist
if not (ROOT / "README.md").exists():
    fail("translations/README.md is missing")


# 2. Meta files must exist
for f in REQUIRED_META_FILES:
    if not (META / f).exists():
        fail(f"translations/_meta/{f} is missing")


# 3. Load locales.json
locales = json.loads((META / "locales.json").read_text(encoding="utf-8"))
supported = set(locales.get("supported_locales", []))

if not supported:
    fail("supported_locales is empty")


# 4. Each locale folder must exist and be complete
for locale in supported:
    locale_dir = ROOT / locale
    if not locale_dir.exists():
        fail(f"Locale folder missing: {locale}")

    for f in REQUIRED_LOCALE_FILES:
        if not (locale_dir / f).exists():
            fail(f"{locale}/{f} is missing")

    for v in REQUIRED_VARIANTS:
        if not (locale_dir / "variants" / v).exists():
            fail(f"{locale}/variants/{v} is missing")

    for d in REQUIRED_TEMPLATE_DIRS:
        if not (locale_dir / d).exists():
            fail(f"{locale}/{d} is missing")


# 5. Alias targets must be valid locales
aliases = json.loads((META / "locale_aliases.json").read_text(encoding="utf-8"))
for alias, target in aliases.get("aliases", {}).items():
    if target not in supported:
        fail(f"Alias '{alias}' points to unsupported locale '{target}'")


print("CI PASS: Localization integrity verified")
