#!/usr/bin/env python3
from __future__ import annotations

"""
Unified Multi-Game Ingestion CLI (Phase 3)
Thin CLI wrapper around the UMI ingestion flow.

Goals:
- expose a stable batch façade over the authoritative orchestrator.ingest()
- provide lightweight helper functions for future batch aggregation use
- avoid duplicating orchestration logic that already lives in orchestrator.py
"""

import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

from rhythm_ingestion.orchestrator import ingest as orchestrator_ingest
from rhythm_ingestion.config.games_loader import (
    get_enabled_games,
    get_games_supporting_tips,
)
from rhythm_ingestion.pipeline.pattern_tags import (
    dominant_tag_categories,
    count_tags_by_category,
)


def _mean(nums: List[float]) -> float:
    return sum(nums) / len(nums) if nums else 0.0


def _aggregate_section_features(
    section_features_list: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Aggregate list[section_feature_vector] -> mean per numeric key.
    """
    if not section_features_list:
        return {}

    out: Dict[str, List[float]] = {}
    for feat in section_features_list:
        for k, v in feat.items():
            if isinstance(v, (int, float)):
                out.setdefault(k, []).append(float(v))

    return {k: _mean(v) for k, v in out.items()}


def _aggregate_pattern_profiles(
    pattern_profiles_list: List[Dict[str, Any]],
    *,
    top_k: int = 3,
) -> Dict[str, Any]:
    """
    Aggregate list[pattern_profile] into a lightweight batch summary.

    Current behavior:
    - if no usable category counts are present, returns empty summary
    - otherwise merges category counts and computes simple shares
    """
    if not pattern_profiles_list:
        return {
            "dominant_categories": [],
            "category_counts": {},
            "category_shares": {},
        }

    merged_counts: Dict[str, int] = {}

    for item in pattern_profiles_list:
        if not isinstance(item, dict):
            continue

        counts = item.get("category_counts")
        if isinstance(counts, dict):
            for k, v in counts.items():
                try:
                    merged_counts[k] = merged_counts.get(k, 0) + int(v)
                except Exception:
                    continue

    total = sum(merged_counts.values())
    shares = {
        k: (v / total if total > 0 else 0.0)
        for k, v in merged_counts.items()
    }

    dominant = sorted(
        merged_counts.items(),
        key=lambda kv: (-kv[1], kv[0])
    )[:top_k]

    return {
        "dominant_categories": [k for k, _ in dominant],
        "category_counts": merged_counts,
        "category_shares": shares,
    }


def ingest_one_chart(path: Path) -> Dict[str, Any]:
    """
    Lightweight per-chart façade for future callers.

    This helper does NOT try to replace the authoritative orchestration path.
    It only returns structured context about the chart path and current
    enablement configuration.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Chart file not found: {p}")

    return {
        "path": str(p),
        "exists": True,
        "enabled_games": list(get_enabled_games()),
        "tips_supported_games": list(get_games_supporting_tips()),
        "note": "Use run_ingestion() for authoritative batch execution.",
    }


def run_ingestion(
    charts_root: str,
    *,
    db_path: str | None = None,
    json_out: str | None = None,
    dry_run: bool = False,
):
    """
    Batch façade over the authoritative orchestrator.ingest().
    """
    return orchestrator_ingest(
        source_dir=charts_root,
        db_path=db_path,
        dry_run=dry_run,
        only_game=None,
        json_out=json_out,
        tips_mode="default",
    )


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser("Unified Multi-Game Ingestion CLI (Phase 3)")
    parser.add_argument("charts_root", help="Root directory containing chart files")
    parser.add_argument("--db-path", default=None, help="Optional Songs DB workbook path")
    parser.add_argument("--json", dest="json_out", default=None, help="Optional JSON output path")
    parser.add_argument("--dry-run", action="store_true", help="Run without mutating persistent outputs")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    return int(
        run_ingestion(
            charts_root=args.charts_root,
            db_path=args.db_path,
            json_out=args.json_out,
            dry_run=bool(args.dry_run),
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())