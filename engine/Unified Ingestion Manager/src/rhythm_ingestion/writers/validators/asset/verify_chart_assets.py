from __future__ import annotations

"""
verify_chart_assets.py

Verification tool for chart asset storage.

Purpose
-------
This is a SYSTEM-LEVEL verification tool (not just validation):
- reads chart_assets.db
- re-validates every stored asset via chart_asset_validator
- optionally compares coverage against file_scan_inventory.db
- emits a deterministic verification report

Scope
-----
- read-only verification
- no database mutation
- no completed-phase modification
"""

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# --------------------------------------------------
# Imports (support both sub-layer layout and flat fallback)
# --------------------------------------------------
try:
    from rhythm_ingestion.writers.models.chart_asset_model import ChartAsset
    from rhythm_ingestion.writers.validators.chart_asset_validator import validate_chart_asset
except ImportError:
    try:
        from ..models.chart_asset_model import ChartAsset
        from ..validators.chart_asset_validator import validate_chart_asset
    except Exception:
        from chart_asset_model import ChartAsset
        from chart_asset_validator import validate_chart_asset


# --------------------------------------------------
# Defaults
# --------------------------------------------------
DEFAULT_CHART_ASSET_DB = Path("chart_assets.db")
DEFAULT_FILE_SCAN_INVENTORY_DB = Path("file_scan_inventory.db")


