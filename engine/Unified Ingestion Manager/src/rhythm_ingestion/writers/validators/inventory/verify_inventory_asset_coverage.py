from __future__ import annotations

"""
verify_inventory_asset_coverage.py

Cross-layer verification between file_scan_inventory.db and chart_assets.db.

Purpose
-------
Verify inventory-to-asset coverage:
- every scanned candidate should have a corresponding asset row
- detect orphan assets that do not map back to inventory

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
DEFAULT_CHART_ASSET_DB = Path("chart_assets.db")


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


def _source_key(value: Any) -> Optional[str]:
    if not value:
        return None
    return str(Path(str(value)).resolve())


@dataclass
class CoverageIssue:
    severity: str  # error / warning
    code: str
    candidate_id: Optional[str] = None
    asset_id: Optional[str] = None
    source_path: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoverageSummary:
    inventory_rows: int = 0
    asset_rows: int = 0

    inventory_candidate_ids: int = 0
    asset_candidate_ids: int = 0

    covered_inventory_candidates: int = 0
    missing_asset_for_inventory_candidates: int = 0
    orphan_asset_candidates: int = 0

    source_path_matched_rows: int = 0
    consistent: bool = False


def verify_inventory_asset_coverage(
    *,
    file_scan_inventory_db: Path,
    chart_asset_db: Path,
) -> Dict[str, Any]:
    issues: List[CoverageIssue] = []
    summary = CoverageSummary()

    if not file_scan_inventory_db.exists():
        raise FileNotFoundError(file_scan_inventory_db)
    if not chart_asset_db.exists():
        raise FileNotFoundError(chart_asset_db)

    with sqlite3.connect(str(file_scan_inventory_db)) as conn:
        inv_table = "file_scan_inventory" if _table_exists(conn, "file_scan_inventory") else "scan_candidates"
        if not _table_exists(conn, inv_table):
            raise ValueError("inventory table not found")
        inv_rows = _get_rows(conn, inv_table)

    with sqlite3.connect(str(chart_asset_db)) as conn:
        if not _table_exists(conn, "chart_assets"):
            raise ValueError("chart_assets table not found")
        asset_rows = _get_rows(conn, "chart_assets")

    summary.inventory_rows = len(inv_rows)
    summary.asset_rows = len(asset_rows)

    inv_candidate_ids = {
        str(r.get("candidate_id"))
        for r in inv_rows
        if r.get("candidate_id") is not None
    }
    asset_candidate_ids = {
        str(r.get("candidate_id"))
        for r in asset_rows
        if r.get("candidate_id") is not None
    }

    summary.inventory_candidate_ids = len(inv_candidate_ids)
    summary.asset_candidate_ids = len(asset_candidate_ids)

    missing_candidate_ids = sorted(inv_candidate_ids - asset_candidate_ids)
    summary.missing_asset_for_inventory_candidates = len(missing_candidate_ids)
    summary.covered_inventory_candidates = len(inv_candidate_ids) - len(missing_candidate_ids)

    for cid in missing_candidate_ids:
        issues.append(CoverageIssue(severity="error", code="inventory_candidate_missing_asset", candidate_id=cid))

    orphan_candidate_ids = sorted(asset_candidate_ids - inv_candidate_ids)
    summary.orphan_asset_candidates = len(orphan_candidate_ids)
    for cid in orphan_candidate_ids:
        issues.append(CoverageIssue(severity="warning", code="asset_candidate_missing_inventory", candidate_id=cid))

    # informational cross-check via normalized source path
    inv_by_source = {
        _source_key(r.get("source_path")): r
        for r in inv_rows
        if _source_key(r.get("source_path")) is not None
    }
    for row in asset_rows:
        sk = _source_key(row.get("source_path"))
        if sk and sk in inv_by_source:
            summary.source_path_matched_rows += 1

    summary.consistent = summary.missing_asset_for_inventory_candidates == 0

    return {
        "summary": asdict(summary),
        "issues": [asdict(i) for i in issues],
    }


def _json_dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser("verify_inventory_asset_coverage")
    parser.add_argument("--file-scan-db", default=str(DEFAULT_FILE_SCAN_DB))
    parser.add_argument("--chart-assets-db", default=str(DEFAULT_CHART_ASSET_DB))
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args(argv)

    report = verify_inventory_asset_coverage(
        file_scan_inventory_db=Path(args.file_scan_db),
        chart_asset_db=Path(args.chart_assets_db),
    )
    summary = report.get("summary", {})
    print("[INVENTORY ↔ ASSET] consistent=", summary.get("consistent"))
    print("[INVENTORY ↔ ASSET] inventory_rows=", summary.get("inventory_rows"))
    print("[INVENTORY ↔ ASSET] asset_rows=", summary.get("asset_rows"))
    print("[INVENTORY ↔ ASSET] covered_inventory_candidates=", summary.get("covered_inventory_candidates"))
    print("[INVENTORY ↔ ASSET] missing_asset_for_inventory_candidates=", summary.get("missing_asset_for_inventory_candidates"))
    print("[INVENTORY ↔ ASSET] orphan_asset_candidates=", summary.get("orphan_asset_candidates"))
    print("[INVENTORY ↔ ASSET] source_path_matched_rows=", summary.get("source_path_matched_rows"))
    if args.json_out:
        _json_dump(Path(args.json_out), report)
    return 0 if bool(summary.get("consistent")) else 1


__all__ = ["verify_inventory_asset_coverage", "cli_main"]
