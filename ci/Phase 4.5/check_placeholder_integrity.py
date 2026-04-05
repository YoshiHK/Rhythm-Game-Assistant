"""CI Check: Placeholder Integrity (Phase 4.5)

Validates that placeholders are preserved across locales for Narrative Module v3 templates.

What it checks (structural only):
1) For every template JSON under <locale>/templates/narrative_v3/**/*.json:
   - Compare placeholders declared in strings.default.placeholders against the base locale.
2) Additionally, detect inline placeholders in strings.default.text using {{placeholder_name}} pattern
   (common i18n placeholder style) and compare sets against the base locale.

This check does NOT evaluate translation quality or meaning.

Run:
  python ci/check_placeholder_integrity.py

Exit code:
  0 on pass, 1 on failure.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path("translations")
META = ROOT / "_meta"
REQUIRED_TEMPLATE_ROOT = Path("templates") / "narrative_v3"

INLINE_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_\-\.]+)\s*\}\}")


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    sys.exit(1)


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"Failed to parse JSON: {path} ({e})")


def list_template_files(locale_dir: Path):
    base = locale_dir / REQUIRED_TEMPLATE_ROOT
    if not base.exists():
        fail(f"Missing template root: {base}")
    files = []
    for p in base.rglob("*.json"):
        if p.is_file():
            files.append(p.relative_to(locale_dir).as_posix())
    return sorted(files)


def extract_placeholders(template_obj: dict):
    """Return (declared_placeholders_set, inline_placeholders_set)."""
    strings = template_obj.get("strings")
    if not isinstance(strings, dict):
        return set(), set()
    default = strings.get("default")
    if not isinstance(default, dict):
        return set(), set()

    # Declared placeholders list
    declared = default.get("placeholders")
    if declared is None:
        declared_set = set()
    elif isinstance(declared, list):
        declared_set = set(str(x) for x in declared)
    else:
        # invalid type caught elsewhere; treat as mismatch
        declared_set = set(["__INVALID_TYPE__"])

    # Inline placeholders in text
    text = default.get("text")
    if isinstance(text, str):
        inline_set = set(INLINE_PLACEHOLDER_RE.findall(text))
    else:
        inline_set = set()

    return declared_set, inline_set


def main():
    locales_path = META / "locales.json"
    if not locales_path.exists():
        fail("translations/_meta/locales.json is missing")

    cfg = load_json(locales_path)
    supported = cfg.get("supported_locales")
    if not isinstance(supported, list) or not supported:
        fail("supported_locales is missing or empty")

    base_locale = cfg.get("base_locale")
    if not isinstance(base_locale, str) or not base_locale:
        fail("base_locale is missing or invalid")
    if base_locale not in supported:
        fail(f"base_locale '{base_locale}' is not in supported_locales")

    base_dir = ROOT / base_locale
    if not base_dir.exists():
        fail(f"Base locale folder missing: {base_locale}")

    # Template list should already be parity-checked, but we don't assume it.
    base_files = list_template_files(base_dir)
    if not base_files:
        fail(f"No templates found under base locale: {base_locale}")

    # Build base placeholder registry
    base_registry = {}
    for rel in base_files:
        path = ROOT / base_locale / rel
        obj = load_json(path)
        if not isinstance(obj, dict):
            fail(f"Template must be an object: {path}")
        declared, inline = extract_placeholders(obj)
        base_registry[rel] = {
            "declared": declared,
            "inline": inline,
        }

    # Compare each locale to base
    for loc in supported:
        loc_dir = ROOT / loc
        if not loc_dir.exists():
            fail(f"Locale folder missing: {loc}")

        loc_files = list_template_files(loc_dir)
        # If file sets differ, parity check should catch; we fail here too.
        if set(loc_files) != set(base_files):
            fail(f"Template set mismatch for locale '{loc}'. Run check_template_parity.py first.")

        for rel in base_files:
            base_ph = base_registry[rel]
            loc_path = ROOT / loc / rel
            obj = load_json(loc_path)
            if not isinstance(obj, dict):
                fail(f"Template must be an object: {loc_path}")

            declared, inline = extract_placeholders(obj)

            if declared != base_ph["declared"]:
                fail(
                    f"Declared placeholders mismatch in '{rel}' for locale '{loc}'. "
                    f"Base={sorted(base_ph['declared'])} Loc={sorted(declared)}"
                )

            if inline != base_ph["inline"]:
                fail(
                    f"Inline placeholders mismatch in '{rel}' for locale '{loc}'. "
                    f"Base={sorted(base_ph['inline'])} Loc={sorted(inline)}"
                )

    print("CI PASS: Placeholder integrity verified across locales")


if __name__ == "__main__":
    main()