# --------------------------------------------------
# DB helpers
# --------------------------------------------------
def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _get_rows(conn: sqlite3.Connection, table_name: str) -> List[Dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(f"SELECT * FROM {table_name}").fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------
# Report models
# --------------------------------------------------
@dataclass
class VerifyIssue:
    severity: str  # error / warning
    code: str
    asset_id: Optional[str] = None
    candidate_id: Optional[str] = None
    source_path: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerifySummary:
    total_assets: int = 0
    valid_assets: int = 0
    invalid_assets: int = 0
    warning_assets: int = 0
    coverage_expected: Optional[int] = None
    coverage_found: Optional[int] = None
    coverage_missing: Optional[int] = None
    duplicate_content_hashes: int = 0


# --------------------------------------------------
# Core verification
# --------------------------------------------------
def verify_chart_assets(
    *,
    chart_asset_db: Path,
    file_scan_inventory_db: Optional[Path] = None,
    sample_limit: int = 20,
) -> Dict[str, Any]:
    issues: List[VerifyIssue] = []
    summary = VerifySummary()

    if not chart_asset_db.exists():
        raise FileNotFoundError(f"chart asset db not found: {chart_asset_db}")

    with sqlite3.connect(str(chart_asset_db)) as conn:
        if not _table_exists(conn, "chart_assets"):
            raise ValueError("chart_assets table not found")
        asset_rows = _get_rows(conn, "chart_assets")

    summary.total_assets = len(asset_rows)

    # Validate every stored asset
    seen_hashes: Dict[str, List[str]] = {}
    warning_asset_ids: set[str] = set()

    for row in asset_rows:
        asset = ChartAsset.from_record(row)
        result = validate_chart_asset(asset)

        if result.is_valid:
            summary.valid_assets += 1
        else:
            summary.invalid_assets += 1
            for err in result.fatal_errors:
                issues.append(
                    VerifyIssue(
                        severity="error",
                        code="asset_validation_failed",
                        asset_id=asset.asset_id,
                        candidate_id=asset.candidate_id,
                        source_path=asset.source_path,
                        details={"message": err},
                    )
                )

        if result.warnings:
            warning_asset_ids.add(asset.asset_id)
            for w in result.warnings:
                issues.append(
                    VerifyIssue(
                        severity="warning",
                        code="asset_validation_warning",
                        asset_id=asset.asset_id,
                        candidate_id=asset.candidate_id,
                        source_path=asset.source_path,
                        details={"message": w},
                    )
                )

        # Additional verify-only checks
        if asset.asset_type == "type_A":
            if not asset.text_representation:
                issues.append(
                    VerifyIssue(
                        severity="error",
                        code="missing_text_representation",
                        asset_id=asset.asset_id,
                        candidate_id=asset.candidate_id,
                        source_path=asset.source_path,
                    )
                )
            elif not asset.text_representation.startswith("# CHART_ASSET_TEXT v1"):
                issues.append(
                    VerifyIssue(
                        severity="warning",
                        code="unexpected_text_envelope",
                        asset_id=asset.asset_id,
                        candidate_id=asset.candidate_id,
                        source_path=asset.source_path,
                    )
                )

        if asset.content_sha256:
            seen_hashes.setdefault(asset.content_sha256, []).append(asset.asset_id)

    summary.warning_assets = len(warning_asset_ids)

    # Duplicate content hash detection
    dup_hashes = {h: ids for h, ids in seen_hashes.items() if len(ids) > 1}
    summary.duplicate_content_hashes = len(dup_hashes)
    for h, ids in dup_hashes.items():
        issues.append(
            VerifyIssue(
                severity="warning",
                code="duplicate_content_sha256",
                details={"content_sha256": h, "asset_ids": ids},
            )
        )

    # Optional coverage check against file_scan_inventory
    if file_scan_inventory_db is not None and file_scan_inventory_db.exists():
        with sqlite3.connect(str(file_scan_inventory_db)) as conn:
            table_name = None
            for cand in ("file_scan_inventory", "scan_candidates"):
                if _table_exists(conn, cand):
                    table_name = cand
                    break
            if table_name:
                inv_rows = _get_rows(conn, table_name)
                summary.coverage_expected = len(inv_rows)

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

                summary.coverage_found = len(asset_candidate_ids)
                missing = sorted(inv_candidate_ids - asset_candidate_ids)
                summary.coverage_missing = len(missing)

                for cid in missing[:sample_limit]:
                    issues.append(
                        VerifyIssue(
                            severity="warning",
                            code="inventory_candidate_missing_chart_asset",
                            candidate_id=cid,
                        )
                    )

    return {
        "summary": asdict(summary),
        "issues": [asdict(i) for i in issues],
    }


# --------------------------------------------------
# CLI
# --------------------------------------------------
def _json_dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser("verify_chart_assets")
    parser.add_argument(
        "--chart-assets-db",
        default=str(DEFAULT_CHART_ASSET_DB),
        help=f"Path to chart_assets.db (default: {DEFAULT_CHART_ASSET_DB})",
    )
    parser.add_argument(
        "--file-scan-db",
        default=None,
        help="Optional path to file_scan_inventory.db for coverage verification",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="Optional path to write JSON verification report",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=20,
        help="Max sample missing candidates to include",
    )

    args = parser.parse_args(argv)

    report = verify_chart_assets(
        chart_asset_db=Path(args.chart_assets_db),
        file_scan_inventory_db=Path(args.file_scan_db) if args.file_scan_db else None,
        sample_limit=int(args.sample_limit),
    )

    summary = report.get("summary", {})
    print("[VERIFY] total_assets=", summary.get("total_assets"))
    print("[VERIFY] valid_assets=", summary.get("valid_assets"))
    print("[VERIFY] invalid_assets=", summary.get("invalid_assets"))
    print("[VERIFY] warning_assets=", summary.get("warning_assets"))
    print("[VERIFY] duplicate_content_hashes=", summary.get("duplicate_content_hashes"))
    if summary.get("coverage_expected") is not None:
        print("[VERIFY] coverage_expected=", summary.get("coverage_expected"))
        print("[VERIFY] coverage_found=", summary.get("coverage_found"))
        print("[VERIFY] coverage_missing=", summary.get("coverage_missing"))

    if args.json_out:
        _json_dump(Path(args.json_out), report)
        print("[VERIFY] report_written=", args.json_out)

    # exit non-zero if hard errors exist
    return 0 if int(summary.get("invalid_assets") or 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(cli_main())


__all__ = [
    "verify_chart_assets",
    "cli_main",
]
