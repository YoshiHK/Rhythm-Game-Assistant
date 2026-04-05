"""CI Check: Token Count Integrity (Phase 4.5)

Asserts that localization does not change template token counts.

We treat "tokens" as variable placeholders used for template substitution.
This prevents translators from accidentally duplicating or dropping placeholders,
which would change runtime binding behavior.

Counted token forms:
- Curly placeholders: {name}
- Double-curly placeholders: {{name}}

Non-goals:
- Translation quality
- Word counts (covered by check_word_budget.py)
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

RE_CURLY = re.compile(r"\{[A-Za-z0-9_\.:-]+\}")
RE_DBL_CURLY = re.compile(r"\{\{[^{}]+\}\}")


def repo_root() -> Path:
    # ci/ is expected to live under repo root
    return Path(__file__).resolve().parents[1]


def translations_root(root: Path) -> Path:
    # Support both layouts:
    # 1) repo_root/translations
    # 2) repo_root/localization/translations
    cand1 = root / 'translations'
    cand2 = root / 'localization' / 'translations'
    if cand1.exists():
        return cand1
    if cand2.exists():
        return cand2
    return cand1


def iter_locale_dirs(troot: Path) -> Iterable[Path]:
    for p in sorted(troot.iterdir()):
        if not p.is_dir():
            continue
        if p.name.startswith('_'):
            continue
        yield p


def choose_base_locale(troot: Path) -> str:
    if (troot / 'en-US').is_dir():
        return 'en-US'
    meta = troot / '_meta' / 'locales.json'
    if meta.exists():
        try:
            data = json.loads(meta.read_text(encoding='utf-8'))
            for key in ('base_locale', 'default_locale', 'root_locale', 'fallback_root'):
                v = data.get(key)
                if isinstance(v, str) and (troot / v).is_dir():
                    return v
        except Exception:
            pass
    locs = [p.name for p in iter_locale_dirs(troot)]
    return locs[0] if locs else 'en-US'


def walk_strings(obj: Any, prefix: str = '') -> Iterable[Tuple[str, str]]:
    if isinstance(obj, str):
        yield (prefix or '$', obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            yield from walk_strings(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            p = f"{prefix}[{i}]" if prefix else f"[{i}]"
            yield from walk_strings(v, p)


def token_counter(text: str) -> Counter:
    tokens = []
    tokens.extend(RE_CURLY.findall(text))
    tokens.extend(RE_DBL_CURLY.findall(text))
    return Counter(tokens)


def collect_template_token_counts(locale_dir: Path) -> Dict[str, Counter]:
    out: Dict[str, Counter] = {}
    templates_dir = locale_dir / 'templates'
    if not templates_dir.exists():
        return out
    for fp in sorted(templates_dir.rglob('*.json')):
        rel = str(fp.relative_to(locale_dir))
        try:
            data = json.loads(fp.read_text(encoding='utf-8'))
        except Exception as exc:
            raise RuntimeError(f"Invalid JSON in {fp}: {exc}")
        c = Counter()
        for _, s in walk_strings(data):
            c.update(token_counter(s))
        out[rel] = c
    return out


def main() -> int:
    root = repo_root()
    troot = translations_root(root)
    if not troot.exists():
        print(f"CI FAIL: translations root not found at {troot}")
        return 1

    base = choose_base_locale(troot)
    base_dir = troot / base
    if not base_dir.is_dir():
        print(f"CI FAIL: base locale directory not found: {base_dir}")
        return 1

    base_map = collect_template_token_counts(base_dir)
    if not base_map:
        print(f"CI FAIL: no templates found under base locale: {base_dir / 'templates'}")
        return 1

    failures = 0
    for loc_dir in iter_locale_dirs(troot):
        if loc_dir.name == base:
            continue
        cur_map = collect_template_token_counts(loc_dir)
        for rel, base_counts in base_map.items():
            if rel not in cur_map:
                continue
            cur_counts = cur_map[rel]
            if cur_counts != base_counts:
                failures += 1
                missing = base_counts - cur_counts
                extra = cur_counts - base_counts
                print(f"CI FAIL: token counts differ for {rel} (base={base}, locale={loc_dir.name})")
                if missing:
                    print(f"  missing tokens: {dict(missing)}")
                if extra:
                    print(f"  extra tokens: {dict(extra)}")

    if failures:
        print(f"CI FAIL: token count integrity failed for {failures} template(s)")
        return 1

    print(f"CI PASS: token count integrity OK across locales (base={base})")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
