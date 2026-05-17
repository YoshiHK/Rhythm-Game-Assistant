#!/usr/bin/env python3
"""
Phase 4.5 Localization — Per-string Token Parity Check (CI-only, NON-RUNTIME)

Enforces:
- Per-template, per-variant placeholder token parity vs base locale
- Explicit waivers (auditable)
- Single-line CI SUMMARY output at end (machine-consumable)

Tokens counted (as written in text):
- {name}
- {{name}}

Non-goals:
- Translation quality
- Word budget (check_word_budget.py)
- File-set parity (check_template_parity.py)

Exit codes:
- 0: pass
- 2: fail
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


LAYER_DIRS = ["chart_level", "element_level", "section_level", "guidance_framing", "tone"]

RE_CURLY = re.compile(r"\{[A-Za-z0-9_.:-]+\}")
RE_DBL_CURLY = re.compile(r"\{\{\s*[A-Za-z0-9_.:-]+\s*\}\}")


def read_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def token_counter(text: str) -> Counter:
    c = Counter()
    c.update(RE_CURLY.findall(text or ""))
    c.update(RE_DBL_CURLY.findall(text or ""))
    return c


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    raise SystemExit(2)


def find_translations_root(cli_value: Optional[str]) -> Path:
    if cli_value:
        return Path(cli_value)
    candidates = [
        Path("translations"),
        Path("Phase 4.5 - Localization") / "translations",
        Path("Phase_4.5_Localization") / "translations",
    ]
    for c in candidates:
        if c.exists():
            return c
    fail("Cannot locate translations root (use --translations-root)")
    return Path(".")  # unreachable


def load_locales(translations_root: Path) -> Tuple[str, List[str]]:
    p = translations_root / "_meta" / "locales.json"
    if not p.exists():
        fail(f"Missing locales.json at {p}")
    obj = read_json(p)
    base = str(obj.get("base_locale", "en-US"))
    supported = obj.get("supported_locales", [])
    if not isinstance(supported, list) or not supported:
        fail("locales.json supported_locales missing/invalid")
    return base, [str(x) for x in supported]


def load_templates(locale_dir: Path) -> Dict[str, Dict[str, str]]:
    """
    Returns: { template_id: { variant: text } }
    """
    out: Dict[str, Dict[str, str]] = {}
    for layer in LAYER_DIRS:
        d = locale_dir / layer
        if not d.exists():
            continue
        for f in d.glob("*.json"):
            try:
                obj = read_json(f)
            except Exception:
                continue
            tid = obj.get("template_id")
            if not isinstance(tid, str) or not tid:
                continue
            strings = obj.get("strings", {})
            if not isinstance(strings, dict):
                continue
            vmap: Dict[str, str] = {}
            for vk, entry in strings.items():
                if isinstance(entry, dict) and isinstance(entry.get("text"), str):
                    vmap[vk] = entry["text"]
            if vmap:
                out[tid] = vmap
    return out


@dataclass(frozen=True)
class DecayPolicy:
    require_review_by: bool = True
    warn_before_days: int = 7
    fail_on_expired: bool = True


def parse_iso_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def load_waivers(ci_dir: Path) -> Tuple[List[dict], DecayPolicy]:
    """
    Load waiver config from:
    - ci/data/token_parity_waivers.json (preferred)
    - ci/token_parity_waivers.json (fallback)
    """
    candidates = [
        ci_dir / "data" / "token_parity_waivers.json",
        ci_dir / "token_parity_waivers.json",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        return [], DecayPolicy()

    obj = read_json(path)
    waivers = obj.get("waivers", [])
    decay = obj.get("decay_policy", {}) if isinstance(obj, dict) else {}

    policy = DecayPolicy(
        require_review_by=bool(decay.get("require_review_by", True)),
        warn_before_days=int(decay.get("warn_before_days", 7)),
        fail_on_expired=bool(decay.get("fail_on_expired", True)),
    )

    return waivers if isinstance(waivers, list) else [], policy


def match(value: str, pat: str) -> bool:
    # wildcard support: "*" matches any
    return pat == "*" or pat == value


def is_waived(waivers: List[dict], locale: str, template_id: str, variant: str) -> Tuple[bool, str, str]:
    """
    Waiver record format (suggested):
    {
      "locale": "zh-Hant-TW" | "*" ,
      "template_id": "element_density" | "*",
      "variant": "default" | "*" ,
      "reason": "...",
      "review_by": "YYYY-MM-DD"
    }
    """
    for w in waivers:
        if not isinstance(w, dict):
            continue
        lp = str(w.get("locale", "*"))
        tp = str(w.get("template_id", "*"))
        vp = str(w.get("variant", "*"))
        if match(locale, lp) and match(template_id, tp) and match(variant, vp):
            return True, str(w.get("reason", "")), str(w.get("review_by", ""))
    return False, "", ""


def enforce_decay(review_by: str, policy: DecayPolicy) -> Tuple[bool, bool]:
    """
    Returns (expired, should_warn)
    """
    if not policy.require_review_by:
        return False, False
    if not review_by:
        # missing date is treated as expired when required
        return True, False

    try:
        rb = parse_iso_date(review_by)
    except Exception:
        return True, False

    today = date.today()
    expired = rb < today
    should_warn = (rb - today) <= timedelta(days=policy.warn_before_days)
    return expired, should_warn


def ci_summary(errors: int, waivers_used: int, expired_waivers: int) -> None:
    # MUST be exactly one physical line
    print(f"CI SUMMARY: token_parity_per_string status={'PASS' if errors==0 else 'FAIL'} mismatches={errors} waivers_used={waivers_used} expired_waivers={expired_waivers}")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--translations-root", type=str, default=None)
    args = ap.parse_args(argv)

    # locate roots
    ci_dir = Path(__file__).resolve().parents[1]
    translations_root = find_translations_root(args.translations_root)
    base_locale, locales = load_locales(translations_root)

    waivers, decay_policy = load_waivers(ci_dir)

    base_dir = translations_root / base_locale
    if not base_dir.exists():
        fail(f"Base locale missing: {base_dir}")

    base_templates = load_templates(base_dir)

    mismatches: List[str] = []
    waivers_used = 0
    expired_waivers = 0

    for loc in locales:
        if loc == base_locale:
            continue
        loc_dir = translations_root / loc
        if not loc_dir.exists():
            mismatches.append(f"[{loc}] Missing locale directory: {loc_dir}")
            continue

        loc_templates = load_templates(loc_dir)

        # Compare only templates present in base (parity check handles missing templates)
        for tid, base_vmap in base_templates.items():
            if tid not in loc_templates:
                continue
            cur_vmap = loc_templates[tid]

            for variant, base_text in base_vmap.items():
                if variant not in cur_vmap:
                    # variant parity check handles this, but keep safe
                    continue

                base_tokens = token_counter(base_text)
                cur_tokens = token_counter(cur_vmap[variant])

                if base_tokens != cur_tokens:
                    waived, reason, review_by = is_waived(waivers, loc, tid, variant)
                    if waived:
                        waivers_used += 1
                        expired, warn = enforce_decay(review_by, decay_policy)
                        if expired:
                            expired_waivers += 1
                            if decay_policy.fail_on_expired:
                                mismatches.append(
                                    f"[{loc}] WAIVER EXPIRED {tid}:{variant} review_by={review_by} reason={reason}"
                                )
                        # waived and not expired -> accept mismatch
                        continue

                    # not waived -> record mismatch
                    mismatches.append(
                        f"[{loc}] token mismatch {tid}:{variant} base={dict(base_tokens)} cur={dict(cur_tokens)}"
                    )

    # Emit details
    for m in mismatches:
        print(f"ERROR: {m}")

    error_count = len(mismatches)
    ci_summary(error_count, waivers_used, expired_waivers)

    return 0 if error_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())