"""
CI Check: Per-string Token Parity (Phase 4.5)

Enforces:
- per-string placeholder token parity (no duplicates/drops)
- explicit waivers (auditable)
- global + per-locale waiver budgets
- waiver decay via review_by dates
- auto-suggestion for review_by fixes in CI output
- a single summary line at end ("CI SUMMARY: ...") for observability scraping

Token forms counted (as written in text):
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
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


RE_CURLY = re.compile(r"\{[A-Za-z0-9_.:-]+\}")
RE_DBL_CURLY = re.compile(r"\{\{\s*[A-Za-z0-9_.:-]+\s*\}\}")


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    sys.exit(1)


def repo_root() -> Path:
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
        except Exception:
            pass
    locs = [p.name for p in iter_locale_dirs(troot)]
    return locs[0] if locs else "en-US"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        fail(f"Failed to parse JSON: {path}: {e}")


def walk_strings(obj: Any, prefix: str = "$") -> Iterable[Tuple[str, str]]:
    if isinstance(obj, str):
        yield (prefix, obj)
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f"{prefix}.{k}")
        return
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{prefix}[{i}]")
        return


def token_counter(text: str) -> Counter:
    c = Counter()
    c.update(RE_CURLY.findall(text))
    c.update(RE_DBL_CURLY.findall(text))
    return c


def collect_per_string(locale_dir: Path) -> Dict[str, Dict[str, Counter]]:
    """
    Returns:
      { template_rel_path: { string_path: Counter(tokens) } }
    """
    out: Dict[str, Dict[str, Counter]] = {}
    tdir = locale_dir / "templates"
    if not tdir.exists():
        return out

    for fp in sorted(tdir.rglob("*.json")):
        rel = fp.relative_to(locale_dir).as_posix()
        data = load_json(fp)
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
    return datetime.strptime(s, "%Y-%m-%d").date()


def match(value: str, pat: str) -> bool:
    return pat == "*" or value == pat


def load_waiver_config(ci_dir: Path) -> Tuple[List[dict], int, Dict[str, int], DecayPolicy]:
    """
    Returns:
      waivers, max_total, per_locale, decay_policy
    """
    # allow both placements: ci/token_parity_waivers.json OR ci/data/token_parity_waivers.json
    cand = [
        ci_dir / "token_parity_waivers.json",
        ci_dir / "data" / "token_parity_waivers.json",
    ]
    path = None
    for c in cand:
        if c.exists():
            path = c
            break

    if path is None:
        # No waivers => strict mode with zero budgets
        return [], 0, {}, DecayPolicy(require_review_by=False, warn_before_days=0, fail_on_expired=False)

    obj = load_json(path)
    if not isinstance(obj, dict):
        fail(f"Waiver config must be object: {path}")

    budget = obj.get("budget", {})
    if not isinstance(budget, dict):
        budget = {}

    max_total = int(budget.get("max_total", 0) or 0)
    per_locale = budget.get("per_locale", {}) or {}
    if not isinstance(per_locale, dict):
        per_locale = {}

    per_locale_int: Dict[str, int] = {}
    for k, v in per_locale.items():
        if isinstance(k, str) and isinstance(v, int):
            per_locale_int[k] = int(v)

    decay_obj = obj.get("decay", {})
    if not isinstance(decay_obj, dict):
        decay_obj = {}

    policy = DecayPolicy(
        require_review_by=bool(decay_obj.get("require_review_by", True)),
        warn_before_days=int(decay_obj.get("warn_before_days", 7) or 7),
        fail_on_expired=bool(decay_obj.get("fail_on_expired", True)),
    )

    waivers = obj.get("waivers", [])
    if not isinstance(waivers, list):
        waivers = []

    return waivers, max_total, per_locale_int, policy


def is_waived(
    waivers: List[dict],
    *,
    locale: str,
    template: str,
    string_path: str,
) -> Tuple[bool, str, str]:
    """
    Returns (waived, reason, review_by)
    Supports wildcard "*" matching.
    """
    for w in waivers:
        if not isinstance(w, dict):
            continue
        loc_pat = str(w.get("locale", "*"))
        tpl_pat = str(w.get("template", "*"))
        sp_pat = str(w.get("string_path", "*"))

        if match(locale, loc_pat) and match(template, tpl_pat) and match(string_path, sp_pat):
            return True, str(w.get("reason", "")), str(w.get("review_by", ""))
    return False, "", ""


def enforce_decay(review_by: str, policy: DecayPolicy) -> Tuple[bool, str]:
    """
    Returns (ok, suggested_review_by)
    """
    suggested = (date.today() + timedelta(days=30)).isoformat()

    if not policy.require_review_by:
        return True, suggested

    if not review_by or not isinstance(review_by, str):
        return False, suggested

    try:
        d = parse_iso_date(review_by)
    except Exception:
        return False, suggested

    today = date.today()
    if d < today and policy.fail_on_expired:
        return False, suggested

    # warning window is informational; does not fail by itself
    return True, suggested


def main() -> int:
    root = repo_root()
    troot = translations_root(root)
    if not troot.exists():
        fail(f"translations root not found under: {root}")

    base_locale = choose_base_locale(troot)
    base_dir = troot / base_locale
    if not base_dir.exists():
        fail(f"Base locale directory not found: {base_dir}")

    ci_dir = Path(__file__).resolve().parent
    waivers, max_total, per_locale_budget, decay_policy = load_waiver_config(ci_dir)

    base = collect_per_string(base_dir)
    if not base:
        fail(f"No templates found under base locale: {base_locale}/templates")

    locales = [p.name for p in iter_locale_dirs(troot)]

    mismatches = 0
    waived = 0
    waived_by_locale = defaultdict(int)
    expired_or_invalid_waivers = 0

    for loc in locales:
        if loc == base_locale:
            continue
        loc_dir = troot / loc
        cur = collect_per_string(loc_dir)

        if set(cur.keys()) != set(base.keys()):
            missing = sorted(set(base.keys()) - set(cur.keys()))
            extra = sorted(set(cur.keys()) - set(base.keys()))
            fail(f"Template set mismatch for locale {loc}. Missing={missing} Extra={extra}")

        for tpl in sorted(base.keys()):
            base_map = base[tpl]
            cur_map = cur[tpl]

            # Compare per string path present in base
            for spath, base_counter in base_map.items():
                cur_counter = cur_map.get(spath, Counter())

                if base_counter == cur_counter:
                    continue

                mismatches += 1

                waived_flag, reason, review_by = is_waived(waivers, locale=loc, template=tpl, string_path=spath)
                if not waived_flag:
                    fail(
                        f"Token parity mismatch (not waived): locale={loc} template={tpl} path={spath} "
                        f"base={dict(base_counter)} cur={dict(cur_counter)}"
                    )

                ok, suggested = enforce_decay(review_by, decay_policy)
                if not ok:
                    expired_or_invalid_waivers += 1
                    fail(
                        f"Waiver invalid/expired: locale={loc} template={tpl} path={spath} "
                        f"review_by='{review_by}' (suggested '{suggested}') reason='{reason}'"
                    )

                waived += 1
                waived_by_locale[loc] += 1

    # Budget enforcement (waivers only; mismatches must be waived to pass)
    if max_total and waived > max_total:
        fail(f"Waiver budget exceeded: used={waived} max_total={max_total}")

    for loc, used in sorted(waived_by_locale.items()):
        cap = per_locale_budget.get(loc)
        if cap is not None and used > cap:
            fail(f"Per-locale waiver budget exceeded: locale={loc} used={used} cap={cap}")

    # Single-line summary for observability scraping (locked format, no versioning)
    print(
        "CI SUMMARY: token_parity_per_string "
        f"status=PASS mismatches={mismatches} waivers_used={waived} "
        f"invalid_waivers={expired_or_invalid_waivers}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())