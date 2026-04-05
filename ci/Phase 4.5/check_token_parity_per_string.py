"""CI Check: Per-string Token Parity (Phase 4.5)

Assert that localization does not change placeholder token counts *per string field*.

This check is stricter than placeholder presence checks:
- compares token multiplicity (no duplicates / no drops)
- compares tokens at each string leaf path in every template JSON

Waiver mechanism
----------------
If a specific locale + template + string_path must intentionally diverge, add an entry to:
  ci/token_parity_waivers.json

Waivers are intended to be rare and auditable.

Token forms counted
-------------------
- Curly placeholders: {name}
- Double-curly placeholders: {{name}}

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
from typing import Any, Dict, Iterable, List, Tuple

RE_CURLY = re.compile(r"\{[A-Za-z0-9_\.:-]+\}")
RE_DBL_CURLY = re.compile(r"\{\{[^{}]+\}\}")


def repo_root() -> Path:
    # ci/ expected under repo root
    return Path(__file__).resolve().parents[1]


def translations_root(root: Path) -> Path:
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
    tokens: List[str] = []
    tokens.extend(RE_CURLY.findall(text))
    tokens.extend(RE_DBL_CURLY.findall(text))
    return Counter(tokens)


def collect_per_string(locale_dir: Path) -> Dict[str, Dict[str, Counter]]:
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
        for spath, s in walk_strings(data):
            mp[spath] = token_counter(s)
        out[rel] = mp
    return out


# -----------------------------
# Waivers
# -----------------------------

def load_waivers(ci_dir: Path) -> List[dict]:
    path = ci_dir / 'token_parity_waivers.json'
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        raise RuntimeError(f"Invalid waiver JSON at {path}: {exc}")
    waivers = data.get('waivers', [])
    return waivers if isinstance(waivers, list) else []


def _match(v: str, pat: str) -> bool:
    return pat == '*' or v == pat


def is_waived(waivers: List[dict], *, locale: str, template: str, string_path: str) -> Tuple[bool, str]:
    """Return (waived, reason)."""
    for w in waivers:
        if not isinstance(w, dict):
            continue
        wloc = str(w.get('locale', '*'))
        wtpl = str(w.get('template', '*'))
        wsp = str(w.get('string_path', '*'))
        if _match(locale, wloc) and _match(template, wtpl) and _match(string_path, wsp):
            return True, str(w.get('reason', ''))
    return False, ''


def main() -> int:
    root = repo_root()
    ci_dir = Path(__file__).resolve().parent
    waivers = load_waivers(ci_dir)

    troot = translations_root(root)
    if not troot.exists():
        print(f"CI FAIL: translations root not found at {troot}")
        return 1

    base = choose_base_locale(troot)
    base_dir = troot / base
    if not base_dir.is_dir():
        print(f"CI FAIL: base locale directory not found: {base_dir}")
        return 1

    base_map = collect_per_string(base_dir)
    if not base_map:
        print(f"CI FAIL: no templates found under base locale: {base_dir / 'templates'}")
        return 1

    failures = 0
    waived_count = 0

    for loc_dir in iter_locale_dirs(troot):
        if loc_dir.name == base:
            continue
        cur_map = collect_per_string(loc_dir)

        for rel, base_strings in base_map.items():
            if rel not in cur_map:
                continue  # parity validated elsewhere
            cur_strings = cur_map[rel]

            for spath, bcnt in base_strings.items():
                if spath not in cur_strings:
                    ok, reason = is_waived(waivers, locale=loc_dir.name, template=rel, string_path=spath)
                    if ok:
                        waived_count += 1
                        print(f"CI WAIVE: missing string path {rel}::{spath} locale={loc_dir.name} ({reason})")
                        continue
                    failures += 1
                    print(f"CI FAIL: missing string path {spath} in {rel} for locale={loc_dir.name}")
                    continue

                ccnt = cur_strings[spath]
                if ccnt != bcnt:
                    ok, reason = is_waived(waivers, locale=loc_dir.name, template=rel, string_path=spath)
                    if ok:
                        waived_count += 1
                        print(f"CI WAIVE: token mismatch at {rel}::{spath} locale={loc_dir.name} ({reason})")
                        continue

                    failures += 1
                    missing = bcnt - ccnt
                    extra = ccnt - bcnt
                    print(f"CI FAIL: token parity mismatch at {rel}::{spath} (base={base}, locale={loc_dir.name})")
                    if missing:
                        print(f"  missing tokens: {dict(missing)}")
                    if extra:
                        print(f"  extra tokens: {dict(extra)}")

    if failures:
        print(f"CI FAIL: per-string token parity failed for {failures} location(s) (waived={waived_count})")
        return 1

    print(f"CI PASS: per-string token parity OK across locales (base={base}, waived={waived_count})")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
