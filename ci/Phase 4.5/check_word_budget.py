"""CI Check: Word Budget Validation (Phase 4.5)

Validates that localized Narrative Module v3 template strings respect per-variant word budgets.

Design notes:
- Phase 4.5 is presentation-only; this is a structural policy check.
- Templates currently provide strings.default.text (baseline). Variants define max_words.
- If a template later adds variant-specific strings (e.g., strings.casual.text), this script
  will validate those too.

Word counting heuristic (deterministic):
- If the string contains whitespace-separated tokens, word_count = number of tokens.
- Otherwise (CJK/no-spaces), token_count = number of non-space, non-punctuation characters.
  This approximates "word" budget for languages without spaces.

Run:
  python ci/check_word_budget.py

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

# Basic punctuation set for CJK/no-space counting
PUNCT_RE = re.compile(r"[\s\u200b\u3000\.,!\?;:\\-—–\(\)\[\]\{\}<>\"'“”‘’、。！，？；：·…～~]+")


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


def count_units(text: str) -> int:
    """Deterministic word/unit counter."""
    if not isinstance(text, str):
        return 0
    stripped = text.strip()
    if not stripped:
        return 0
    # If contains whitespace between tokens, count tokens.
    if any(ch.isspace() for ch in stripped):
        tokens = [t for t in stripped.split() if t]
        return len(tokens)
    # No spaces: count non-punctuation characters as units.
    compact = PUNCT_RE.sub("", stripped)
    return len(compact)


def iter_variant_texts(template_obj: dict):
    """Yield (variant_id, text, path_hint). Defaults to 'default'."""
    strings = template_obj.get("strings")
    if not isinstance(strings, dict):
        return

    # Always check strings.default.text if present
    default = strings.get("default")
    if isinstance(default, dict) and isinstance(default.get("text"), str):
        yield ("default", default.get("text"), "strings.default.text")

    # Optional variant keys may be present in the future
    for variant_id in ("casual", "expert", "debug"):
        v = strings.get(variant_id)
        if isinstance(v, dict) and isinstance(v.get("text"), str):
            yield (variant_id, v.get("text"), f"strings.{variant_id}.text")


def main():
    locales_path = META / "locales.json"
    if not locales_path.exists():
        fail("translations/_meta/locales.json is missing")

    cfg = load_json(locales_path)
    supported = cfg.get("supported_locales")
    if not isinstance(supported, list) or not supported:
        fail("supported_locales is missing or empty")

    # Validate variants config exists per locale
    for loc in supported:
        loc_dir = ROOT / loc
        if not loc_dir.exists():
            fail(f"Locale folder missing: {loc}")

        variants_dir = loc_dir / "variants"
        if not variants_dir.exists():
            fail(f"Missing variants directory: {loc}/variants")

        variant_budgets = {}
        for vid in ("casual", "expert", "debug"):
            p = variants_dir / f"{vid}.json"
            if not p.exists():
                fail(f"Missing variant file: {loc}/variants/{vid}.json")
            vobj = load_json(p)
            rules = vobj.get("rules") if isinstance(vobj, dict) else None
            max_words = rules.get("max_words") if isinstance(rules, dict) else None
            if not isinstance(max_words, int) or max_words <= 0:
                fail(f"Invalid max_words in {loc}/variants/{vid}.json")
            variant_budgets[vid] = max_words

        # Templates
        t_files = list_template_files(loc_dir)
        if not t_files:
            fail(f"No templates found for locale: {loc}")

        for rel in t_files:
            tpath = loc_dir / rel
            tobj = load_json(tpath)
            if not isinstance(tobj, dict):
                fail(f"Template must be an object: {tpath}")

            # Validate any variant-specific strings against its budget
            for vid, text, hint in iter_variant_texts(tobj):
                if vid == "default":
                    # Default uses the strictest budget among casual/expert/debug, to keep baseline safe.
                    budget = min(variant_budgets.values())
                    budget_name = f"min(casual,expert,debug)={budget}"
                else:
                    budget = variant_budgets.get(vid)
                    budget_name = f"{vid}={budget}"

                units = count_units(text)
                if units > budget:
                    fail(
                        f"Word budget exceeded in {loc}/{rel} ({hint}). "
                        f"Units={units} Budget({budget_name})."
                    )

    print("CI PASS: Word budgets verified")


if __name__ == "__main__":
    main()
