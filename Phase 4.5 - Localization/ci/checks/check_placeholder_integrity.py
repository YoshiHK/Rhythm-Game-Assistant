#!/usr/bin/env python3
"""
Phase 4.5 Localization — Placeholder Integrity Check (CI-only)

Checks:
- All templates in all locales preserve placeholder sets per variant
- Placeholders must match base locale (en-US) exactly

Exit codes:
- 0: pass
- 2: fail
"""

from pathlib import Path
import json
import sys

def extract_placeholders(strings: dict) -> dict:
    out = {}
    for variant, entry in strings.items():
        ph = entry.get("placeholders", [])
        out[variant] = tuple(sorted(ph))
    return out

def main() -> int:
    root = Path(__file__).resolve().parents[2]
    translations = root / "translations"
    meta = translations / "_meta"
    locales = json.loads((meta / "locales.json").read_text(encoding="utf-8"))
    base_locale = locales.get("base_locale", "en-US")
    supported = locales.get("supported_locales", [])
    errors = []

    # Load base locale templates
    base_dir = translations / base_locale
    base_templates = {}
    for layer in ["chart_level", "element_level", "section_level", "guidance_framing", "tone"]:
        layer_dir = base_dir / layer
        if not layer_dir.exists():
            continue
        for f in layer_dir.glob("*.json"):
            obj = json.loads(f.read_text(encoding="utf-8"))
            base_templates[obj["template_id"]] = extract_placeholders(obj["strings"])

    # Check all locales
    for loc in supported:
        if loc == base_locale:
            continue
        loc_dir = translations / loc
        for layer in ["chart_level", "element_level", "section_level", "guidance_framing", "tone"]:
            layer_dir = loc_dir / layer
            if not layer_dir.exists():
                continue
            for f in layer_dir.glob("*.json"):
                obj = json.loads(f.read_text(encoding="utf-8"))
                tid = obj["template_id"]
                if tid not in base_templates:
                    continue
                cur_ph = extract_placeholders(obj["strings"])
                base_ph = base_templates[tid]
                for variant, ph in base_ph.items():
                    if variant not in cur_ph:
                        errors.append(f"{loc}:{tid} missing variant '{variant}' (base has it)")
                    elif cur_ph[variant] != ph:
                        errors.append(f"{loc}:{tid}:{variant} placeholders {cur_ph[variant]} != base {ph}")

    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        sys.exit(2)
    print("PASS: check_placeholder_integrity.py")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())