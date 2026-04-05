#!/usr/bin/env python3
"""
PHASE 3 CONTRACT — Unified Ingestion Orchestrator (UMI)

This file is the authoritative coordination layer for Phase 3 of the
Rhythm Game Assistant pipeline.

Phase 3 Responsibilities (What this file DOES):
- Route input files to the correct game adapter
- Produce canonical rows and canonical payloads
- Validate canonical data using game-specific validators
- Invoke downstream semantic pipelines (Phase 1–2) via stable entrypoints
- Coordinate optional tips generation based on capability gating
- Perform governance and observability (e.g. taxonomy auditing, diagnostics)
- Persist results via writers and emit batch / run-level reports

Phase 3 Non-Responsibilities (What this file MUST NOT do):
- MUST NOT contain gameplay analysis logic
- MUST NOT re-implement or alter Phase 1–2 algorithms
- MUST NOT infer severity, select elements, or generate narratives directly
- MUST NOT embed game-specific semantics or heuristics
- MUST NOT depend on exploratory or experimental logic

Stability & Governance Guarantees:
- Phase 1–2 behavior must remain deterministic and unchanged
- All additions must be additive, observable, and non-semantic
- Governance features (e.g. taxonomy checks) may record, not decide
- This file is safe to use as a long-term reference and audit anchor

Forward Compatibility:
- Future phases may extend orchestration, reporting, or lifecycle control
- New phases MUST NOT back-propagate logic into completed phases
- This file defines the execution boundary between ingestion and analysis

Copilot / Knowledge Hub Note:
- This file is intended to serve as the Phase 3 “spine” document
- It may be referenced by M365 Copilot Notebook to resume system context
- It represents the authoritative end-state of Phase 3 execution flow
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
from rhythm_ingestion.pipeline.pattern_tags.pattern_tags_taxonomy import PatternTagsTaxonomy


# ----------------------------
# Helpers
# ----------------------------

def _json_dump(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def _detect_game_for_file(
    file_path: Path,
    enabled_game_ids: List[str],
) -> Tuple[Optional[str], List[str]]:
    """
    Detect which enabled game adapter accepts this file.
    Returns (chosen_game_id or None, matching_game_ids).
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
    if len(matches) == 1:
        return matches[0], matches
    return None, matches


def _try_build_payload(adapter: Any, path: Path) -> Dict[str, Any]:
    """
    Build canonical payload if the adapter provides it; else return a minimal payload.
    """
    if hasattr(adapter, "to_canonical_payload"):
        try:
            return adapter.to_canonical_payload(str(path))
        except Exception:
            return {"diagnostics": {}}
    return {"diagnostics": {}}


def _run_tips_if_supported(
    game_id: str,
    canonical_payload: Dict[str, Any],
    canonical_row: Dict[str, Any],
    *,
    tips_enabled_games: set,
    mode: str,
) -> Optional[Dict[str, Any]]:
    """
    Run tips generation only if the game is tips-enabled in games.json.
    Returns tips_result dict or None.
    """
    if game_id not in tips_enabled_games:
        return None

    try:
        from rhythm_ingestion.pipeline.tips import run_for_chart  # type: ignore
    except Exception:
        return None

    try:
        return run_for_chart(
            game_id=game_id,
            canonical_payload=canonical_payload,
            canonical_row=canonical_row,
            mode=mode,
            attach_to_payload=True,
        )
    except Exception as exc:
        diag = canonical_payload.setdefault("diagnostics", {})
        diag["tips_error"] = str(exc)
        return None


def _mean(nums: List[float]) -> float:
    return (sum(nums) / len(nums)) if nums else 0.0


def _aggregate_section_features(section_features_list: List[Dict[str, Any]]) -> Dict[str, float]:
    if not section_features_list:
        return {}
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
        if vals:
            out[k] = _mean(vals)
    return out


def _aggregate_pattern_profiles(pattern_profiles_list: List[Dict[str, Any]], *, top_k: int = 3) -> Dict[str, Any]:
    if not pattern_profiles_list:
        return {"dominant_categories": [], "category_counts": {}, "category_shares": {}}

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


def _init_taxonomy_policy_counters() -> Dict[str, int]:
    """Run-level counters for taxonomy governance (observability)."""
    return {
        "charts_seen": 0,
        "charts_with_tags": 0,
        "charts_with_unknown_tags": 0,
        "total_tags": 0,
        "total_unknown_tags": 0,
    }


def _update_taxonomy_policy_counters(
    counters: Dict[str, int],
    canonical_payload: Dict[str, Any],
) -> None:
    """Update run-level taxonomy counters from payload diagnostics."""
    counters["charts_seen"] += 1
    diag = canonical_payload.get("diagnostics") or {}
    tp = (diag.get("taxonomy_policy") or {}) if isinstance(diag, dict) else {}
    if not isinstance(tp, dict):
        return
    tag_count = tp.get("tag_count")
    unk_count = tp.get("unknown_tag_count")

    if isinstance(tag_count, int) and tag_count > 0:
        counters["charts_with_tags"] += 1
        counters["total_tags"] += tag_count

    if isinstance(unk_count, int) and unk_count > 0:
        counters["charts_with_unknown_tags"] += 1
        counters["total_unknown_tags"] += unk_count


