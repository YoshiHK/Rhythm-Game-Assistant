from __future__ import annotations

"""
verify_asset_pattern_reconciliation.py

System-level reconciliation verifier between:
- chart_assets.db (asset/source layer)
- chart_patterns.db (derived/pattern layer)

Purpose
-------
This verifier answers a different question from verify_chart_assets.py:
not just whether assets are valid, but whether asset-side chart knowledge and
pattern-side derived knowledge can be reconciled using available identity.

Important
---------
- read-only only
- no database mutation
- no completed-phase modification
- conservative matching only; if identity is insufficient, report that clearly
"""

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------
# Imports (support both sub-layer layout and flat fallback)
# --------------------------------------------------
try:
    from rhythm_ingestion.writers.readers.chart_pattern_reader import (
        DEFAULT_DB_PATH as DEFAULT_CHART_PATTERN_DB,
    )
except ImportError:
    try:
        from ..readers.chart_pattern_reader import DEFAULT_DB_PATH as DEFAULT_CHART_PATTERN_DB
    except Exception:
        try:
            from chart_pattern_reader import DEFAULT_DB_PATH as DEFAULT_CHART_PATTERN_DB
        except Exception:
            DEFAULT_CHART_PATTERN_DB = Path("chart_patterns.db")  # type: ignore


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


def _get_table_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    if not _table_exists(conn, table_name):
        return []
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [str(r[1]) for r in rows]


def _best_available_column(columns: Sequence[str], candidates: Sequence[str]) -> Optional[str]:
    colset = {str(c) for c in columns}
    for c in candidates:
        if c in colset:
            return c
    return None


def _choose_pattern_table(conn: sqlite3.Connection) -> Optional[str]:
    for name in ("chart_patterns", "chart_pattern_features", "patterns"):
        if _table_exists(conn, name):
            return name
    return None


# --------------------------------------------------
# Helpers
# --------------------------------------------------
def _to_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _norm_token(value: Any) -> str:
    s = _to_text(value).strip().lower()
    if not s:
        return ""
    for old, new in (("/", "-"), ("\\", "-"), (" ", "_"), ("|", ":")):
        s = s.replace(old, new)
    while "__" in s:
        s = s.replace("__", "_")
    while ":::" in s:
        s = s.replace(":::", "::")
    return s.strip("_:")


def _load_extra_metadata(row: Dict[str, Any]) -> Dict[str, Any]:
    raw = row.get("extra_metadata_json")
    if not raw:
        return {}
    try:
        out = json.loads(raw)
        return out if isinstance(out, dict) else {}
    except Exception:
        return {}


def _candidate_id_from_path(run_id: Optional[str], source_path: str) -> Optional[str]:
    if not run_id or not source_path:
        return None
    return f"{run_id}:{source_path}"


# --------------------------------------------------
# Report models
# --------------------------------------------------
@dataclass
class ReconciliationIssue:
    severity: str  # error / warning / info
    code: str
    asset_id: Optional[str] = None
    candidate_id: Optional[str] = None
    chart_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReconciliationSummary:
    total_assets: int = 0
    type_a_assets: int = 0
    type_b_assets_skipped: int = 0

    pattern_rows: int = 0
    pattern_unique_chart_ids: int = 0

    reconciled_exact_chart_id: int = 0
    reconciled_song_tuple: int = 0
    reconciled_basename_hint: int = 0
    unreconciled_assets: int = 0
    insufficient_identity_assets: int = 0

    inventory_checked: bool = False
    inventory_candidate_ids_missing_in_assets: Optional[int] = None


