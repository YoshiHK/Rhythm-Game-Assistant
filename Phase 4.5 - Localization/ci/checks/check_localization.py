"""
CI Check: Localization Integrity (Phase 4.5)

Purpose:
- Validate that the translationsals:- Validate that the translations/ directory is structurally complete
- Translation quality
- Linguistic correctness
- Narrative semantics
"""

from pathlib import Path
import json
import sys


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    sys.exit(1)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main() -> int:
    root = repo_root()
    translations = root / "translations"
    meta = translations / "_meta"

    if not translations.exists():
        fail("translations/ directory is missing")

    if not (translations / "README.md").exists():
        fail("translations/README.md is missing")

    required_meta = [
        "locales.json",
        "locale_aliases.json",
        "sources.json",
    ]

    for f in required_meta:
        p = meta / f
        if not p.exists():
            fail(f"translations/_meta/{f} is missing")

    try:
        locales = json.loads((meta / "locales.json").read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"Failed to parse locales.json: {e}")

    supported = set(locales.get("supported_locales", []))
    if not supported:
        fail("supported_locales is empty in locales.json")

    for locale in supported:
        loc_dir = translations / locale
        if not loc_dir.exists():
            fail(f"Locale directory missing: translations/{locale}")

        for required in ["glossary", "variants", "templates", "locale_meta.json"]:
            if not (loc_dir / required).exists():
                fail(f"Missing {required} in locale: {locale}")

    print("CI PASS: Localization directory integrity verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
- Enforce Phase 4.5 localization contract (structure only)

