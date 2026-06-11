#!/usr/bin/env python3
"""
PHASE 3 CONTRACT — Unified Ingestion Orchestrator (UMI)

This file is the authoritative coordination layer for Phase 3 of the
Rhythm Game Assistant pipeline.

(Completed Phases 1–2 MUST remain unchanged.)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rhythm_ingestion.config.games_loader import (
    get_enabled_games,
    get_games_supporting_tips,
)
from rhythm_ingestion.utils import scan_directory, log
from rhythm_ingestion.adapters import get_adapter
from rhythm_ingestion.validators import get_validator
from rhythm_ingestion.writers import get_writer
from rhythm_ingestion.pipeline.tips import build_batch_summary
from rhythm_ingestion.pipeline.section_metrics import build_section_feature_vector
from rhythm_ingestion.pipeline.pattern_tags import (
    dominant_tag_categories,
    count_tags_by_category,
)
from rhythm_ingestion.pipeline.pattern_tags.pattern_tags_taxonomy import (
    PatternTagsTaxonomy,
)
from rhythm_ingestion.runtime_meta import RuntimeMetaManager

# ------------------------------------------------------------
# Control-plane constants
# ------------------------------------------------------------

DEFAULT_CHART_ROOT = (
    r"C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Chart File"
)

SUPPORTED_CHART_EXTENSIONS = {
    ".html",
    ".htm",
    ".svg",
    ".json",
    ".txt",
    ".mht",
}

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _json_dump(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)



def _filter_supported_extensions(
    paths: List[Path],
) -> Tuple[List[Path], List[Path]]:
    """
    Control-plane validation only.

    Returns:
      (supported_files, excluded_files)

    No semantic decisions are made here.
    """
    supported: List[Path] = []
    excluded: List[Path] = []

    for p in paths:
        try:
            if p.suffix.lower() in SUPPORTED_CHART_EXTENSIONS:
                supported.append(p)
            else:
                excluded.append(p)
        except Exception:
            excluded.append(p)

    return supported, excluded


def _detect_game_for_file(
    file_path: Path,
    enabled_game_ids: List[str],
) -> Tuple[Optional[str], List[str]]:
    """
    Detect which enabled game adapter accepts this file.

    Returns:
      (chosen_game_id or None, matching_game_ids)
    """
    matches: List[str] = []

    for gid in enabled_game_ids:
        try:
            adapter = get_adapter(gid)
            if adapter.accepts_file(file_path):
                matches.append(gid)
        except Exception:
            continue

    if not matches:
        return None, []

    return matches[0], matches


def _try_build_payload(adapter: Any, path: Path) -> Dict[str, Any]:
    if hasattr(adapter, "to_canonical_payload"):
        try:
            return adapter.to_canonical_payload(str(path))
        except Exception:
            return {"diagnostics": {}}
    return {"diagnostics": {}}


# ------------------------------------------------------------
# Core ingest loop
# ------------------------------------------------------------

def ingest(
    source_dir: str,
    *,
    db_path: Optional[str],
    dry_run: bool,
    only_game: Optional[str],
    json_out: Optional[str],
    tips_mode: str,
) -> int:
    src = Path(source_dir)
    
    # ❌ no runtime here

    if not src.exists():
        log(f"Error: directory not found: {src}")
        return 1

    # --------------------------------------------------------
    # 1) File scan (recursive)
    # --------------------------------------------------------
    all_files = scan_directory(
        src,
        allowed_extensions=sorted(SUPPORTED_CHART_EXTENSIONS),
    )

    files, excluded = _filter_supported_extensions(all_files)

    if excluded:
        log(
            f"Excluded {len(excluded)} files with unsupported extensions "
            f"(out of {len(all_files)} total files scanned)"
        )

    log(f"Candidate chart files after filtering: {len(files)}")
    
    total = len(files)

    for idx, file_path in enumerate(files):

        if idx % 100 == 0:
            log(f"[INGEST PROGRESS] {idx}/{total} current={file_path}") 
    
    # --------------------------------------------------------
    # Resolve artifact paths (NEW)
    # --------------------------------------------------------
    resolved_db_path = db_path or str(runtime.build_artifact_path("song_db"))
    resolved_json_out = json_out or str(runtime.build_artifact_path("song_db_meta"))

    # --------------------------------------------------------
    # 2) Game / adapter routing
    # --------------------------------------------------------
    enabled_games = get_enabled_games()
    tips_enabled_games = set(get_games_supporting_tips())

    rows: List[Dict[str, Any]] = []
    
    route_none_count = 0
    canonical_error_count = 0
    canonical_error_samples: List[str] = []

    for path in files:
        game_id, matches = _detect_game_for_file(path, enabled_games)

        if only_game and game_id != only_game:
            continue

        if not game_id:
            route_none_count += 1
            continue

        adapter = get_adapter(game_id)
        validator = get_validator(game_id)

        payload = _try_build_payload(adapter, path)

        try:
            validator.validate(payload)
        except Exception as e:
            payload.setdefault("diagnostics", {})["validation_error"] = str(e)

        try:
            canonical_row = adapter.to_canonical_row(payload)
        except Exception as e:
            canonical_error_count += 1
            if len(canonical_error_samples) < 10:
                canonical_error_samples.append(f"{path.name}: {repr(e)}")
            log(f"canonical_row error for {path}: {e}")
            continue

        rows.append(
            {
                "game_id": game_id,
                "canonical_row": canonical_row,
            }
        )
    
    log(f"[INGEST] rows={len(rows)} route_miss={route_none_count} errors={canonical_error_count}")

    if canonical_error_samples:
        print("CANONICAL_ERROR_SAMPLES:")
        for item in canonical_error_samples:
            print("  ", item)

    # --------------------------------------------------------
    # 3) Writers / QA summary
    # --------------------------------------------------------
    if not dry_run:
        writer = get_writer()
        writer.write_rows(rows, db_path=resolved_db_path)

    summary = build_batch_summary(rows, tips_mode=tips_mode)
    
    batch_summary = summary
    log("Batch summary generated")
    
    # --------------------------------------------------------
    # Build song_db_meta
    # --------------------------------------------------------
    by_game = {}
    for item in rows:
        gid = item.get("game_id")
        if not gid:
            continue
        slot = by_game.setdefault(gid, {"files": 0, "rows": 0, "failures": 0})
        slot["files"] += 1
        slot["rows"] += 1

    from datetime import datetime, timezone

    song_db_meta = {
        "report_type": "song_db_meta",
        "report_date": Path(resolved_json_out).parent.parent.name,
        "run_id": Path(resolved_json_out).parent.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),

        "db_file": Path(resolved_db_path).name,

        "summary": {
            "total_files_scanned": len(files),
            "total_supported_files": len(files),
            "rows_built": len(rows),
            "rows_written": len(rows) if not dry_run else 0,
        },

        "validation": {
            "routing_failures": route_none_count,
            "adapter_failures": 0,
            "canonical_row_errors": canonical_error_count,
            "validation_errors": 0,
        },

        "by_game": by_game,

        "data_quality": {},
        "lookup_stats": {},

        "integrity": {
            "schema_version": 1,
        },
    }

    # --------------------------------------------------------
    # SINGLE WRITE ONLY (NO FALLBACK, NO DUPLICATION)
    # --------------------------------------------------------
    if json_out:
        _json_dump(resolved_json_out, song_db_meta)
    else:
        raise ValueError("json_out must be provided for song_db_meta")

    log("Ingestion completed")

    # --------------------------------------------------------
    # CLEAN RETURN CONTRACT
    # --------------------------------------------------------
    return {
        "status_code": 0,
        "rows": rows,
        "batch_summary": batch_summary
    }


# ------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser("Unified Ingestion Orchestrator (UMI)")

    parser.add_argument(
        "--source",
        required=False,
        default=DEFAULT_CHART_ROOT,
        help=(
            "Directory containing raw chart files "
            f"(default: {DEFAULT_CHART_ROOT})"
        ),
    )
    parser.add_argument(
        "--db",
        required=False,
        help="Path to Song Database (full).xlsx (required unless --dry-run)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without writing to Excel DB",
    )
    parser.add_argument(
        "--game",
        required=False,
        help="Restrict run to a single enabled game_id from games.json",
    )
    parser.add_argument(
        "--json",
        required=False,
        help="Write run report to JSON path",
    )
    parser.add_argument(
        "--tips-mode",
        default="production",
        choices=["production", "debug"],
        help="Tips generation mode (only for games that support tips)",
    )

    args = parser.parse_args()

    ingest(
        args.source,
        db_path=args.db,
        dry_run=args.dry_run,
        only_game=args.game,
        json_out=args.json,
        tips_mode=args.tips_mode,
    )


if __name__ == "__main__":
    main()
