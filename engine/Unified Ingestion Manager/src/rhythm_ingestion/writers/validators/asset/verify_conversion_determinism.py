from __future__ import annotations

"""
verify_conversion_determinism.py

System-level verification for deterministic type_A conversion.

Purpose
-------
This verifier checks whether current conversion output is still deterministic
with respect to persisted chart assets in chart_assets.db.

What it verifies
----------------
- For type_A assets with a reachable source_path:
  - re-run convert_chart_file_to_text(...)
  - compare the regenerated text_representation against the stored asset
  - compare regenerated content_sha256 against stored content_sha256
- For missing source files:
  - report as skipped (not hard-fail by itself)

Important
---------
- read-only only
- no database mutation
- no completed-phase modification
- only applies to type_A assets
"""

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# --------------------------------------------------
# Imports (support both sub-layer layout and flat fallback)
# --------------------------------------------------
try:
    from rhythm_ingestion.writers.converters.chart_text_converter import convert_chart_file_to_text
except ImportError:
    try:
        from ..converters.chart_text_converter import convert_chart_file_to_text
    except Exception:
        try:
            from chart_text_converter import convert_chart_file_to_text
        except Exception:
            convert_chart_file_to_text = None  # type: ignore

DEFAULT_CHART_ASSET_DB = Path("chart_assets.db")


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
class DeterminismIssue:
    severity: str  # error / warning / info
    code: str
    asset_id: Optional[str] = None
    candidate_id: Optional[str] = None
    source_path: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeterminismSummary:
    total_assets: int = 0
    type_a_assets: int = 0
    type_b_assets_skipped: int = 0

    source_files_checked: int = 0
    source_files_missing: int = 0

    exact_text_match: int = 0
    hash_match: int = 0
    text_mismatch: int = 0
    hash_mismatch: int = 0
    conversion_exceptions: int = 0

    deterministic: bool = False


# --------------------------------------------------
# Core verification
# --------------------------------------------------
def verify_conversion_determinism(
    *,
    chart_asset_db: Path,
    sample_limit: int = 20,
) -> Dict[str, Any]:
    issues: List[DeterminismIssue] = []
    summary = DeterminismSummary()

    if convert_chart_file_to_text is None:
        raise ImportError("convert_chart_file_to_text import unavailable")

    if not chart_asset_db.exists():
        raise FileNotFoundError(f"chart asset db not found: {chart_asset_db}")

    with sqlite3.connect(str(chart_asset_db)) as conn:
        if not _table_exists(conn, "chart_assets"):
            raise ValueError("chart_assets table not found")
        rows = _get_rows(conn, "chart_assets")

    summary.total_assets = len(rows)

    for row in rows:
        asset_id = row.get("asset_id")
        candidate_id = row.get("candidate_id")
        source_path_str = str(row.get("source_path") or "")
        asset_type = str(row.get("asset_type") or "")

        if asset_type != "type_A":
            summary.type_b_assets_skipped += 1
            continue

        summary.type_a_assets += 1

        if not source_path_str:
            summary.source_files_missing += 1
            issues.append(
                DeterminismIssue(
                    severity="warning",
                    code="missing_source_path_for_type_A",
                    asset_id=asset_id,
                    candidate_id=candidate_id,
                )
            )
            continue

        source_path = Path(source_path_str)
        if not source_path.exists():
            summary.source_files_missing += 1
            issues.append(
                DeterminismIssue(
                    severity="warning",
                    code="source_file_missing_for_determinism_check",
                    asset_id=asset_id,
                    candidate_id=candidate_id,
                    source_path=source_path_str,
                )
            )
            continue

        summary.source_files_checked += 1

        try:
            regenerated = convert_chart_file_to_text(source_path)
        except Exception as e:
            summary.conversion_exceptions += 1
            issues.append(
                DeterminismIssue(
                    severity="error",
                    code="conversion_exception",
                    asset_id=asset_id,
                    candidate_id=candidate_id,
                    source_path=source_path_str,
                    details={"message": f"{type(e).__name__}: {e}"},
                )
            )
            continue

        regenerated_text = regenerated.get("text_representation")
        regenerated_hash = regenerated.get("content_sha256")
        stored_text = row.get("text_representation")
        stored_hash = row.get("content_sha256")

        if regenerated_text == stored_text:
            summary.exact_text_match += 1
        else:
            summary.text_mismatch += 1
            if len([i for i in issues if i.code == "text_representation_mismatch"]) < sample_limit:
                issues.append(
                    DeterminismIssue(
                        severity="error",
                        code="text_representation_mismatch",
                        asset_id=asset_id,
                        candidate_id=candidate_id,
                        source_path=source_path_str,
                        details={
                            "stored_hash": stored_hash,
                            "regenerated_hash": regenerated_hash,
                        },
                    )
                )

        if regenerated_hash == stored_hash:
            summary.hash_match += 1
        else:
            summary.hash_mismatch += 1
            if len([i for i in issues if i.code == "content_sha256_mismatch"]) < sample_limit:
                issues.append(
                    DeterminismIssue(
                        severity="error",
                        code="content_sha256_mismatch",
                        asset_id=asset_id,
                        candidate_id=candidate_id,
                        source_path=source_path_str,
                        details={
                            "stored_hash": stored_hash,
                            "regenerated_hash": regenerated_hash,
                        },
                    )
                )

    summary.deterministic = (
        summary.text_mismatch == 0
        and summary.hash_mismatch == 0
        and summary.conversion_exceptions == 0
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
    parser = argparse.ArgumentParser("verify_conversion_determinism")
    parser.add_argument(
        "--chart-assets-db",
        default=str(DEFAULT_CHART_ASSET_DB),
        help=f"Path to chart_assets.db (default: {DEFAULT_CHART_ASSET_DB})",
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
        help="Max number of mismatch samples to include",
    )

    args = parser.parse_args(argv)

    report = verify_conversion_determinism(
        chart_asset_db=Path(args.chart_assets_db),
        sample_limit=int(args.sample_limit),
    )

    summary = report.get("summary", {})
    print("[DETERMINISM] total_assets=", summary.get("total_assets"))
    print("[DETERMINISM] type_a_assets=", summary.get("type_a_assets"))
    print("[DETERMINISM] type_b_assets_skipped=", summary.get("type_b_assets_skipped"))
    print("[DETERMINISM] source_files_checked=", summary.get("source_files_checked"))
    print("[DETERMINISM] source_files_missing=", summary.get("source_files_missing"))
    print("[DETERMINISM] exact_text_match=", summary.get("exact_text_match"))
    print("[DETERMINISM] hash_match=", summary.get("hash_match"))
    print("[DETERMINISM] text_mismatch=", summary.get("text_mismatch"))
    print("[DETERMINISM] hash_mismatch=", summary.get("hash_mismatch"))
    print("[DETERMINISM] conversion_exceptions=", summary.get("conversion_exceptions"))
    print("[DETERMINISM] deterministic=", summary.get("deterministic"))

    if args.json_out:
        _json_dump(Path(args.json_out), report)
        print("[DETERMINISM] report_written=", args.json_out)

    return 0 if bool(summary.get("deterministic")) else 1


if __name__ == "__main__":
    raise SystemExit(cli_main())


__all__ = [
    "verify_conversion_determinism",
    "cli_main",
]
