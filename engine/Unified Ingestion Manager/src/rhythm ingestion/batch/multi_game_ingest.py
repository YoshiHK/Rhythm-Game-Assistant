#!/usr/bin/env python3
"""
Unified Multi‑Game Ingestion CLI (Phase 3)

Thin CLI wrapper around the UMI ingestion flow.
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
    Aggregate list[pattern_profile].
    """
    if not pattern_profiles_list:
        return {
            "dominant_categories": [],
            "category_counts": {},
            "category_shares": {},
        }

    # Stub aggregation (logic unchanged / not implemented here)
    return {
        "dominant_categories": [],
        "category_counts": {},
        "category_shares": {},
    }


def ingest_one_chart(path: Path):
    enabled_games = get_enabled_games()
    # Stub: real logic lives in orchestrator
    return None


def run_ingestion(
    charts_root: str,
    *,
    db_path: str | None = None,
    json_out: str | None = None,
    dry_run: bool = False,
):
    root = Path(charts_root)
    if not root.exists():
        log(f"Error: directory not found: {charts_root}")
        return 1

    # Stub: real orchestration handled elsewhere
    if not dry_run:
        pass

    return 0


if __name__ == "__main__":
    charts_root = None
    db_path = None
    json_path = None
    dry = False