"""CI Check: Per-string Token Parity (Phase 4.5)

Enforces:
- per-string placeholder token parity (no duplicates/drops)
- explicit waivers (auditable)
- global + per-locale waiver budgets
- waiver decay via per-waiver `review_by` date
- auto-suggestion for `review_by` fixes in CI output
- single summary line at end

Auto-suggestion
---------------
When a waiver is missing/invalid/expired, CI output includes a suggested review_by value
of (today + 30 days) to make fixes quick.

Token forms counted
-------------------
- Curly placeholders: {name}
- Double-curly placeholders: {{name}}

Exit codes
----------
0 = pass
1 = fail
"""

# CI_CONTRACT: CI SUMMARY v1
# This script emits a single-line, machine-consumed summary at the end of execution.
# The format is versioned, documented in CI/README.md, and locked by CI self-tests.

from __future__ import annotations

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

RE_CURLY = re.compile(r"\{[A-Za-z0-9_\.:-]+\}")
RE_DBL_CURLY = re.compile(r"\{\{[^{}]+\}\}")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def translations_root(root: Path) -> Path:
    cand1 = root / 'translations'
    cand2 = root / 'localization' / 'translations'
    if cand1.exists():
        return cand1
    return cand2


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
            for k in ('base_locale', 'default_locale', 'root_locale', 'fallback_root'):
                v = data.get(k)
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


@dataclass(frozen=True)
class DecayPolicy:
    require_review_by: bool = True
    warn_before_days: int = 7
    fail_on_expired: bool = True


def parse_iso_date(s: str) -> date:
    return datetime.strptime(s, '%Y-%m-%d').date()


def load_waiver_config(ci_dir: Path) -> Tuple[List[dict], int, Dict[str, int], DecayPolicy]:
    path = ci_dir / 'token_parity_waivers.json'
    if not path.exists():
        return [], 0, {}, DecayPolicy(require_review_by=False, warn_before_days=0, fail_on_expired=False)

    data = json.loads(path.read_text(encoding='utf-8'))
    waivers = data.get('waivers', []) if isinstance(data.get('waivers', []), list) else []

    budget = int((data.get('budget', {}) or {}).get('max_total', 0))
    per_locale_raw = (data.get('budget', {}) or {}).get('per_locale', {}) or {}
    per_locale = {k: int(v) for k, v in per_locale_raw.items()}

    decay_raw = data.get('decay', {}) or {}
    policy = DecayPolicy(
        require_review_by=bool(decay_raw.get('require_review_by', True)),
        warn_before_days=int(decay_raw.get('warn_before_days', 7)),
        fail_on_expired=bool(decay_raw.get('fail_on_expired', True)),
    )
    return waivers, budget, per_locale, policy


def match(v: str, pat: str) -> bool:
    return pat == '*' or v == pat


def is_waived(waivers: List[dict], *, locale: str, template: str, string_path: str) -> Tuple[bool, str, str]:
    for w in waivers:
        if not isinstance(w, dict):
            continue
        if match(locale, str(w.get('locale', '*'))) and match(template, str(w.get('template', '*'))) and match(string_path, str(w.get('string_path', '*'))):
            return True, str(w.get('reason', '')), str(w.get('review_by', ''))
    return False, '', ''


def enforce_decay(waivers: List[dict], policy: DecayPolicy) -> str:
    """Validate waiver review_by dates. Returns suggested review_by string."""
    today = date.today()
    suggested = (today + timedelta(days=30)).isoformat()

    failures = 0
    for w in waivers:
        if not isinstance(w, dict):
            continue
        rb = str(w.get('review_by', '')).strip()

        if not rb:
            if policy.require_review_by:
                failures += 1
                print(f"CI FAIL: waiver missing review_by. Suggested review_by={suggested}. Waiver={w}")
            continue

        try:
            rb_date = parse_iso_date(rb)
        except Exception:
            failures += 1
            print(f"CI FAIL: waiver has invalid review_by date (expected YYYY-MM-DD). Suggested review_by={suggested}. review_by={rb} waiver={w}")
            continue

        if policy.fail_on_expired and today > rb_date:
            failures += 1
            print(f"CI FAIL: waiver expired (today={today}, review_by={rb_date}). Suggested review_by={suggested}. Waiver={w}")
        else:
            days_left = (rb_date - today).days
            if policy.warn_before_days and 0 <= days_left <= policy.warn_before_days:
                print(f"CI WARN: waiver nearing expiry in {days_left} day(s) (review_by={rb_date}). Consider updating review_by (e.g., {suggested}). Waiver={w}")

    if failures:
        raise SystemExit(1)

    return suggested


def main() -> int:
    root = repo_root()
    ci_dir = Path(__file__).resolve().parent

    waivers, global_budget, per_locale_budget, decay_policy = load_waiver_config(ci_dir)
    suggested_review_by = enforce_decay(waivers, decay_policy)

    troot = translations_root(root)
    if not troot.exists():
        print(f"CI FAIL: translations root not found at {troot}")
        print(f"CI SUMMARY: status=FAIL reason=missing_translations_root suggested_review_by={suggested_review_by}")
        return 1

    base = choose_base_locale(troot)
    base_dir = troot / base
    base_map = collect_per_string(base_dir)
    if not base_map:
        print("CI FAIL: no templates under base locale")
        print(f"CI SUMMARY: status=FAIL reason=no_base_templates base={base} suggested_review_by={suggested_review_by}")
        return 1

    failures = 0
    waived_total = 0
    waived_by_locale = defaultdict(int)

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
                    ok, reason, review_by = is_waived(waivers, locale=loc_dir.name, template=rel, string_path=spath)
                    if ok:
                        waived_total += 1
                        waived_by_locale[loc_dir.name] += 1
                        extra_note = f" review_by={review_by}" if review_by else ""
                        print(f"CI WAIVE: {rel}::{spath} locale={loc_dir.name} ({reason}){extra_note}")
                    else:
                        failures += 1
                        print(f"CI FAIL: token parity mismatch at {rel}::{spath} locale={loc_dir.name}")

    status = 'PASS'
    reason = 'ok'

    if failures:
        status = 'FAIL'
        reason = f'token_mismatch_count={failures}'
    elif global_budget and waived_total > global_budget:
        status = 'FAIL'
        reason = f'global_budget_exceeded used={waived_total} max={global_budget}'
    else:
        for loc, used in waived_by_locale.items():
            limit = per_locale_budget.get(loc)
            if limit is not None and used > limit:
                status = 'FAIL'
                reason = f'per_locale_budget_exceeded locale={loc} used={used} max={limit}'
                break

    # Single summary line (always printed)
    print(
        "CI SUMMARY: "
        f"status={status} "
        f"base={base} "
        f"waived_total={waived_total}/{global_budget or 0} "
        f"waived_by_locale={dict(waived_by_locale)} "
        f"per_locale_budget={per_locale_budget} "
        f"decay=require_review_by:{decay_policy.require_review_by},warn_before_days:{decay_policy.warn_before_days},fail_on_expired:{decay_policy.fail_on_expired} "
        f"suggested_review_by={suggested_review_by} "
        f"reason={reason}"
    )

    return 0 if status == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
