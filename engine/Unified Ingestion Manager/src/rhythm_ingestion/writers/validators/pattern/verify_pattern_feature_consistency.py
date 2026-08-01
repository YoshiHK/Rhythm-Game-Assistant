from __future__ import annotations

"""
verify_pattern_feature_consistency.py

Check consistency of pattern_features rows against chart_patterns.db.
"""

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from rhythm_ingestion.writers.chart_pattern_writer import DEFAULT_DB_PATH as DEFAULT_CHART_PATTERNS_DB
except Exception:
    try:
        from chart_pattern_writer import DEFAULT_DB_PATH as DEFAULT_CHART_PATTERNS_DB
    except Exception:
        DEFAULT_CHART_PATTERNS_DB = Path("chart_patterns.db")

_NUMERIC_KEYS = [
    "density",
    "burst_density",
    "stream_length_avg",
    "jump_ratio",
    "hold_complexity",
    "section_variance",
    "spike_count",
]


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _get_rows(conn: sqlite3.Connection, table_name: str) -> List[Dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"SELECT * FROM {table_name}").fetchall()
    return [dict(r) for r in rows]


@dataclass
class FeatureConsistencyIssue:
    severity: str
    code: str
    chart_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeatureConsistencySummary:
    feature_rows: int = 0
    linked_rows: int = 0
    orphan_rows: int = 0
    invalid_numeric_rows: int = 0
    invalid_pattern_score_json_rows: int = 0
    consistent: bool = False


def verify_pattern_feature_consistency(*, chart_patterns_db: Path) -> Dict[str, Any]:
    issues: List[FeatureConsistencyIssue] = []
    summary = FeatureConsistencySummary()

    if not chart_patterns_db.exists():
        raise FileNotFoundError(chart_patterns_db)

    with sqlite3.connect(str(chart_patterns_db)) as conn:
        if not _table_exists(conn, "chart_patterns"):
            raise ValueError("chart_patterns table not found")
        if not _table_exists(conn, "pattern_features"):
            return {"summary": asdict(summary), "issues": [asdict(FeatureConsistencyIssue(severity="warning", code="pattern_features_table_missing"))]}

        base_rows = _get_rows(conn, "chart_patterns")
        feat_rows = _get_rows(conn, "pattern_features")

    summary.feature_rows = len(feat_rows)
    keyset = {
        (str(r.get("chart_id")), int(r.get("extraction_version") or 0))
        for r in base_rows
    }

    for row in feat_rows:
        chart_id = str(row.get("chart_id") or "")
        ev = int(row.get("extraction_version") or 0)
        key = (chart_id, ev)

        if key in keyset:
            summary.linked_rows += 1
        else:
            summary.orphan_rows += 1
            issues.append(FeatureConsistencyIssue(severity="warning", code="orphan_feature_row", chart_id=chart_id, details={"extraction_version": ev}))

        bad_numeric = False
        for k in _NUMERIC_KEYS:
            v = row.get(k)
            if v is None:
                continue
            try:
                float(v)
            except Exception:
                bad_numeric = True
                issues.append(FeatureConsistencyIssue(severity="warning", code="invalid_numeric_value", chart_id=chart_id, details={"field": k, "value": v}))
        if bad_numeric:
            summary.invalid_numeric_rows += 1

        psj = row.get("pattern_score_json")
        if psj:
            try:
                json.loads(psj)
            except Exception:
                summary.invalid_pattern_score_json_rows += 1
                issues.append(FeatureConsistencyIssue(severity="warning", code="invalid_pattern_score_json", chart_id=chart_id))

    summary.consistent = (
        summary.orphan_rows == 0 and
        summary.invalid_numeric_rows == 0 and
        summary.invalid_pattern_score_json_rows == 0
    )

    return {"summary": asdict(summary), "issues": [asdict(i) for i in issues]}


def _json_dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser("verify_pattern_feature_consistency")
    parser.add_argument("--chart-patterns-db", default=str(DEFAULT_CHART_PATTERNS_DB))
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args(argv)

    report = verify_pattern_feature_consistency(chart_patterns_db=Path(args.chart_patterns_db))
    summary = report.get("summary", {})
    print("[FEATURE CONSISTENCY] consistent=", summary.get("consistent"))
    print("[FEATURE CONSISTENCY] feature_rows=", summary.get("feature_rows"))
    print("[FEATURE CONSISTENCY] orphan_rows=", summary.get("orphan_rows"))
    print("[FEATURE CONSISTENCY] invalid_numeric_rows=", summary.get("invalid_numeric_rows"))
    print("[FEATURE CONSISTENCY] invalid_pattern_score_json_rows=", summary.get("invalid_pattern_score_json_rows"))
    if args.json_out:
        _json_dump(Path(args.json_out), report)
    return 0 if bool(summary.get("consistent")) else 1


__all__ = ["verify_pattern_feature_consistency", "cli_main"]
