"""Asserts that localization does not change template token counts.

We treat "tokens" as placeholder markers used for template substitution.
This prevents translators from accidentally duplicating or dropping placeholders,
which would change runtime binding behavior.

Counted token forms (as written in text):
- Curly placeholders: {name}
- Double-curly placeholders: {{name}}

Non-goals:
- Translation quality
- Word budget (covered by check_word_budget.py)
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple


RE_CURLY = re.compile(r"\{[A-Za-z0-9_.:-]+\}")
RE_DBL_CURLY = re.compile(r"\{\{\s*[A-Za-z0-9_.:-]+\s*\}\}")


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    sys.exit(1)


def repo_root() -> Path:
    # Works for both repo/ci/* and Phase_4.5_Localization/ci/* layouts
    return Path(__file__).resolve().parents[2]


def translations_root(root: Path) -> Path:
    candidates = [
        root / "translations",
        root / "Phase_4.5_Localization" / "translations",
        root / "Phase 4.5 - Localization" / "translations",
        root / "localization" / "translations",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


def iter_locale_dirs(troot: Path) -> Iterable[Path]:
    for p in sorted(troot.iterdir()):
        if p.is_dir() and not p.name.startswith("_"):
            yield p


def choose_base_locale(troot: Path) -> str:
    # Prefer explicit en-US
    if (troot / "en-US").is_dir():
        return "en-US"

    meta = troot / "_meta" / "locales.json"
    if meta.exists():
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
            supported = data.get("supported_locales") or data.get("supportedLocales")
            if isinstance(supported, list) and supported:
                v = supported[0]
                if isinstance(v, str) and (troot / v).is_dir():
                    return v
            for key in ("base_locale", "default_locale", "root_locale", "fallback_root"):
                v = data.get(key)
                if isinstance(v, str) and (troot / v).is_dir():
                    return v
        except Exception:
            pass

    locs = [p.name for p in iter_locale_dirs(troot)]
    return locs[0] if locs else "en-US"


def walk_strings(obj: Any, prefix: str = "$") -> Iterable[Tuple[str, str]]:
    if isinstance(obj, str):
        yield (prefix, obj)
        return

    if isinstance(obj, dict):
        for k, v in obj.items():
            kp = f"{prefix}.{k}"
            yield from walk_strings(v, kp)
        return

    if isinstance(obj, list):
        for i, v in enumerate(obj):
            kp = f"{prefix}[{i}]"
            yield from walk_strings(v, kp)
        return


def token_counter(text: str) -> Counter:
    c = Counter()
    c.update(RE_CURLY.findall(text))
    c.update(RE_DBL_CURLY.findall(text))
    return c


def collect_template_token_counts(locale_dir: Path) -> Dict[str, Counter]:
    out: Dict[str, Counter] = {}
    templates_dir = locale_dir / "templates"
    if not templates_dir.exists():
        return out

    for fp in sorted(templates_dir.rglob("*.json")):
        rel = fp.relative_to(locale_dir).as_posix()
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"Invalid JSON in {locale_dir.name}/{rel}: {exc}")

        c = Counter()
        for _, s in walk_strings(data):
            c.update(token_counter(s))
        out[rel] = c

    return out


def diff_counters(a: Counter, b: Counter) -> Dict[str, int]:
    # returns items where counts differ (b - a)
    out: Dict[str, int] = {}
    keys = set(a.keys()) | set(b.keys())
    for k in sorted(keys):
        da = int(a.get(k, 0))
        db = int(b.get(k, 0))
        if da != db:
            out[k] = db - da
    return out


def main() -> int:
    root = repo_root()
    troot = translations_root(root)
    if not troot.exists():
        fail(f"translations root not found (checked common locations) under: {root}")

    base = choose_base_locale(troot)
    base_dir = troot / base
    if not base_dir.exists():
        fail(f"Base locale directory not found: {base_dir}")

    base_counts = collect_template_token_counts(base_dir)
    if not base_counts:
        fail(f"No templates found under base locale: {base}/templates")

    locales = [p.name for p in iter_locale_dirs(troot)]
    for loc in locales:
        if loc == base:
            continue
        loc_dir = troot / loc
        cur_counts = collect_template_token_counts(loc_dir)

        # Ensure same template set
        if set(cur_counts.keys()) != set(base_counts.keys()):
            missing = sorted(set(base_counts.keys()) - set(cur_counts.keys()))
            extra = sorted(set(cur_counts.keys()) - set(base_counts.keys()))
            fail(f"Template set mismatch for locale {loc}. Missing={missing} Extra={extra}")

        # Compare per template counter
        for rel in sorted(base_counts.keys()):
            d = diff_counters(base_counts[rel], cur_counts[rel])
            if d:
                fail(f"Token count mismatch: locale={loc} template={rel} diff(b-base)={d}")

    print("CI PASS: Token count integrity verified across locales")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
CI Check: Token Count Integrity (Phase 4.5)

