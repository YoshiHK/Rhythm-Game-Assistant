"""CI Check: Per-string Token Parity (Phase 4.5) with Waiver Budget

Adds a waiver budget to prevent silent drift:
- Waivers are allowed but capped by a global budget.

Budget rules
------------
- Read from ci/token_parity_waivers.json -> budget.max_total
- CI fails if applied waivers exceed the budget.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

RE_CURLY = re.compile(r"\{[A-Za-z0-9_\.:-]+\}")
RE_DBL_CURLY = re.compile(r"\{\{[^{}]+\}\}")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def translations_root(root: Path) -> Path:
    cand1 = root / 'translations'
    cand2 = root / 'localization' / 'translations'
    return cand1 if cand1.exists() else cand2


def iter_locale_dirs(troot: Path) -> Iterable[Path]:
    for p in sorted(troot.iterdir()):
        if p.is_dir() and not p.name.startswith('_'):
            yield p


def choose_base_locale(troot: Path) -> str:
    if (troot / 'en-US').is_dir():
        return 'en-US'
    meta = troot / '_meta' / 'locales.json'
    if meta.exists():
        try:
            data = json.loads(meta.read_text(encoding='utf-8'))
            for k in ('base_locale','default_locale','root_locale','fallback_root'):
                v = data.get(k)
                if isinstance(v,str) and (troot / v).is_dir():
                    return v
        except Exception:
            pass
    locs = [p.name for p in iter_locale_dirs(troot)]
    return locs[0] if locs else 'en-US'


def walk_strings(obj: Any, prefix: str = '') -> Iterable[Tuple[str, str]]:
    if isinstance(obj, str):
        yield (prefix or '$', obj)
    elif isinstance(obj, dict):
        for k,v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            yield from walk_strings(v,p)
    elif isinstance(obj, list):
        for i,v in enumerate(obj):
            p = f"{prefix}[{i}]" if prefix else f"[{i}]"
            yield from walk_strings(v,p)


def token_counter(text: str) -> Counter:
    c = Counter()
    c.update(RE_CURLY.findall(text))
    c.update(RE_DBL_CURLY.findall(text))
    return c


def collect_per_string(locale_dir: Path) -> Dict[str, Dict[str, Counter]]:
    out: Dict[str, Dict[str, Counter]] = {}
    tdir = locale_dir / 'templates'
    if not tdir.exists():
        return out
    for fp in sorted(tdir.rglob('*.json')):
        rel = str(fp.relative_to(locale_dir))
        data = json.loads(fp.read_text(encoding='utf-8'))
        mp: Dict[str, Counter] = {}
        for spath, s in walk_strings(data):
            mp[spath] = token_counter(s)
        out[rel] = mp
    return out


def load_waivers(ci_dir: Path) -> Tuple[List[dict], int]:
    path = ci_dir / 'token_parity_waivers.json'
    if not path.exists():
        return [], 0
    data = json.loads(path.read_text(encoding='utf-8'))
    waivers = data.get('waivers', []) if isinstance(data.get('waivers', []), list) else []
    budget = int(data.get('budget', {}).get('max_total', 0))
    return waivers, budget


def match(v: str, pat: str) -> bool:
    return pat == '*' or v == pat


def is_waived(waivers: List[dict], *, locale: str, template: str, string_path: str) -> Tuple[bool, str]:
    for w in waivers:
        if not isinstance(w, dict):
            continue
        if match(locale, str(w.get('locale','*'))) and match(template, str(w.get('template','*'))) and match(string_path, str(w.get('string_path','*'))):
            return True, str(w.get('reason',''))
    return False, ''


def main() -> int:
    root = repo_root()
    ci_dir = Path(__file__).resolve().parent
    waivers, budget = load_waivers(ci_dir)

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
        print("CI FAIL: no templates under base locale")
        return 1

    failures = 0
    waived = 0

    for loc_dir in iter_locale_dirs(troot):
        if loc_dir.name == base:
            continue
        cur_map = collect_per_string(loc_dir)
        for rel, base_strings in base_map.items():
            if rel not in cur_map:
                continue
            cur_strings = cur_map[rel]
            for spath, bcnt in base_strings.items():
                if spath not in cur_strings or cur_strings[spath] != bcnt:
                    ok, reason = is_waived(waivers, locale=loc_dir.name, template=rel, string_path=spath)
                    if ok:
                        waived += 1
                        print(f"CI WAIVE: {rel}::{spath} locale={loc_dir.name} ({reason})")
                    else:
                        failures += 1
                        print(f"CI FAIL: token parity mismatch at {rel}::{spath} locale={loc_dir.name}")

    if failures:
        print(f"CI FAIL: per-string token parity failed for {failures} location(s)")
        return 1

    if budget and waived > budget:
        print(f"CI FAIL: waiver budget exceeded (used={waived}, max={budget})")
        return 1

    print(f"CI PASS: per-string token parity OK (waived={waived}, budget={budget})")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