# ----------------------------
# Core ingest loop
# ----------------------------

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

    from rhythm_ingestion.config.games_loader import build_game_registry

    registry = build_game_registry()

    enabled_game_ids = [
        gid for gid, entry in registry.items()
        if entry["status"] in ("enabled", "ingestion_only")
    ]

    if only_game:
        if only_game not in enabled_games:
            log(f"Error: --game={only_game!r} is not enabled in games.json")
            return 1
        enabled_game_ids = [only_game]

    tips_enabled_games = {
        gid for gid, entry in registry.items()
        if entry["status"] == "enabled"
    }


    if dry_run:
        writer = get_writer(kind="noop", capture_rows=True)
    else:
        if not db_path:
            log("Error: --db is required unless --dry-run is used.")
            return 1
        writer = get_writer(kind="excel", db_path=db_path)

    files = scan_directory(src)
    if not files:
        log("No candidate files found.")
        return 0

    log(f"Scanning {len(files)} candidate files under: {src}")

    results: List[Dict[str, Any]] = []
    per_game_counts: Dict[str, Dict[str, int]] = {}
    failure_types: Dict[str, int] = {}

    # Accumulator for batch summaries and semantic enrichment
    # batch_accumulator[game_id][difficulty] holds:
    # chart_summaries, tips_texts, section_features, pattern_profiles
    batch_accumulator: Dict[str, Dict[str, Dict[str, list]]] = {}

    # ----------------------------
    # Taxonomy governance policy (Phase 3, governance + observability only)
    # ----------------------------
    taxonomy_policy_mode = "observe"   # or "strict" if you want hard fail
    taxonomy_counters = _init_taxonomy_policy_counters()
    
    for f in files:
        game_id, matches = _detect_game_for_file(f, enabled_game_ids)

        if game_id is None:
            if not matches:
                res = {
                    "file": str(f),
                    "game_id": None,
                    "passed": False,
                    "error": "No enabled adapters accept this file.",
                    "ambiguous": False,
                }
            else:
                res = {
                    "file": str(f),
                    "game_id": matches,
                    "passed": False,
                    "error": f"Ambiguous adapters: {matches}",
                    "ambiguous": True,
                }
            results.append(res)
            per_game_counts.setdefault("None", {"passed": 0, "failed": 0})
            per_game_counts["None"]["failed"] += 1
            continue

        entry = registry[game_id]

        if entry["adapter"] is None:
            raise RuntimeError(f"No adapter wired for game_id={game_id}")

        adapter = get_adapter(game_id)

        validator = None
        if entry["validator"] is not None:
            validator = get_validator(game_id)

            
        if validator is not None:
            validator.validate(...)


        log(f"[{game_id}] Processing: {f}")

        passed = False
        error_msg: Optional[str] = None
        canonical_row: Dict[str, Any] = {}
        canonical_payload: Dict[str, Any] = {}

        try:
            raw = adapter.load(f)
            canonical_row = adapter.to_canonical_row(raw)
            canonical_payload = _try_build_payload(adapter, f)

            validator.validate(
                raw_chart=raw,
                canonical_payload=canonical_payload,
                canonical_row=canonical_row,
            )

            _apply_taxonomy_governance(
                canonical_payload,
                policy_mode=taxonomy_policy_mode,
                payload_key="detected_tags",
            )
            _update_taxonomy_policy_counters(taxonomy_counters, canonical_payload)

            _run_tips_if_supported(
                game_id,
                canonical_payload,
                canonical_row,
                tips_enabled_games=tips_enabled_games,
                mode=tips_mode,
            )

            if not dry_run:
                writer.insert_row(game_id, canonical_row)

            passed = True

            # ---- Accumulate enrichment for batch profile (only if chart_summary exists) ----
            difficulty = canonical_row.get("difficulty_label")
            chart_summary = canonical_payload.get("chart_summary") if isinstance(canonical_payload, dict) else None
            tips_text = canonical_payload.get("tips_text") if isinstance(canonical_payload, dict) else None

            if chart_summary and difficulty:
                # semantic enrichment from sections + tags
                sections = canonical_payload.get("sections", []) if isinstance(canonical_payload, dict) else []
                tags = canonical_payload.get("detected_tags", []) if isinstance(canonical_payload, dict) else []

                section_features = build_section_feature_vector(sections or [])
                pattern_profile = {
                    "dominant_categories": dominant_tag_categories(tags or []),
                    "category_counts": count_tags_by_category(tags or []),
                }

                bucket = batch_accumulator.setdefault(game_id, {}).setdefault(
                    difficulty,
                    {"chart_summaries": [], "tips_texts": [], "section_features": [], "pattern_profiles": []},
                )
                bucket["chart_summaries"].append(chart_summary)
                bucket["section_features"].append(section_features)
                bucket["pattern_profiles"].append(pattern_profile)
                if isinstance(tips_text, str):
                    bucket["tips_texts"].append(tips_text)

        except Exception as exc:
            passed = False
            error_msg = str(exc)

        per_game_counts.setdefault(game_id, {"passed": 0, "failed": 0})
        if passed:
            per_game_counts[game_id]["passed"] += 1
        else:
            per_game_counts[game_id]["failed"] += 1
            if error_msg:
                key = error_msg.split("\n")[0].strip()
                failure_types[key] = failure_types.get(key, 0) + 1

        diag = canonical_payload.get("diagnostics", {}) if isinstance(canonical_payload, dict) else {}
        adapter_meta = canonical_payload.get("adapter_metadata", {}) if isinstance(canonical_payload, dict) else {}
        internal_meta = canonical_payload.get("internal_metadata", {}) if isinstance(canonical_payload, dict) else {}

        results.append(
            {
                "file": str(f),
                "game_id": game_id,
                "passed": passed,
                "error": error_msg,
                "song_id": canonical_row.get("song_id"),
                "difficulty_label": canonical_row.get("difficulty_label"),
                "adapter_version": adapter_meta.get("adapter_version"),
                "canonical_sections_version": canonical_payload.get("canonical_sections_version") if isinstance(canonical_payload, dict) else None,
                "sections_source": internal_meta.get("sections_source"),
                "avg_nps": diag.get("avg_nps"),
                "avg_npb": diag.get("avg_npb"),
                "total_hold_coverage": diag.get("total_hold_coverage"),
                "tips_generated": bool(canonical_payload.get("tips_text")) if isinstance(canonical_payload, dict) else False,
                "tips_error": (diag.get("tips_error") if isinstance(diag, dict) else None),
            }
        )

    if not dry_run:
        writer.save()

    # ----------------------------
    # Batch summaries + compact difficulty profiles
    # ----------------------------
    batch_tips_summaries: Dict[str, Dict[str, Any]] = {}
    for gid, by_diff in batch_accumulator.items():
        for diff, data in by_diff.items():
            try:
                base = build_batch_summary(
                    difficulty=diff,
                    per_chart_summaries=data.get("chart_summaries", []),
                    tips_texts=data.get("tips_texts", []),
                )

                # Compact batch difficulty profile (additive)
                base["difficulty_profile_version"] = "v1"
                base["difficulty_profile"] = {
                    "section_features_mean": _aggregate_section_features(data.get("section_features", [])),
                    "pattern_profile": _aggregate_pattern_profiles(data.get("pattern_profiles", []), top_k=3),
                    "chart_count": base.get("chart_count", len(data.get("chart_summaries", []))),
                }

                batch_tips_summaries.setdefault(gid, {})[diff] = base
            except Exception as exc:
                log(f"[{gid}][{diff}] Batch summary failed: {exc}")

    # Print summary
    log("\n========================================")
    log(" UNIFIED INGESTION SUMMARY (UMI)")
    log("========================================")
    log(f"Total candidate files: {len(files)}")
    for gid, stats in per_game_counts.items():
        log(f"{gid}: {stats['passed']} PASSED, {stats['failed']} FAILED")

    if failure_types:
        log("\nFailure Types:")
        for err, n in sorted(failure_types.items(), key=lambda kv: (-kv[1], kv[0])):
            log(f"{n} × {err}")

    if json_out:
        _json_dump(
            json_out,
            {
                "source": str(src),
                "dry_run": dry_run,
                "games": enabled_game_ids,
                "total_files": len(files),
                "per_game": per_game_counts,
                "failure_types": failure_types,
                "results": results,
                "batch_tips_summaries": batch_tips_summaries,
                "taxonomy_policy": {
                "taxonomy_id": PatternTagsTaxonomy.TAXONOMY_ID,
                "taxonomy_version": PatternTagsTaxonomy.TAXONOMY_VERSION,
                "mode": taxonomy_policy_mode,
                "counters": taxonomy_counters,
            },
            },
        )
        log(f"\nJSON report written to: {json_out}")

    log("\nDone.\n")
    return 0


# ----------------------------
# CLI entry point
# ----------------------------

def main() -> None:
    parser = argparse.ArgumentParser("Unified Ingestion Orchestrator (UMI)")
    parser.add_argument("--source", required=True, help="Directory containing raw chart files")
    parser.add_argument("--db", required=False, help="Path to Song Database (full).xlsx (required unless --dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="Run without writing to Excel DB")
    parser.add_argument("--game", required=False, help="Restrict run to a single enabled game_id from games.json")
    parser.add_argument("--json", required=False, help="Write run report to JSON path")
    parser.add_argument(
        "--tips-mode",
        default="production",
        choices=["production", "debug"],
        help="Tips generation mode (only for games that support tips in games.json)",
    )

    args = parser.parse_args()
    raise SystemExit(
        ingest(
            source_dir=args.source,
            db_path=args.db,
            dry_run=args.dry_run,
            only_game=args.game,
            json_out=args.json,
            tips_mode=args.tips_mode,
        )
    )


if __name__ == "__main__":
    main()
