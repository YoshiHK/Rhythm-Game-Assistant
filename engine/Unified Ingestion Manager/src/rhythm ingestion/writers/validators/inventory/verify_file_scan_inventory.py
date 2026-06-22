from __future__ import annotations

"""
verify_file_scan_inventory.py

System-level verification for file_scan_inventory.db.

Purpose
-------
Verify that file_scan_inventory.db is structurally present, readable,
and internally consistent enough to support downstream asset/pattern coverage checks.

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

DEFAULT_FILE_SCAN_DB = Path("file_scan_inventory.db")


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
class InventoryVerifyIssue:
    severity: str  # error / warning
    code: str
    candidate_id: Optional[str] = None
    source_path: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InventoryVerifySummary:
    db_present: bool = False
    table_present: bool = False
    total_rows: int = 0
    unreadable_table: bool = False

    missing_candidate_id_rows: int = 0
    missing_source_path_rows: int = 0
    missing_normalized_key_rows: int = 0
    invalid_normalization_issues_json_rows: int = 0
    source_path_missing_on_disk_rows: int = 0
    duplicate_normalized_key_within_run: int = 0

    usable: bool = False


def verify_file_scan_inventory(*, file_scan_inventory_db: Path) -> Dict[str, Any]:
    issues: List[InventoryVerifyIssue] = []
    summary = InventoryVerifySummary()

    if not file_scan_inventory_db.exists():
        return {
            "summary": asdict(summary),
            "issues": [
                asdict(
                    InventoryVerifyIssue(
                        severity="error",
                        code="file_scan_inventory_db_missing",
                        details={"path": str(file_scan_inventory_db)},
                    )
                )
            ],
        }

    summary.db_present = True

    with sqlite3.connect(str(file_scan_inventory_db)) as conn:
        summary.table_present = _table_exists(conn, "file_scan_inventory") or _table_exists(conn, "scan_candidates")
        table_name = "file_scan_inventory" if _table_exists(conn, "file_scan_inventory") else "scan_candidates"

        if not summary.table_present:
            issues.append(InventoryVerifyIssue(severity="error", code="inventory_table_missing"))
            return {"summary": asdict(summary), "issues": [asdict(i) for i in issues]}

        try:
            rows = _get_rows(conn, table_name)
        except Exception as e:
            summary.unreadable_table = True
            issues.append(
                InventoryVerifyIssue(
                    severity="error",
                    code="inventory_table_unreadable",
                    details={"message": f"{type(e).__name__}: {e}"},
                )
            )
            return {"summary": asdict(summary), "issues": [asdict(i) for i in issues]}

    summary.total_rows = len(rows)

    seen_run_norm: Dict[tuple[str, str], int] = {}

    for row in rows:
        candidate_id = row.get("candidate_id")
        source_path = row.get("source_path")
        normalized_key = row.get("normalized_key")
        run_id = str(row.get("run_id") or "")

        if not candidate_id:
            summary.missing_candidate_id_rows += 1
            issues.append(InventoryVerifyIssue(severity="error", code="missing_candidate_id", source_path=source_path))

        if not source_path:
            summary.missing_source_path_rows += 1
            issues.append(InventoryVerifyIssue(severity="error", code="missing_source_path", candidate_id=candidate_id))
        else:
            p = Path(str(source_path))
            if not p.exists():
                summary.source_path_missing_on_disk_rows += 1
                issues.append(
                    InventoryVerifyIssue(
                        severity="warning",
                        code="source_path_missing_on_disk",
                        candidate_id=candidate_id,
                        source_path=str(source_path),
                    )
                )

        if not normalized_key:
            summary.missing_normalized_key_rows += 1
            issues.append(InventoryVerifyIssue(severity="error", code="missing_normalized_key", candidate_id=candidate_id, source_path=source_path))
        else:
            key = (run_id, str(normalized_key))
            seen_run_norm[key] = seen_run_norm.get(key, 0) + 1

        ni = row.get("normalization_issues_json")
        if ni:
            try:
                parsed = json.loads(ni)
                if not isinstance(parsed, (list, dict)):
                    raise ValueError("normalization_issues_json must decode to list/dict")
            except Exception:
                summary.invalid_normalization_issues_json_rows += 1
                issues.append(
                    InventoryVerifyIssue(
                        severity="warning",
                        code="invalid_normalization_issues_json",
                        candidate_id=candidate_id,
                        source_path=source_path,
                    )
                )

    for (run_id, normalized_key), count in seen_run_norm.items():
        if count > 1:
            summary.duplicate_normalized_key_within_run += 1
            issues.append(
                InventoryVerifyIssue(
                    severity="warning",
                    code="duplicate_normalized_key_within_run",
                    details={"run_id": run_id, "normalized_key": normalized_key, "count": count},
                )
            )

    if summary.total_rows == 0:
        issues.append(InventoryVerifyIssue(severity="warning", code="inventory_empty"))

    summary.usable = (
        summary.db_present
        and summary.table_present
        and not summary.unreadable_table
        and summary.missing_candidate_id_rows == 0
        and summary.missing_source_path_rows == 0
        and summary.missing_normalized_key_rows == 0
    )

    return {
        "summary": asdict(summary),
        "issues": [asdict(i) for i in issues],
    }


def _json_dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser("verify_file_scan_inventory")
    parser.add_argument("--file-scan-db", default=str(DEFAULT_FILE_SCAN_DB))
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args(argv)

    report = verify_file_scan_inventory(file_scan_inventory_db=Path(args.file_scan_db))
    summary = report.get("summary", {})
    print("[SCAN INVENTORY] usable=", summary.get("usable"))
    print("[SCAN INVENTORY] total_rows=", summary.get("total_rows"))
    print("[SCAN INVENTORY] missing_candidate_id_rows=", summary.get("missing_candidate_id_rows"))
    print("[SCAN INVENTORY] missing_source_path_rows=", summary.get("missing_source_path_rows"))
    print("[SCAN INVENTORY] missing_normalized_key_rows=", summary.get("missing_normalized_key_rows"))
    print("[SCAN INVENTORY] invalid_normalization_issues_json_rows=", summary.get("invalid_normalization_issues_json_rows"))
    print("[SCAN INVENTORY] source_path_missing_on_disk_rows=", summary.get("source_path_missing_on_disk_rows"))
    print("[SCAN INVENTORY] duplicate_normalized_key_within_run=", summary.get("duplicate_normalized_key_within_run"))
    if args.json_out:
        _json_dump(Path(args.json_out), report)
    return 0 if bool(summary.get("usable")) else 1


__all__ = ["verify_file_scan_inventory", "cli_main"]
