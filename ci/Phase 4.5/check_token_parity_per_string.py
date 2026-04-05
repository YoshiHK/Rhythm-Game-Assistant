"""CI Check: Per-string Token Parity (Phase 4.5)

Assert that localization does not change placeholder token counts *per string field*.

Why
---
Placeholder integrity checks usually ensure placeholders are present. This check is stricter:
- compares token multiplicity (no duplicates / no drops)
- performs comparison at each string leaf path in every template JSON

Token forms counted
-------------------
- Curly placeholders: {name}
- Double-curly placeholders: {{name}}

Notes
-----
- Non-semantic: does not judge translation quality.
- Word budgets are enforced elsewhere.
- Template file parity / basic structure is enforced elsewhere.

Exit codes
----------
0 = pass
1 = fail
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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _translations_root(root: Path) -> Path:
    cand1 = root / 'translations'
    cand2 = root / 'localization' / 'translations'
    if cand1.exists():
        return cand1
    if cand2.exists():
        return cand2
    return cand1


def _iter_locale_dirs(troot: Path) -> Iterable[Path]:
    for p in sorted(troot.iterdir()):
        if not p.is_dir():
            continue
        if p.name.startswith('_'):
            continue
        yield p


def _choose_base_locale(troot: Path) -> str:
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
    locs = [p.name for p in _iter_locale_dirs(troot)]
    return locs[0] if locs else 'en-US'


def _walk_strings(obj: Any, prefix: str = '') -> Iterable[Tuple[str, str]]:
    if isinstance(obj, str):
        yield (prefix or '$', obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            yield from _walk_strings(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            p = f"{prefix}[{i}]" if prefix else f"[{i}]"
            yield from _walk_strings(v, p)


def _token_counter(text: str) -> Counter:
    tokens = []
    tokens.extend(RE_CURLY.findall(text))
    tokens.extend(RE_DBL_CURLY.findall(text))
    return Counter(tokens)


def _collect_per_string(locale_dir: Path) -> Dict[str, Dict[str, Counter]]:
    """Return mapping: template_relpath -> {string_path -> Counter(tokens)}"""
    out: Dict[str, Dict[str, Counter]] = {}
    templates_dir = locale_dir / 'templates'
    if not templates_dir.exists():
        return out
    for fp in sorted(templates_dir.rglob('*.json')):
        rel = str(fp.relative_to(locale_dir))
        try:
            data = json.loads(fp.read_text(encoding='utf-8'))
        except Exception as exc:
            raise RuntimeError(f"Invalid JSON in {fp}: {exc}")
        mp: Dict[str, Counter] = {}
        for path, s in _walk_strings(data):
            mp[path] = _token_counter(s)
        out[rel] = mp
    return out


def main() -> int:
    root = _repo_root()
    troot = _translations_root(root)
    if not troot.exists():
        print(f"CI FAIL: translations root not found at {troot}")
        return 1

    base = _choose_base_locale(troot)
    base_dir = troot / base
    if not base_dir.is_dir():
        print(f"CI FAIL: base locale directory not found: {base_dir}")
        return 1

    base_map = _collect_per_string(base_dir)
    if not base_map:
        print(f"CI FAIL: no templates found under base locale: {base_dir / 'templates'}")
        return 1

    failures = 0

    for loc_dir in _iter_locale_dirs(troot):
        if loc_dir.name == base:
            continue
        cur_map = _collect_per_string(loc_dir)

        for rel, base_strings in base_map.items():
            if rel not in cur_map:
                # file parity is checked elsewhere; skip to avoid duplicate noise
                continue
            cur_strings = cur_map[rel]

            # Compare per string path. Treat missing string paths as failure because it implies structure drift.
            for spath, bcnt in base_strings.items():
                if spath not in cur_strings:
                    failures += 1
                    print(f"CI FAIL: missing string path {spath} in {rel} for locale={loc_dir.name}")
                    continue
                ccnt = cur_strings[spath]
                if ccnt != bcnt:
                    failures += 1
                    missing = bcnt - ccnt
                    extra = ccnt - bcnt
                    print(f"CI FAIL: token parity mismatch at {rel}::{spath} (base={base}, locale={loc_dir.name})")
                    if missing:
                        print(f"  missing tokens: {dict(missing)}")
                    if extra:
                        print(f"  extra tokens: {dict(extra)}")

    if failures:
        print(f"CI FAIL: per-string token parity failed for {failures} location(s)")
        return 1

    print(f"CI PASS: per-string token parity OK across locales (base={base})")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
