"""
CI Check: Placeholder Integrity (Phase 4.5)

Purpose:
- Ensure placeholders are preserved across locales
- Prevent runtime binding breakage due to missing/extra placeholders

Non-goals:
- Translation quality
- Linguistic correctness
"""

from pathlib import Path
import json
import re
import sys


INLINE_RE = re.compile(r"{{\s*([a-zA-Z0-9_.:-]+)\s*}}")


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    sys.exit(1)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def extract_placeholders(obj: dict) -> set[str]:
    out = set()
    strings = obj.get("strings", {})
    default = strings.get("default", {})

    declared = default.get("placeholders", [])
    if isinstance(declared, list):
        out.update(str(p) for p in declared)

    text = default.get("text")
    if isinstance(text, str):
        out.update(INLINE_RE.findall(text))

    return out


def main() -> int:
    root = repo_root()
    translations = root / "translations"
    meta = translations / "_meta"

    locales = json.loads((meta / "locales.json").read_text(encoding="utf-8"))
    supported = locales.get("supported_locales", [])

    base_locale = supported[0]
    base_dir = translations / base_locale
    base_templates = list((base_dir / "templates" / "narrative_v3").rglob("*.json"))

    base_map = {}
    for fp in base_templates:
        obj = json.loads(fp.read_text(encoding="utf-8"))
        base_map[str(fp.relative_to(base_dir))] = extract_placeholders(obj)

    for locale in supported:
        loc_dir = translations / locale
        for rel, expected in base_map.items():
            path = loc_dir / rel
            if not path.exists():
                fail(f"Missing template {rel} in locale {locale}")

            obj = json.loads(path.read_text(encoding="utf-8"))
            found = extract_placeholders(obj)

            if found != expected:
                fail(
                    f"Placeholder mismatch in {locale}/{rel}: "
                    f"expected={sorted(expected)}, found={sorted(found)}"
                )

    print("CI PASS: Placeholder integrity verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())