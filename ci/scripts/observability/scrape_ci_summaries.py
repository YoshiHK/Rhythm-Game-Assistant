"""Phase-6-style Observability Hook: CI SUMMARY Scraper

Purpose
-------
Scrape machine-consumed `CI SUMMARY:` log lines across runs and emit a structured
artifact (JSONL + JSON aggregate) for dashboards/alerts.

This is *wiring-only* observability:
- No gameplay semantics
- No upstream modification

Inputs
------
One or more log files (or directories containing logs). The scraper searches for
lines starting with `CI SUMMARY:`.

Outputs
-------
- ci_summary_events.jsonl  (one JSON object per summary line)
- ci_summary_aggregate.json (latest + counts by status/reason)

Usage examples
--------------
# scrape a single log
python scripts/observability/scrape_ci_summaries.py --log CI/logs/localization.log

# scrape all logs under a folder
python scripts/observability/scrape_ci_summaries.py --log-dir CI/logs --recursive

# in GitHub Actions: tee CI output then scrape
python ci/check_token_parity_per_string.py | tee CI/logs/token_parity.log
python scripts/observability/scrape_ci_summaries.py --log CI/logs/token_parity.log --out CI/artifacts

Contract
--------
Relies on log-level contract "CI SUMMARY v1".
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

SUMMARY_PREFIX = 'CI SUMMARY:'

# Very lightweight parser: split by spaces, keep key=value tokens.
# Values that contain spaces are not supported by contract.

KV_RE = re.compile(r"(?P<k>[A-Za-z0-9_]+)=(?P<v>.+)")


def iter_logs(paths: List[Path], recursive: bool = False) -> Iterable[Path]:
    for p in paths:
        if p.is_file():
            yield p
        elif p.is_dir():
            if recursive:
                yield from p.rglob('*.log')
                yield from p.rglob('*.txt')
                yield from p.rglob('*.out')
            else:
                yield from p.glob('*.log')
                yield from p.glob('*.txt')
                yield from p.glob('*.out')


def parse_summary_line(line: str) -> Dict[str, str]:
    line = line.strip()
    assert line.startswith(SUMMARY_PREFIX)
    rest = line[len(SUMMARY_PREFIX):].strip()
    parts = rest.split(' ')
    data: Dict[str, str] = {}
    for part in parts:
        if not part:
            continue
        m = KV_RE.match(part)
        if not m:
            # allow tokens like decay=require_review_by:True,warn_before_days:7,... (still key=value)
            continue
        data[m.group('k')] = m.group('v')
    return data


def scrape_file(fp: Path) -> List[Dict[str, str]]:
    events: List[Dict[str, str]] = []
    try:
        text = fp.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return events
    for line in text.splitlines():
        if line.startswith(SUMMARY_PREFIX):
            ev = parse_summary_line(line)
            ev['_source_file'] = str(fp)
            ev['_scraped_at'] = datetime.utcnow().isoformat() + 'Z'
            events.append(ev)
    return events


def aggregate(events: List[Dict[str, str]]) -> Dict:
    agg = {
        'total': len(events),
        'by_status': {},
        'by_reason': {},
        'latest': None,
    }
    if not events:
        return agg

    # latest by scraped_at order
    latest = events[-1]
    agg['latest'] = latest

    for ev in events:
        st = ev.get('status', 'UNKNOWN')
        rs = ev.get('reason', 'UNKNOWN')
        agg['by_status'][st] = agg['by_status'].get(st, 0) + 1
        agg['by_reason'][rs] = agg['by_reason'].get(rs, 0) + 1
    return agg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--log', action='append', default=[], help='Log file path (repeatable)')
    ap.add_argument('--log-dir', action='append', default=[], help='Directory containing logs (repeatable)')
    ap.add_argument('--recursive', action='store_true', help='Recurse into subdirectories for logs')
    ap.add_argument('--out', default='CI/artifacts', help='Output directory')
    args = ap.parse_args()

    inputs: List[Path] = [Path(p) for p in args.log] + [Path(p) for p in args.log_dir]
    if not inputs:
        print('No inputs. Provide --log or --log-dir.')
        return 2

    logs = list(iter_logs(inputs, recursive=args.recursive))
    all_events: List[Dict[str, str]] = []
    for fp in sorted(logs):
        all_events.extend(scrape_file(fp))

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = out_dir / 'ci_summary_events.jsonl'
    with jsonl_path.open('w', encoding='utf-8') as f:
        for ev in all_events:
            f.write(json.dumps(ev, ensure_ascii=False) + '
')

    agg_path = out_dir / 'ci_summary_aggregate.json'
    agg = aggregate(all_events)
    agg_path.write_text(json.dumps(agg, indent=2, ensure_ascii=False) + '
', encoding='utf-8')

    print(f'Wrote {jsonl_path} ({len(all_events)} events)')
    print(f'Wrote {agg_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
