"""
CI Observability Hook — CI SUMMARY Scraper (Design-Locked)

Purpose:
- Scrape log-level CI SUMMARY signals emitted by Phase CI layers
- Produce structured artifacts for dashboards and alerting

IMPORTANT:
- Phase-agnostic
- CI-only
- Does NOT gate Phase CI
- Does NOT evaluate CI correctness
- Operates strictly on CI SUMMARY v1 (log-level contract)
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

SUMMARY_PREFIX = "CI SUMMARY:"

# key=value tokens; values must not contain spaces
KV_RE = re.compile(r"(?P<k>[A-Za-z0-9_]+)=(?P<v>[^ ]+)")


def iter_logs(paths: List[Path], recursive: bool = False) -> Iterable[Path]:
    for p in paths:
        if p.is_file():
            yield p
        elif p.is_dir():
            if recursive:
                yield from p.rglob("*.log")
                yield from p.rglob("*.txt")
                yield from p.rglob("*.out")
            else:
                yield from p.glob("*.log")
                yield from p.glob("*.txt")
                yield from p.glob("*.out")


def parse_summary_line(line: str) -> Dict[str, str]:
    """
    Parse a single CI SUMMARY line into a dict of key=value tokens.
    """
    data: Dict[str, str] = {}
    if not line.startswith(SUMMARY_PREFIX):
        return data

    rest = line[len(SUMMARY_PREFIX) :].strip()
    for part in rest.split(" "):
        if not part:
            continue
        m = KV_RE.match(part)
        if not m:
            continue
        data[m.group("k")] = m.group("v")
    return data


def scrape_file(fp: Path) -> List[Dict[str, str]]:
    events: List[Dict[str, str]] = []
    try:
        text = fp.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return events

    for line in text.splitlines():
        if not line.startswith(SUMMARY_PREFIX):
            continue
        ev = parse_summary_line(line)
        if not ev:
            continue
        ev["_source_file"] = str(fp)
        ev["_scraped_at"] = datetime.utcnow().isoformat() + "Z"
        events.append(ev)
    return events


def aggregate(events: List[Dict[str, str]]) -> Dict:
    """
    Aggregate CI SUMMARY events into a single JSON object.
    """
    agg = {
        "total": len(events),
        "by_status": {},
        "by_reason": {},
        "latest": None,
    }

    for ev in events:
        status = ev.get("status", "UNKNOWN")
        reason = ev.get("reason", "UNKNOWN")

        agg["by_status"][status] = agg["by_status"].get(status, 0) + 1
        agg["by_reason"][reason] = agg["by_reason"].get(reason, 0) + 1

    if events:
        agg["latest"] = events[-1]

    return agg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", action="append", default=[], help="Log file path (repeatable)")
    ap.add_argument("--log-dir", action="append", default=[], help="Directory containing logs (repeatable)")
    ap.add_argument("--recursive", action="store_true", help="Recurse into subdirectories for logs")
    ap.add_argument("--out", default="CI/artifacts", help="Output directory")

    args = ap.parse_args()

    paths = [Path(p) for p in args.log] + [Path(p) for p in args.log_dir]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_events: List[Dict[str, str]] = []
    for fp in iter_logs(paths, recursive=args.recursive):
        all_events.extend(scrape_file(fp))

    # Write JSONL
    events_path = out_dir / "ci_summary_events.jsonl"
    with events_path.open("w", encoding="utf-8") as f:
        for ev in all_events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    # Write aggregate
    agg = aggregate(all_events)
    agg_path = out_dir / "ci_summary_aggregate.json"
    agg_path.write_text(json.dumps(agg, indent=2), encoding="utf-8")

    print(f"SCRAPE PASS: {len(all_events)} CI SUMMARY events written to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())