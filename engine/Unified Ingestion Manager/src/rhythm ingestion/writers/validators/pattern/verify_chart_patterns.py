from __future__ import annotations

"""
verify_chart_patterns.py

System-level verification for chart_patterns.db.

Purpose
-------
Verify that chart_patterns.db is structurally present and internally readable.
This is the pattern-side counterpart to asset verification.

Scope
-----
- read-only verification
- no DB mutation
- no completed-phase modification
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
class PatternVerifyIssue:
    severity: str  # error / warning
    code: str
    chart_id: Optional[str] = None
    blob_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PatternVerifySummary:
    db_present: bool = False
    chart_patterns_table_present: bool = False
    pattern_features_table_present: bool = False
    pattern_blobs_table_present: bool = False

    chart_pattern_rows: int = 0
    pattern_feature_rows: int = 0
    pattern_blob_rows: int = 0

    unique_chart_ids: int = 0
    orphan_feature_rows: int = 0
    orphan_blob_rows: int = 0
    unreadable_tables: int = 0

    usable: bool = False


def verify_chart_patterns(
    *,
    chart_patterns_db: Path,
) -> Dict[str, Any]:
    issues: List[PatternVerifyIssue] = []
    summary = PatternVerifySummary()

    if not chart_patterns_db.exists():
        return {
            "summary": asdict(summary),
            "issues": [asdict(PatternVerifyIssue(severity="error", code="chart_patterns_db_missing", details={"path": str(chart_patterns_db)}))],
        }

    summary.db_present = True

    with sqlite3.connect(str(chart_patterns_db)) as conn:
        summary.chart_patterns_table_present = _table_exists(conn, "chart_patterns")
        summary.pattern_features_table_present = _table_exists(conn, "pattern_features")
        summary.pattern_blobs_table_present = _table_exists(conn, "pattern_blobs")

        if not summary.chart_patterns_table_present:
            issues.append(PatternVerifyIssue(severity="error", code="chart_patterns_table_missing"))
            return {"summary": asdict(summary), "issues": [asdict(i) for i in issues]}

        try:
            chart_rows = _get_rows(conn, "chart_patterns")
            summary.chart_pattern_rows = len(chart_rows)
            summary.unique_chart_ids = len({str(r.get("chart_id")) for r in chart_rows if r.get("chart_id") is not None})
        except Exception as e:
            summary.unreadable_tables += 1
            issues.append(PatternVerifyIssue(severity="error", code="chart_patterns_unreadable", details={"message": f"{type(e).__name__}: {e}"}))
            return {"summary": asdict(summary), "issues": [asdict(i) for i in issues]}

        feature_rows: List[Dict[str, Any]] = []
        if summary.pattern_features_table_present:
            try:
                feature_rows = _get_rows(conn, "pattern_features")
                summary.pattern_feature_rows = len(feature_rows)
            except Exception as e:
                summary.unreadable_tables += 1
                issues.append(PatternVerifyIssue(severity="error", code="pattern_features_unreadable", details={"message": f"{type(e).__name__}: {e}"}))

        blob_rows: List[Dict[str, Any]] = []
        if summary.pattern_blobs_table_present:
            try:
                blob_rows = _get_rows(conn, "pattern_blobs")
                summary.pattern_blob_rows = len(blob_rows)
            except Exception as e:
                summary.unreadable_tables += 1
                issues.append(PatternVerifyIssue(severity="error", code="pattern_blobs_unreadable", details={"message": f"{type(e).__name__}: {e}"}))

    keyset = {
        (str(r.get("chart_id")), int(r.get("extraction_version") or 0))
        for r in chart_rows
        if r.get("chart_id") is not None
    }

    for r in feature_rows:
        key = (str(r.get("chart_id")), int(r.get("extraction_version") or 0))
        if key not in keyset:
            summary.orphan_feature_rows += 1
            issues.append(PatternVerifyIssue(severity="warning", code="orphan_pattern_feature_row", chart_id=key[0], details={"extraction_version": key[1]}))

    for r in blob_rows:
        key = (str(r.get("chart_id")), int(r.get("extraction_version") or 0))
        if key not in keyset:
            summary.orphan_blob_rows += 1
            issues.append(PatternVerifyIssue(severity="warning", code="orphan_pattern_blob_row", chart_id=key[0], blob_id=r.get("blob_id"), details={"extraction_version": key[1]}))

    if summary.chart_pattern_rows == 0:
        issues.append(PatternVerifyIssue(severity="warning", code="chart_patterns_empty"))

    summary.usable = (
        summary.db_present
        and summary.chart_patterns_table_present
        and summary.unreadable_tables == 0
        and summary.orphan_feature_rows == 0
        and summary.orphan_blob_rows == 0
    )

    return {
        "summary": asdict(summary),
        "issues": [asdict(i) for i in issues],
    }


def _json_dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser("verify_chart_patterns")
    parser.add_argument("--chart-patterns-db", default=str(DEFAULT_CHART_PATTERNS_DB))
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args(argv)

    report = verify_chart_patterns(chart_patterns_db=Path(args.chart_patterns_db))
    summary = report.get("summary", {})
    print("[PATTERNS] usable=", summary.get("usable"))
    print("[PATTERNS] chart_pattern_rows=", summary.get("chart_pattern_rows"))
    print("[PATTERNS] pattern_feature_rows=", summary.get("pattern_feature_rows"))
    print("[PATTERNS] pattern_blob_rows=", summary.get("pattern_blob_rows"))
    print("[PATTERNS] orphan_feature_rows=", summary.get("orphan_feature_rows"))
    print("[PATTERNS] orphan_blob_rows=", summary.get("orphan_blob_rows"))
    if args.json_out:
        _json_dump(Path(args.json_out), report)
    return 0 if bool(summary.get("usable")) else 1


__all__ = ["verify_chart_patterns", "cli_main"]
