#!/usr/bin/env python3
"""
Unified Multi‑Game Batch QA Runner (Phase 3)

Uses:
- utils.file_scan for filesystem discovery
- adapters for ingestion
- validators for correctness
- utils.logger for consistent logging
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any
from rhythm_ingestion.config.games_loader import get_enabled_games
from rhythm_ingestion.utils import scan_directory, log
from rhythm_ingestion.adapters import get_adapter
from rhythm_ingestion.validators import get_validator
from rhythm_ingestion.pipeline.section_metrics import build_section_feature_vector
from rhythm_ingestion.pipeline.pattern_tags import (
    dominant_tag_categories,
    count_tags_by_category,
)


def pretty(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False)


# ----------------------------------------------------------------------
# VALIDATE ONE FILE
# ----------------------------------------------------------------------
def validate_one_file(path: Path) -> Dict[str, Any]:
    """
    Auto-detect which game adapter should process this file.
    Returns structured QA result.
    """
    
    matching = []

    for game_id in get_enabled_games():
        adapter = get_adapter(game_id)
        if adapter.accepts_file(path):
            matching.append(game_id)


    if not matching:
        return {
            "file": str(path),
            "game_id": None,
            "passed": False,
            "error": "No adapters accept this file.",
            "metadata_parity": None,
        }

    if len(matching) > 1:
        return {
            "file": str(path),
            "game_id": matching,
            "passed": False,
            "error": f"Ambiguous adapters: {matching}",
            "metadata_parity": None,
        }

    game_id = matching[0]
    adapter = get_adapter(game_id)
    validator = get_validator(game_id)

    # Build canonical row
    raw = adapter.load(path)
    canonical_row = adapter.to_canonical_row(raw)

    # Build canonical payload if supported
    sections = canonical_payload.get("sections", [])
    tags = canonical_payload.get("detected_tags", [])

    section_features = build_section_feature_vector(sections)
    pattern_profile = {
        "dominant_categories": dominant_tag_categories(tags),
        "category_counts": count_tags_by_category(tags),
    }
    if hasattr(adapter, "to_canonical_payload"):
        payload = adapter.to_canonical_payload(str(path))
    else:
        payload = {"diagnostics": {}}

    # Run validator
    error_msg = None
    try:
        validator.validate(
            raw_chart=None,
            canonical_payload=payload,
            canonical_row=canonical_row,
        )
        passed = True
    except Exception as exc:
        passed = False
        error_msg = str(exc)

    diagnostics = payload.get("diagnostics", {})
    internal_meta = payload.get("internal_metadata", {})
    adapter_meta = payload.get("adapter_metadata", {})

    return {
        "file": str(path),
        "game_id": game_id,
        "passed": passed,
        "error": error_msg,
        "metadata_parity": diagnostics.get("metadata_parity"),
        "canonical_sections_version": payload.get("canonical_sections_version"),
        "adapter_version": adapter_meta.get("adapter_version"),
        "sections_source": internal_meta.get("sections_source"),
        "avg_nps": diagnostics.get("avg_nps"),
        "avg_npb": diagnostics.get("avg_npb"),
        "total_hold_coverage": diagnostics.get("total_hold_coverage"),
    }


# ----------------------------------------------------------------------
# BATCH RUN
# ----------------------------------------------------------------------
def run_batch(root: str, json_out: str | None):
    root = Path(root)
    if not root.exists():
        log(f"Error: directory not found: {root}")
        return 1

    files = scan_directory(root)
    if not files:
        log("No files found.")
        return 0

    log(f"Scanning {len(files)} files...\n")

    results = []
    per_game_counts = {}
    failure_types = {}

    for path in files:
        log(f"Validating: {path}")
        res = validate_one_file(path)
        results.append(res)

        gid = res["game_id"]
        per_game_counts.setdefault(gid, {"passed": 0, "failed": 0})

        if res["passed"]:
            per_game_counts[gid]["passed"] += 1
        else:
            per_game_counts[gid]["failed"] += 1
            if res["error"]:
                key = res["error"].split("\n")[0].strip()
                failure_types[key] = failure_types.get(key, 0) + 1

    # Summary
    log("\n========================================")
    log(" UNIFIED MULTI‑GAME QA SUMMARY")
    log("========================================")
    log(f"Total files: {len(results)}")

    for gid, stats in per_game_counts.items():
        log(f"{gid}: {stats['passed']} PASSED, {stats['failed']} FAILED")

    if failure_types:
        log("\nFailure Types:")
        for err, n in failure_types.items():
            log(f"{n} × {err}")

    if json_out:
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "total": len(results),
                    "results": results,
                    "per_game": per_game_counts,
                    "failure_types": failure_types,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        log(f"\nJSON report written to: {json_out}")

    log("\nDone.\n")
    return 0


# ----------------------------------------------------------------------
# ENTRY POINT
# ----------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage:\n"
            " python -m multi_game_batch_qa chart_dir/ [--json=report.json]"
        )
        sys.exit(1)

    json_out = None
    paths = []

    for arg in sys.argv[1:]:
        if arg.startswith("--json="):
            json_out = arg.split("=", 1)[1]
        else:
            paths.append(arg)

    if len(paths) != 1:
        print(
            "Usage:\n"
            " python -m multi_game_batch_qa chart_dir/ [--json=report.json]"
        )
        sys.exit(1)

    sys.exit(run_batch(paths[0], json_out))