# --------------------------------------------------
# Pattern indexing
# --------------------------------------------------
def _build_pattern_indexes(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    idx_by_chart_id: Dict[str, List[Dict[str, Any]]] = {}
    idx_by_song_tuple: Dict[Tuple[str, str, str, str], List[Dict[str, Any]]] = {}
    idx_by_basename_hint: Dict[str, List[Dict[str, Any]]] = {}

    for row in rows:
        chart_id = _to_text(row.get("normalized_chart_id") or row.get("chart_id"))
        if chart_id:
            idx_by_chart_id.setdefault(chart_id, []).append(row)

        game = _norm_token(row.get("game"))
        song_id = _norm_token(row.get("song_id"))
        difficulty = _norm_token(row.get("difficulty"))
        level = _norm_token(row.get("level"))
        if game and song_id and difficulty:
            idx_by_song_tuple.setdefault((game, song_id, difficulty, level), []).append(row)

        # weak hint only
        for key in ("source_path", "source_file", "file_name", "basename"):
            sval = _to_text(row.get(key))
            if sval:
                idx_by_basename_hint.setdefault(Path(sval).name.lower(), []).append(row)
                if Path(sval).stem:
                    idx_by_basename_hint.setdefault(Path(sval).stem.lower(), []).append(row)

    return {
        "by_chart_id": idx_by_chart_id,
        "by_song_tuple": idx_by_song_tuple,
        "by_basename_hint": idx_by_basename_hint,
    }


# --------------------------------------------------
# Reconciliation logic
# --------------------------------------------------
def _try_reconcile_asset(
    asset_row: Dict[str, Any],
    pattern_indexes: Dict[str, Any],
) -> Tuple[str, Optional[Dict[str, Any]], Optional[str]]:
    """
    Returns:
        (strategy, matched_row, reason_if_unreconciled)

    Strategies:
      - exact_chart_id
      - song_tuple
      - basename_hint
      - unreconciled
    """
    meta = _load_extra_metadata(asset_row)

    # Strategy 1: explicit chart id / normalized chart id
    explicit_chart_id = _to_text(
        meta.get("normalized_chart_id") or meta.get("chart_id") or asset_row.get("chart_id")
    )
    if explicit_chart_id:
        matches = pattern_indexes["by_chart_id"].get(explicit_chart_id, [])
        if len(matches) == 1:
            return "exact_chart_id", matches[0], None
        if len(matches) > 1:
            return "exact_chart_id", matches[0], None
        return "unreconciled", None, "explicit_chart_id_not_found"

    # Strategy 2: (game, song_id, difficulty, level)
    game = _norm_token(asset_row.get("game_normalized") or meta.get("game") or meta.get("game_id"))
    song_id = _norm_token(asset_row.get("song_id") or meta.get("song_id"))
    difficulty = _norm_token(asset_row.get("difficulty_normalized") or meta.get("difficulty"))
    level = _norm_token(asset_row.get("level_normalized") or meta.get("level"))
    if game and song_id and difficulty:
        matches = pattern_indexes["by_song_tuple"].get((game, song_id, difficulty, level), [])
        if len(matches) == 1:
            return "song_tuple", matches[0], None
        if len(matches) > 1:
            return "song_tuple", matches[0], None
        return "unreconciled", None, "song_tuple_not_found"

    # Strategy 3: weak basename hint (only if unique)
    basename = _to_text(asset_row.get("basename") or meta.get("basename") or asset_row.get("source_path"))
    if basename:
        probe_keys = [Path(basename).name.lower()]
        if Path(basename).stem:
            probe_keys.append(Path(basename).stem.lower())
        seen = []
        for probe in probe_keys:
            seen.extend(pattern_indexes["by_basename_hint"].get(probe, []))
        # unique weak match only
        uniq = []
        uniq_keys = set()
        for r in seen:
            rid = _to_text(r.get("normalized_chart_id") or r.get("chart_id"))
            if rid and rid not in uniq_keys:
                uniq.append(r)
                uniq_keys.add(rid)
        if len(uniq) == 1:
            return "basename_hint", uniq[0], None
        if len(uniq) > 1:
            return "unreconciled", None, "basename_hint_ambiguous"

    # No enough identity to reconcile conservatively
    if not explicit_chart_id and not (game and song_id and difficulty) and not basename:
        return "unreconciled", None, "insufficient_identity"

    return "unreconciled", None, "no_conservative_match"


# --------------------------------------------------
# Public verification
# --------------------------------------------------
def verify_asset_pattern_reconciliation(
    *,
    chart_asset_db: Path = DEFAULT_CHART_ASSET_DB,
    chart_patterns_db: Path = DEFAULT_CHART_PATTERN_DB,
    file_scan_inventory_db: Optional[Path] = None,
    sample_limit: int = 20,
) -> Dict[str, Any]:
    issues: List[ReconciliationIssue] = []
    summary = ReconciliationSummary()

    # Load assets
    if not chart_asset_db.exists():
        raise FileNotFoundError(f"chart asset db not found: {chart_asset_db}")

    with sqlite3.connect(str(chart_asset_db)) as conn:
        if not _table_exists(conn, "chart_assets"):
            raise ValueError("chart_assets table not found")
        asset_rows = _get_rows(conn, "chart_assets")

    summary.total_assets = len(asset_rows)
    type_a_rows = [r for r in asset_rows if _to_text(r.get("asset_type")) == "type_A"]
    type_b_rows = [r for r in asset_rows if _to_text(r.get("asset_type")) == "type_B"]
    summary.type_a_assets = len(type_a_rows)
    summary.type_b_assets_skipped = len(type_b_rows)

    # Load patterns
    if not chart_patterns_db.exists():
        raise FileNotFoundError(f"chart patterns db not found: {chart_patterns_db}")

    with sqlite3.connect(str(chart_patterns_db)) as conn:
        table = _choose_pattern_table(conn)
        if not table:
            raise ValueError("chart pattern table not found")
        pattern_rows = _get_rows(conn, table)

    summary.pattern_rows = len(pattern_rows)
    summary.pattern_unique_chart_ids = len(
        {
            _to_text(r.get("normalized_chart_id") or r.get("chart_id"))
            for r in pattern_rows
            if _to_text(r.get("normalized_chart_id") or r.get("chart_id"))
        }
    )

    pattern_indexes = _build_pattern_indexes(pattern_rows)

    # Reconcile only type_A assets; type_B are reference-only
    for row in type_a_rows:
        strategy, matched, reason = _try_reconcile_asset(row, pattern_indexes)
        asset_id = _to_text(row.get("asset_id")) or None
        candidate_id = _to_text(row.get("candidate_id")) or None

        if matched is not None:
            chart_id = _to_text(matched.get("normalized_chart_id") or matched.get("chart_id")) or None
            if strategy == "exact_chart_id":
                summary.reconciled_exact_chart_id += 1
            elif strategy == "song_tuple":
                summary.reconciled_song_tuple += 1
            elif strategy == "basename_hint":
                summary.reconciled_basename_hint += 1
                issues.append(
                    ReconciliationIssue(
                        severity="warning",
                        code="reconciled_by_weak_basename_hint",
                        asset_id=asset_id,
                        candidate_id=candidate_id,
                        chart_id=chart_id,
                    )
                )
            continue

        # Unreconciled
        summary.unreconciled_assets += 1
        if reason == "insufficient_identity":
            summary.insufficient_identity_assets += 1
            sev = "warning"
        else:
            sev = "warning"

        issues.append(
            ReconciliationIssue(
                severity=sev,
                code=f"asset_pattern_unreconciled::{reason}",
                asset_id=asset_id,
                candidate_id=candidate_id,
                details={
                    "basename": row.get("basename"),
                    "game_normalized": row.get("game_normalized"),
                    "difficulty_normalized": row.get("difficulty_normalized"),
                    "level_normalized": row.get("level_normalized"),
                },
            )
        )

    # Optional inventory perspective: inventory candidates without ANY asset row
    if file_scan_inventory_db is not None and file_scan_inventory_db.exists():
        summary.inventory_checked = True
        with sqlite3.connect(str(file_scan_inventory_db)) as conn:
            table_name = None
            for cand in ("file_scan_inventory", "scan_candidates"):
                if _table_exists(conn, cand):
                    table_name = cand
                    break
            if table_name:
                inv_rows = _get_rows(conn, table_name)
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
                summary.inventory_candidate_ids_missing_in_assets = len(inv_candidate_ids - asset_candidate_ids)

    return {
        "summary": asdict(summary),
        "issues": [asdict(i) for i in issues[: max(sample_limit * 5, 50)]],
    }


# --------------------------------------------------
# CLI
# --------------------------------------------------
def _json_dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser("verify_asset_pattern_reconciliation")
    parser.add_argument(
        "--chart-assets-db",
        default=str(DEFAULT_CHART_ASSET_DB),
        help=f"Path to chart_assets.db (default: {DEFAULT_CHART_ASSET_DB})",
    )
    parser.add_argument(
        "--chart-patterns-db",
        default=str(DEFAULT_CHART_PATTERN_DB),
        help=f"Path to chart_patterns.db (default: {DEFAULT_CHART_PATTERN_DB})",
    )
    parser.add_argument(
        "--file-scan-db",
        default=None,
        help="Optional path to file_scan_inventory.db (inventory perspective only)",
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
        help="Max number of issue samples to include per category",
    )

    args = parser.parse_args(argv)

    report = verify_asset_pattern_reconciliation(
        chart_asset_db=Path(args.chart_assets_db),
        chart_patterns_db=Path(args.chart_patterns_db),
        file_scan_inventory_db=Path(args.file_scan_db) if args.file_scan_db else None,
        sample_limit=int(args.sample_limit),
    )

    summary = report.get("summary", {})
    print("[RECONCILE] total_assets=", summary.get("total_assets"))
    print("[RECONCILE] type_a_assets=", summary.get("type_a_assets"))
    print("[RECONCILE] type_b_assets_skipped=", summary.get("type_b_assets_skipped"))
    print("[RECONCILE] pattern_rows=", summary.get("pattern_rows"))
    print("[RECONCILE] pattern_unique_chart_ids=", summary.get("pattern_unique_chart_ids"))
    print("[RECONCILE] reconciled_exact_chart_id=", summary.get("reconciled_exact_chart_id"))
    print("[RECONCILE] reconciled_song_tuple=", summary.get("reconciled_song_tuple"))
    print("[RECONCILE] reconciled_basename_hint=", summary.get("reconciled_basename_hint"))
    print("[RECONCILE] unreconciled_assets=", summary.get("unreconciled_assets"))
    print("[RECONCILE] insufficient_identity_assets=", summary.get("insufficient_identity_assets"))
    if summary.get("inventory_checked"):
        print("[RECONCILE] inventory_candidate_ids_missing_in_assets=", summary.get("inventory_candidate_ids_missing_in_assets"))

    if args.json_out:
        _json_dump(Path(args.json_out), report)
        print("[RECONCILE] report_written=", args.json_out)

    # Non-zero only if there are unreconciled assets with enough identity to expect a match.
    hard_fail = int(summary.get("unreconciled_assets") or 0) > int(summary.get("insufficient_identity_assets") or 0)
    return 0 if not hard_fail else 1


if __name__ == "__main__":
    raise SystemExit(cli_main())


__all__ = [
    "verify_asset_pattern_reconciliation",
    "cli_main",
]
