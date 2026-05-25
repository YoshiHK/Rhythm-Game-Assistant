from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _parse_used_budget(waived_total: str):
    if not isinstance(waived_total, str) or '/' not in waived_total:
        return None
    left, right = waived_total.split('/', 1)
    try:
        return int(left.strip()), int(right.strip())
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--aggregate', default='CI/artifacts/ci_summary_aggregate.json')
    ap.add_argument('--fail-remaining', type=int, default=1)
    ap.add_argument('--fail-ratio', type=float, default=0.9)

    args = ap.parse_args()

    agg_path = Path(args.aggregate)

    if not agg_path.exists():
        print("ERROR: missing aggregate file")
        return 2

    data = json.loads(agg_path.read_text(encoding="utf-8"))

    by_phase = data.get("by_phase", {})

    # ✅ Phase-aware failure detection
    failed_phases = [
        phase for phase, entry in by_phase.items()
        if entry.get("status") == "FAIL"
    ]

    if failed_phases:
        print(f"FAIL: phases failed → {failed_phases}")
        return 1

    # ✅ Budget check (optional)
    latest = data.get("latest") or {}
    waived = latest.get("waived_total")

    parsed = _parse_used_budget(waived)
    if parsed:
        used, budget = parsed
        remaining = budget - used

        if remaining <= args.fail-remaining:
            print(f"FAIL: remaining budget too low → {remaining}")
            return 1

        if budget > 0 and (used / budget) >= args.fail-ratio:
            print(f"FAIL: budget ratio exceeded → {used}/{budget}")
            return 1

    print("PASS: CI summary healthy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
``