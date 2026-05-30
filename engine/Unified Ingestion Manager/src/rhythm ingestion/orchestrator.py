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

# ------------------------------------------------------------
# Control‑plane constants
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
    Control‑plane validation only.

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

    # --------------------------------------------------------
    # 2) Game / adapter routing
    # --------------------------------------------------------
    enabled_games = get_enabled_games()
    tips_enabled_games = set(get_games_supporting_tips())

    rows: List[Dict[str, Any]] = []

    for path in files:
        game_id, matches = _detect_game_for_file(path, enabled_games)

        if only_game and game_id != only_game:
            continue

        if not game_id:
            continue

        adapter = get_adapter(game_id)
        validator = get_validator(game_id)

        payload = _try_build_payload(adapter, path)

        try:
            validator.validate(payload)
        except Exception as e:
            payload.setdefault("diagnostics", {})["validation_error"] = str(e)

        rows.append(
            {
                "game_id": game_id,
                "path": str(path),
                "payload": payload,
            }
        )

    # --------------------------------------------------------
    # 3) Writers / QA summary
    # --------------------------------------------------------
    if not dry_run:
        writer = get_writer()
        writer.write_rows(rows, db_path=db_path)

    summary = build_batch_summary(rows, tips_mode=tips_mode)

    if json_out:
        _json_dump(json_out, summary)

    log("Ingestion completed")
    return 0


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