from __future__ import annotations

"""
verify_asset_consistency.py

Internal consistency verification for chart_assets.db.

Purpose
-------
Check whether stored chart assets are internally consistent:
- unique identifiers
- hash consistency
- type_A / type_B correctness
- candidate ↔ asset mapping sanity

Scope
-----
- read-only verification
- no mutation
- no cross-layer checking (no pattern DB)
"""

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_CHART_ASSET_DB = Path("chart_assets.db")


# --------------------------------------------------
# DB helpers
# --------------------------------------------------

def _get_rows(conn: sqlite3.Connection, table: str) -> List[Dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    return [dict(r) for r in conn.execute(f"SELECT * FROM {table}")]


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table,),
    ).fetchone()
    return row is not None


# --------------------------------------------------
# Models
# --------------------------------------------------

@dataclass
class ConsistencyIssue:
    severity: str
    code: str
    asset_id: Optional[str] = None
    candidate_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsistencySummary:
    total_assets: int = 0

    duplicate_asset_ids: int = 0
    duplicate_candidate_ids: int = 0

    missing_hash_type_a: int = 0
    invalid_type_structure: int = 0

    duplicate_content_hashes: int = 0

    consistent: bool = False


# --------------------------------------------------
# Core
# --------------------------------------------------

def verify_asset_consistency(
    *,
    chart_asset_db: Path,
) -> Dict[str, Any]:

    if not chart_asset_db.exists():
        raise FileNotFoundError(chart_asset_db)

    issues: List[ConsistencyIssue] = []
    summary = ConsistencySummary()

    with sqlite3.connect(str(chart_asset_db)) as conn:
        if not _table_exists(conn, "chart_assets"):
            raise ValueError("chart_assets table missing")

        rows = _get_rows(conn, "chart_assets")

    summary.total_assets = len(rows)

    asset_id_seen = {}
    candidate_id_seen = {}
    hash_seen = {}

    for row in rows:
        asset_id = row.get("asset_id")
        candidate_id = row.get("candidate_id")
        asset_type = str(row.get("asset_type") or "")
        content_hash = row.get("content_sha256")

        # ---------------------------------
        # asset_id uniqueness
        # ---------------------------------
        if asset_id:
            asset_id_seen.setdefault(asset_id, []).append(row)
        else:
            issues.append(
                ConsistencyIssue(
                    severity="error",
                    code="missing_asset_id",
                    candidate_id=candidate_id,
                )
            )

        # ---------------------------------
        # candidate_id mapping
        # ---------------------------------
        if candidate_id:
            candidate_id_seen.setdefault(candidate_id, []).append(row)

        # ---------------------------------
        # type-specific checks
        # ---------------------------------
        if asset_type == "type_A":
            if not row.get("text_representation"):
                summary.invalid_type_structure += 1
                issues.append(
                    ConsistencyIssue(
                        severity="error",
                        code="missing_text_representation",
                        asset_id=asset_id,
                        candidate_id=candidate_id,
                    )
                )

            if not content_hash:
                summary.missing_hash_type_a += 1
                issues.append(
                    ConsistencyIssue(
                        severity="error",
                        code="missing_content_sha256",
                        asset_id=asset_id,
                        candidate_id=candidate_id,
                    )
                )

        elif asset_type == "type_B":
            if not row.get("reference_url"):
                summary.invalid_type_structure += 1
                issues.append(
                    ConsistencyIssue(
                        severity="error",
                        code="missing_reference_url",
                        asset_id=asset_id,
                        candidate_id=candidate_id,
                    )
                )

        else:
            summary.invalid_type_structure += 1
            issues.append(
                ConsistencyIssue(
                    severity="error",
                    code="invalid_asset_type",
                    asset_id=asset_id,
                    candidate_id=candidate_id,
                )
            )

        # ---------------------------------
        # content hash tracking
        # ---------------------------------
        if content_hash:
            hash_seen.setdefault(content_hash, []).append(asset_id)

    # ---------------------------------
    # duplicates detection
    # ---------------------------------

    for aid, items in asset_id_seen.items():
        if len(items) > 1:
            summary.duplicate_asset_ids += 1
            issues.append(
                ConsistencyIssue(
                    severity="error",
                    code="duplicate_asset_id",
                    asset_id=aid,
                    details={"count": len(items)},
                )
            )

    for cid, items in candidate_id_seen.items():
        if len(items) > 1:
            summary.duplicate_candidate_ids += 1
            issues.append(
                ConsistencyIssue(
                    severity="warning",
                    code="duplicate_candidate_id",
                    candidate_id=cid,
                    details={"count": len(items)},
                )
            )

    for h, ids in hash_seen.items():
        if len(ids) > 1:
            summary.duplicate_content_hashes += 1
            issues.append(
                ConsistencyIssue(
                    severity="warning",
                    code="duplicate_content_hash",
                    details={"hash": h, "asset_ids": ids},
                )
            )

    # ---------------------------------
    # final state
    # ---------------------------------
    summary.consistent = (
        summary.duplicate_asset_ids == 0
        and summary.missing_hash_type_a == 0
        and summary.invalid_type_structure == 0
    )

    return {
        "summary": asdict(summary),
        "issues": [asdict(i) for i in issues],
    }


# --------------------------------------------------
# CLI
# --------------------------------------------------

def cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser("verify_asset_consistency")

    parser.add_argument(
        "--chart-assets-db",
        default=str(DEFAULT_CHART_ASSET_DB),
    )

    parser.add_argument(
        "--json-out",
        default=None,
    )

    args = parser.parse_args(argv)

    report = verify_asset_consistency(
        chart_asset_db=Path(args.chart_assets_db),
    )

    summary = report["summary"]

    print("[CONSISTENCY] total_assets =", summary["total_assets"])
    print("[CONSISTENCY] duplicate_asset_ids =", summary["duplicate_asset_ids"])
    print("[CONSISTENCY] duplicate_candidate_ids =", summary["duplicate_candidate_ids"])
    print("[CONSISTENCY] missing_hash_type_a =", summary["missing_hash_type_a"])
    print("[CONSISTENCY] invalid_type_structure =", summary["invalid_type_structure"])
    print("[CONSISTENCY] duplicate_content_hashes =", summary["duplicate_content_hashes"])
    print("[CONSISTENCY] consistent =", summary["consistent"])

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, indent=2))

    return 0 if summary["consistent"] else 1


if __name__ == "__main__":
    raise SystemExit(cli_main())


__all__ = [
    "verify_asset_consistency",
    "cli_main",
]