from __future__ import annotations
from typing import Any, Dict, List
from datetime import datetime
from collections import Counter


def build_recommendation_meta(
    *,
    rows: List[Dict[str, Any]],
    run_id: str,
    report_date: str,
) -> Dict[str, Any]:

    total = len(rows)

    # -------------------------------
    # Basic game distribution
    # -------------------------------
    game_counter = Counter()
    difficulty_counter = Counter()

    for item in rows:
        game_id = item.get("game_id", "unknown")
        game_counter[game_id] += 1

        canonical = item.get("canonical_row", {})
        difficulty = canonical.get("difficulty_code") or canonical.get("difficulty_label") or "UNKNOWN"
        difficulty_counter[difficulty] += 1

    # -------------------------------
    # Simple recommendation logic (v1)
    # -------------------------------
    # NOTE: for pipeline test, keep deterministic
    top_games = sorted(game_counter.items(), key=lambda x: x[1], reverse=True)
    top_difficulties = sorted(difficulty_counter.items(), key=lambda x: x[1], reverse=True)

    # simulate recommendation
    recommended_games = [g for g, _ in top_games[:3]]
    recommended_difficulties = [d for d, _ in top_difficulties[:3]]

    # -------------------------------
    # Construct output
    # -------------------------------
    return {
        "report_type": "recommendation_meta",
        "run_id": run_id,
        "report_date": report_date,
        "generated_at": datetime.utcnow().isoformat(),

        "summary": {
            "total_rows": total,
            "unique_games": len(game_counter),
        },

        "recommendations": {
            "games": recommended_games,
            "difficulties": recommended_difficulties,
        },

        "signals": {
            "game_distribution": dict(game_counter),
            "difficulty_distribution": dict(difficulty_counter),
        },

        "integrity": {
            "schema_version": 1
        }
    }