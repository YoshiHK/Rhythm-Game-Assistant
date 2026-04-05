#!/usr/bin/env python3
"""
Unified Multi‑Game Ingestion CLI (Phase 3)

This is a thin CLI wrapper around the UMI ingestion flow:
- file discovery (utils.file_scan)
- game detection (config/games.json)
- adapters + validators
- tips generation (Phase 1–2, if supported)
- batch‑level tips summaries
- QA reporting
- Excel DB writing or dry‑run

This file intentionally does NOT re‑implement the orchestrator;
it follows the same architectural rules.
"""

from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Dict, Any, List

from rhythm_ingestion.config.games_loader import (
    get_enabled_games,
    get_games_supporting_tips,
)
from rhythm_ingestion.utils import scan_directory, log
from rhythm_ingestion.adapters import get_adapter
from rhythm_ingestion.validators import get_validator
from rhythm_ingestion.writers import get_writer
from rhythm_ingestion.utils.qa_reporter import QASummary

from rhythm_ingestion.pipeline.section_metrics import build_section_feature_vector
from rhythm_ingestion.pipeline.pattern_tags import (
    dominant_tag_categories,
    count_tags_by_category,
)

from rhythm_ingestion.pipeline.tips import (
    run_for_chart,
    build_batch_summary,
)

def _mean(nums: List[float]) -> float:
    return (sum) / len(nums)) if nums else 0.0


