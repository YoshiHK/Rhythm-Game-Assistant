
"""
CI Check: Narrative v3 Template Parity (Phase 4 template setsCI Check: Narrative v3 Template Parity (Phase 4.5)
- Validate Narrative v3 template schema (structure only)

Non-goals:
- Translation quality
- Text content comparison
"""

from pathlib import Path
import json
import sys


REQUIRED_KEYS = ["template_id", "version", "strings"]


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    sys.exit(1)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def list_templates(locale_dir: Path) -> set[str]:
    base = locale_dir / "templates" / "narrative_v3"
    if not base.exists():
        fail(f"Missing templates/narrative_v3 in {locale_dir.name}")
    return {
        str(p.relative_to(locale_dir))
        for p in base.rglob("*.json")
        if p.is_file()
    }


def validate_template_schema(path: Path) -> None:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"Invalid JSON: {path}: {e}")

    if not isinstance(obj, dict):
        fail(f"Template must be an object: {path}")

    for k in REQUIRED_KEYS:
        if k not in obj:
            fail(f"Missing key '{k}' in template: {path}")

    if obj.get("version") != "v3":
        fail(f"Template version must be 'v3': {path}")

    strings = obj.get("strings")
    if not isinstance(strings, dict):
        fail(f"strings must be object: {path}")

    default = strings.get("default")
    if not isinstance(default, dict):
        fail(f"strings.default must be object: {path}")

    if not isinstance(default.get("text"), str):
        fail(f"strings.default.text must be string: {path}")

    if "placeholders" in default and not isinstance(default["placeholders"], list):
        fail(f"strings.default.placeholders must be list: {path}")


def main() -> int:
    root = repo_root()
    translations = root / "translations"
    meta = translations / "_meta"

    locales = json.loads((meta / "locales.json").read_text(encoding="utf-8"))
    supported = locales.get("supported_locales", [])

    base_locale = supported[0]
    base_set = list_templates(translations / base_locale)

    for locale in supported:
        locale_dir = translations / locale
        cur_set = list_templates(locale_dir)

        if cur_set != base_set:
            fail(f"Template set mismatch in locale: {locale}")

        for rel in cur_set:
            validate_template_schema(locale_dir / rel)

    print("CI PASS: Template parity and schema validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
