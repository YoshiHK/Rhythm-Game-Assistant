from __future__ import annotations

"""
verify_pattern_blob_integrity.py

Verify pattern_blobs rows and referenced blob files.
"""

import argparse
import hashlib
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


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


@dataclass
class BlobIntegrityIssue:
    severity: str
    code: str
    blob_id: Optional[str] = None
    chart_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BlobIntegritySummary:
    blob_rows: int = 0
    missing_blob_files: int = 0
    checksum_mismatch_rows: int = 0
    unreadable_blob_files: int = 0
    invalid_json_blobs: int = 0
    consistent: bool = False


def verify_pattern_blob_integrity(*, chart_patterns_db: Path) -> Dict[str, Any]:
    issues: List[BlobIntegrityIssue] = []
    summary = BlobIntegritySummary()

    if not chart_patterns_db.exists():
        raise FileNotFoundError(chart_patterns_db)

    with sqlite3.connect(str(chart_patterns_db)) as conn:
        if not _table_exists(conn, "pattern_blobs"):
            return {"summary": asdict(summary), "issues": [asdict(BlobIntegrityIssue(severity="warning", code="pattern_blobs_table_missing"))]}
        rows = _get_rows(conn, "pattern_blobs")

    summary.blob_rows = len(rows)

    for row in rows:
        blob_id = row.get("blob_id")
        chart_id = row.get("chart_id")
        blob_path = row.get("blob_path")
        checksum = row.get("checksum")

        if not blob_path:
            summary.missing_blob_files += 1
            issues.append(BlobIntegrityIssue(severity="warning", code="missing_blob_path", blob_id=blob_id, chart_id=chart_id))
            continue

        p = Path(str(blob_path))
        if not p.exists():
            summary.missing_blob_files += 1
            issues.append(BlobIntegrityIssue(severity="warning", code="blob_file_missing", blob_id=blob_id, chart_id=chart_id, details={"blob_path": str(p)}))
            continue

        try:
            actual = _sha256_file(p)
        except Exception as e:
            summary.unreadable_blob_files += 1
            issues.append(BlobIntegrityIssue(severity="error", code="blob_file_unreadable", blob_id=blob_id, chart_id=chart_id, details={"message": f"{type(e).__name__}: {e}"}))
            continue

        if checksum and checksum != actual:
            summary.checksum_mismatch_rows += 1
            issues.append(BlobIntegrityIssue(severity="error", code="blob_checksum_mismatch", blob_id=blob_id, chart_id=chart_id, details={"stored": checksum, "actual": actual}))

        if p.suffix.lower() == ".json":
            try:
                json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                summary.invalid_json_blobs += 1
                issues.append(BlobIntegrityIssue(severity="warning", code="invalid_json_blob", blob_id=blob_id, chart_id=chart_id))

    summary.consistent = (
        summary.missing_blob_files == 0 and
        summary.checksum_mismatch_rows == 0 and
        summary.unreadable_blob_files == 0 and
        summary.invalid_json_blobs == 0
    )

    return {"summary": asdict(summary), "issues": [asdict(i) for i in issues]}


def _json_dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser("verify_pattern_blob_integrity")
    parser.add_argument("--chart-patterns-db", default=str(DEFAULT_CHART_PATTERNS_DB))
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args(argv)

    report = verify_pattern_blob_integrity(chart_patterns_db=Path(args.chart_patterns_db))
    summary = report.get("summary", {})
    print("[BLOB INTEGRITY] consistent=", summary.get("consistent"))
    print("[BLOB INTEGRITY] blob_rows=", summary.get("blob_rows"))
    print("[BLOB INTEGRITY] missing_blob_files=", summary.get("missing_blob_files"))
    print("[BLOB INTEGRITY] checksum_mismatch_rows=", summary.get("checksum_mismatch_rows"))
    print("[BLOB INTEGRITY] unreadable_blob_files=", summary.get("unreadable_blob_files"))
    print("[BLOB INTEGRITY] invalid_json_blobs=", summary.get("invalid_json_blobs"))
    if args.json_out:
        _json_dump(Path(args.json_out), report)
    return 0 if bool(summary.get("consistent")) else 1


__all__ = ["verify_pattern_blob_integrity", "cli_main"]