def _aggregate_section_features(section_features_list: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Aggregate list[section_feature_vector] -> mean per key (numeric only).
    Returns {} if no usable numeric features exist.
    """
    if not section_features_list:
        return {}

    # Union of keys across dicts
    keys = set()
    for d in section_features_list:
        if isinstance(d, dict):
            keys.update(d.keys())

    out: Dict[str, float] = {}
    for k in sorted(keys):
        vals: List[float] = []
        for d in section_features_list:
            if not isinstance(d, dict):
                continue
            v = d.get(k)
            if isinstance(v, (int, float)):
                vals.append(float(v))
        # Only include keys that had at least one numeric value
        if vals:
            out[k] = _mean(vals)

    return out


def _aggregate_pattern_profiles(pattern_profiles_list: List[Dict[str, Any]], *, top_k: int = 3) -> Dict[str, Any]:
    """
    Aggregate list[pattern_profile] -> summed category_counts + top dominant categories + shares.
    pattern_profile is expected like:
      { "dominant_categories": [...], "category_counts": {cat: count, ...} }
    """
    if not pattern_profiles_list:
        return {"dominant_categories": [], "category_counts": {}, "category_shares": {}}

    # Sum category counts across charts
    counts: Dict[str, int] = {}
    for prof in pattern_profiles_list:
        if not isinstance(prof, dict):
            continue
        cc = prof.get("category_counts") or {}
        if not isinstance(cc, dict):
            continue
        for cat, cnt in cc.items():
            if not isinstance(cat, str) or not cat:
                continue
            if isinstance(cnt, (int, float)):
                counts[cat] = counts.get(cat, 0) + int(cnt)

    total = sum(counts.values())
    dominant = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    dominant_categories = [c for c, _ in dominant[: max(1, int(top_k))]] if counts else []

    shares: Dict[str, float] = {}
    if total > 0:
        for cat, cnt in counts.items():
            shares[cat] = float(cnt) / float(total)

    return {
        "dominant_categories": dominant_categories,
        "category_counts": counts,
        "category_shares": shares,
    }


# ------------------------------------------------------------
# Ingest one chart
# ------------------------------------------------------------
def ingest_one_chart(path: Path):
    enabled_games = get_enabled_games()

    matching = []
    for game_id in enabled_games:
        adapter = get_adapter(game_id)
        if adapter.accepts_file(path):
            matching.append(game_id)

    if not matching:
        return None, None, None, "No adapters accept this file"
    if len(matching) > 1:
        return None, None, None, f"Ambiguous adapters: {matching}"

    game_id = matching[0]
    adapter = get_adapter(game_id)
    validator = get_validator(game_id)

    raw = adapter.load(path)
    canonical_row = adapter.to_canonical_row(raw)

    if hasattr(adapter, "to_canonical_payload"):
        canonical_payload = adapter.to_canonical_payload(str(path))
    else:
        canonical_payload = {"diagnostics": {}}

    try:
        validator.validate(
            raw_chart=raw,
            canonical_payload=canonical_payload,
            canonical_row=canonical_row,
        )
        error = None
    except Exception as exc:
        error = str(exc)

    return game_id, canonical_row, canonical_payload, error


# ------------------------------------------------------------
# Batch ingestion
# ------------------------------------------------------------
def run_ingestion(
    charts_root: str,
    *,
    db_path: str | None,
    json_out: str | None,
    dry_run: bool,
):
    root = Path(charts_root)
    if not root.exists():
        log(f"Error: directory not found: {root}")
        return 1

    files = scan_directory(root)
    if not files:
        log("No files found.")
        return 0

    enabled_games = get_enabled_games()
    tips_games = set(get_games_supporting_tips())

    writer = get_writer(
        kind="noop" if dry_run else "excel",
        db_path=db_path,
    )

    qa = QASummary(
        total_charts=0,
        total_success=0,
        total_failed=0,
        by_game={},
        failures=[],
        metadata_stats={},
    )

    batch_accumulator: Dict[str, Dict[str, Dict[str, list]]] = {}
    results: List[Dict[str, Any]] = []

    log(f"Processing {len(files)} charts...\n")

    for f in files:
        log(f"[Ingest] {f}")
        game_id, row, payload, error = ingest_one_chart(f)

        qa.total_charts += 1
        qa.by_game.setdefault(game_id, {"success": 0, "failed": 0})

        if error:
            qa.total_failed += 1
            qa.by_game[game_id]["failed"] += 1
            qa.failures.append(
                {"game_id": game_id, "song_id": row.get("song_id") if row else None, "error": error}
            )
        else:
            qa.total_success += 1
            qa.by_game[game_id]["success"] += 1

            # Tips generation (per-chart)
            if game_id in tips_games:
                run_for_chart(
                    game_id=game_id,
                    canonical_payload=payload,
                    canonical_row=row,
                    mode="production",
                    attach_to_payload=True,
                )

                difficulty = row.get("difficulty_label")
                chart_summary = payload.get("chart_summary")
                tips_text = payload.get("tips_text")
                


                if difficulty and chart_summary:
                    sections = payload.get("sections", []) or []
                    tags = payload.get("detected_tags", []) or []
                    
                    section_features = build_section_feature_vector(sections)
                    pattern_profile = {
                        "dominant_categories": dominant_tag_categories(tags),
                        "category_counts": count_tags_by_category(tags),
                    }
                    
                    batch_accumulator \
                        .setdefault(game_id, {}) \
                        .setdefault(difficulty, {"chart_summaries": [], "tips_texts": []})

                    batch_accumulator[game_id][difficulty]["chart_summaries"].append(chart_summary)

                    batch_accumulator[game_id][difficulty] \
                        .setdefault("section_features", []).append(section_features)

                    batch_accumulator[game_id][difficulty] \
                        .setdefault("pattern_profiles", []).append(pattern_profile)
                    
                    if isinstance(tips_text, str):
                        batch_accumulator[game_id][difficulty]["tips_texts"].append(tips_text)

            if not dry_run:
                writer.insert_row(game_id, row)

        results.append(
            {
                "file": str(f),
                "game_id": game_id,
                "passed": error is None,
                "error": error,
            }
        )

if not dry_run:
    writer.save()

    # ------------------------------------------------------------
    # Batch-level tips summaries
    # ------------------------------------------------------------
    base_summary = build_batch_summary(
    difficulty=difficulty,
    per_chart_summaries=data["chart_summaries"],
    tips_texts=data["tips_texts"],
    )

    # --- NEW: compact batch difficulty profile (additive) ---
    section_feature_profile = _aggregate_section_features(data.get("section_features", []))
    pattern_profile = _aggregate_pattern_profiles(data.get("pattern_profiles", []), top_k=3)

    base_summary["difficulty_profile_version"] = "v1"
    base_summary["difficulty_profile"] = {
        "section_features_mean": section_feature_profile,
        "pattern_profile": pattern_profile,
        "chart_count": base_summary.get("chart_count", len(data.get("chart_summaries", []))),
    }

    batch_tips_summaries.setdefault(game_id, {})[difficulty] = base_summary
        except Exception as exc:
            log(f"[{game_id}][{difficulty}] Batch summary failed: {exc}")

    # ------------------------------------------------------------
    # Output
    # ------------------------------------------------------------
    log("\n===============================")
    log(" UNIFIED INGESTION SUMMARY")
    log("===============================")
    log(f"Total charts: {qa.total_charts}")
    log(f"Success: {qa.total_success}")
    log(f"Failed: {qa.total_failed}")

    if json_out:
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "results": results,
                    "qa": qa.to_json_dict(),
                    "batch_tips_summaries": batch_tips_summaries,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )
        log(f"\nJSON report written to: {json_out}")

    log("\nDone.\n")
    return 0


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------
if __name__ == "__main__":
    charts_root = None
    db_path = None
    json_path = None
    dry = False

    for arg in sys.argv[1:]:
        if arg.startswith("--db="):
            db_path = arg.split("=", 1)[1]
        elif arg.startswith("--json="):
            json_path = arg.split("=", 1)[1]
        elif arg == "--dry-run":
            dry = True
        else:
            charts_root = arg

    if charts_root is None:
        print(
            "Usage:\n"
            " python multi_game_ingest.py chart_dir/ "
            "[--db=SongDB.xlsx] [--json=report.json] [--dry-run]"
        )
        sys.exit(1)

    sys.exit(
        run_ingestion(
            charts_root,
            db_path=db_path,
            json_out=json_path,
            dry_run=dry,
        )
    )
