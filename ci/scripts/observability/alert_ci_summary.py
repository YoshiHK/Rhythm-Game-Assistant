"""Phase-6-style Alert Rule: CI SUMMARY Aggregate Gate

This script reads `CI/artifacts/ci_summary_aggregate.json` (produced by
`scripts/observability/scrape_ci_summaries.py`) and fails CI when:

1) latest.status == FAIL
2) waived_total approaches the configured budget threshold

The rule is intentionally non-semantic and operates only on the log-level
contract (CI SUMMARY v1).

Usage:
  python scripts/observability/alert_ci_summary.py --aggregate CI/artifacts/ci_summary_aggregate.json

Optional thresholds:
  --fail-remaining 1     # fail when remaining budget <= this value
  --fail-ratio 0.9       # fail when used/budget >= this ratio

Exit codes:
  0 pass
  1 fail
  2 misconfigured / missing artifact
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _parse_used_budget(waived_total: str) -> tuple[int, int] | None:
    """Parse 'used/budget' from waived_total string."""
    if not isinstance(waived_total, str) or '/' not in waived_total:
        return None
    left, right = waived_total.split('/', 1)
    try:
        used = int(left.strip())
        budget = int(right.strip())
        return used, budget
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--aggregate', default='CI/artifacts/ci_summary_aggregate.json')
    ap.add_argument('--fail-remaining', type=int, default=1,
                    help='Fail when remaining waiver budget <= this value (default: 1)')
    ap.add_argument('--fail-ratio', type=float, default=0.9,
                    help='Fail when used/budget >= this ratio (default: 0.90)')
    args = ap.parse_args()

    path = Path(args.aggregate)
    if not path.exists():
        print(f"ALERT FAIL: missing aggregate artifact: {path}")
        return 2

    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        print(f"ALERT FAIL: invalid JSON in aggregate artifact: {path} ({exc})")
        return 2

    latest = data.get('latest')
    if not latest:
        print("ALERT FAIL: aggregate has no latest event (did scraper run?)")
        return 2

    status = latest.get('status')
    if status == 'FAIL':
        reason = latest.get('reason', 'UNKNOWN')
        print(f"ALERT FAIL: latest.status=FAIL (reason={reason})")
        return 1

    waived_total = latest.get('waived_total')
    parsed = _parse_used_budget(waived_total)
    if parsed:
        used, budget = parsed
        if budget > 0:
            remaining = budget - used
            ratio = used / budget
            if remaining <= args.fail_remaining:
                print(f"ALERT FAIL: waiver budget nearly exhausted (used={used}, budget={budget}, remaining={remaining})")
                return 1
            if ratio >= args.fail_ratio:
                print(f"ALERT FAIL: waiver budget usage high (used={used}, budget={budget}, ratio={ratio:.2f} >= {args.fail_ratio})")
                return 1

    # Pass
    print("ALERT PASS: CI summary aggregate within thresholds")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
