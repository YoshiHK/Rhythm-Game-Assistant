"""CI Check: Narrative v3 Template Parity (Phase 4.5)

Validates that all locales listed in translations/_meta/locales.json have:
- identical template file set under templates/narrative_v3/
- each template JSON contains required Narrative Module v3 fields

This is a structural/policy check only (no semantic judgement of translations).

Run:
  python ci/check_template_parity.py

Exit code:
  0 on pass, 1 on failure.
"""

import json
import sys
from pathlib import Path

ROOT = Path("translations")
META = ROOT / "_meta"

BASE_LOCALE = None

REQUIRED_TEMPLATE_ROOT = Path("templates") / "narrative_v3"
REQUIRED_KEYS = ["template_id", "version", "strings"]


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


def validate_template_file(path: Path):
    data = load_json(path)
    if not isinstance(data, dict):
        fail(f"Template must be an object: {path}")
    for k in REQUIRED_KEYS:
        if k not in data:
            fail(f"Missing key '{k}' in template: {path}")
    if data.get("version") != "v3":
        fail(f"Template version must be 'v3' in: {path}")
    strings = data.get("strings")
    if not isinstance(strings, dict):
        fail(f"'strings' must be an object in: {path}")
    default = strings.get("default")
    if not isinstance(default, dict):
        fail(f"strings.default must be an object in: {path}")
    if "text" not in default or not isinstance(default.get("text"), str):
        fail(f"strings.default.text must be a string in: {path}")
    # placeholders may be missing if not used; if present, must be list
    if "placeholders" in default and not isinstance(default.get("placeholders"), list):
        fail(f"strings.default.placeholders must be a list when present in: {path}")


def main():
    # Preconditions
    if not META.exists():
        fail("translations/_meta is missing")
    locales_path = META / "locales.json"
    if not locales_path.exists():
        fail("translations/_meta/locales.json is missing")

    cfg = load_json(locales_path)
    supported = cfg.get("supported_locales")
    if not isinstance(supported, list) or not supported:
        fail("supported_locales is missing or empty")

    global BASE_LOCALE
    BASE_LOCALE = cfg.get("base_locale")
    if not isinstance(BASE_LOCALE, str) or not BASE_LOCALE:
        fail("base_locale is missing or invalid")
    if BASE_LOCALE not in supported:
        fail(f"base_locale '{BASE_LOCALE}' is not in supported_locales")

    base_dir = ROOT / BASE_LOCALE
    if not base_dir.exists():
        fail(f"Base locale folder missing: {BASE_LOCALE}")

    base_files = list_template_files(base_dir)
    if not base_files:
        fail(f"No templates found under base locale: {BASE_LOCALE}")

    # Validate base templates content
    for rel in base_files:
        validate_template_file(ROOT / BASE_LOCALE / rel)

    # Check parity + validate per-locale templates content
    for loc in supported:
        loc_dir = ROOT / loc
        if not loc_dir.exists():
            fail(f"Locale folder missing: {loc}")

        loc_files = list_template_files(loc_dir)
        if loc_files != base_files:
            # Provide minimal diff
            base_set = set(base_files)
            loc_set = set(loc_files)
            missing = sorted(base_set - loc_set)
            extra = sorted(loc_set - base_set)
            fail(
                f"Template parity mismatch for locale '{loc}'. "
                f"Missing: {missing[:10]} Extra: {extra[:10]}"
            )

        for rel in loc_files:
            validate_template_file(ROOT / loc / rel)

    print("CI PASS: Template parity and v3 structure verified")


if __name__ == "__main__":
    main()
