from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List

SUMMARY_PREFIX = "CI SUMMARY:"

# key=value (no spaces inside value)
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
    data: Dict[str, str] = {}
    if not line.startswith(SUMMARY_PREFIX):
        return data

    payload = line[len(SUMMARY_PREFIX):].strip()

    for m in KV_RE.finditer(payload):
        data[m.group("k")] = m.group("v")

    return data


def scrape_file(fp: Path) -> List[Dict[str, str]]:
    events: List[Dict[str, str]] = []
    try:
        text = fp.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return events

    for line in text.splitlines():
        parsed = parse_summary_line(line)
        if parsed:
            events.append(parsed)

    return events


def aggregate(events: List[Dict[str, str]]) -> Dict:
    agg: Dict = {
        "total": len(events),
        "by_status": {},
        "by_phase": {},
        "latest": None,
    }

    for e in events:
        status = e.get("status", "unknown")
        phase = e.get("phase", "unknown")

        agg["by_status"][status] = agg["by_status"].get(status, 0) + 1

        agg["by_phase"][phase] = e  # last seen per phase

        agg["latest"] = e

    return agg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", action="append", default=[])
    ap.add_argument("--log-dir", action="append", default=[])
    ap.add_argument("--recursive", action="store_true")
    ap.add_argument("--out", default="CI/artifacts")
    args = ap.parse_args()

    paths = [Path(p) for p in args.log] + [Path(p) for p in args.log_dir]

    events: List[Dict[str, str]] = []

    for fp in iter_logs(paths, recursive=args.recursive):
        events.extend(scrape_file(fp))

    result = aggregate(events)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / "ci_summary_aggregate.json"
    out_file.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("CI SUMMARY AGGREGATED:", json.dumps(result))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())