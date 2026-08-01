from __future__ import annotations

"""
verify_identity_consistency.py

Cross-check identity signals inside chart_assets.db.

Purpose
-------
Verify consistency between:
- inferred_game_id (path-based hint)
- normalized_game (folder-based normalization)

Scope
-----
- read-only
- no DB mutation
- no authoritative decisions

This is a SOFT verifier:
- mostly warnings
- does not block pipeline by default
"""

import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_CHART_ASSET_DB = Path("chart_assets.db")


# --------------------------------------------------
# Models
# --------------------------------------------------

@dataclass
class IdentityIssue:
    severity: str  # warning / info
    code: str
    asset_id: Optional[str] = None
    candidate_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IdentitySummary:
    total_assets: int = 0

    both_present: int = 0
    consistent: int = 0
    conflicts: int = 0

    missing_inferred: int = 0
    missing_normalized: int = 0

    fully_missing: int = 0

    consistent_identity: bool = False


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def _get_rows(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    return [dict(r) for r in conn.execute("SELECT * FROM chart_assets")]


# --------------------------------------------------
# Core
# --------------------------------------------------

def verify_identity_consistency(
    *,
    chart_asset_db: Path,
) -> Dict[str, Any]:

    if not chart_asset_db.exists():
        raise FileNotFoundError(chart_asset_db)

    issues: List[IdentityIssue] = []
    summary = IdentitySummary()

    with sqlite3.connect(str(chart_asset_db)) as conn:
        rows = _get_rows(conn)

    summary.total_assets = len(rows)

    for row in rows:
        asset_id = row.get("asset_id")
        candidate_id = row.get("candidate_id")

        inferred = None
        normalized = row.get("game_normalized")

        # try reading inferred from JSON
        try:
            extra = row.get("extra_metadata_json")
            if extra:
                import json
                meta = json.loads(extra)
                inferred = meta.get("inferred_game_id")
        except Exception:
            inferred = None

        # -----------------------------------------
        # cases
        # -----------------------------------------

        if inferred and normalized:
            summary.both_present += 1

            if inferred == normalized:
                summary.consistent += 1
            else:
                summary.conflicts += 1
                issues.append(
                    IdentityIssue(
                        severity="warning",
                        code="identity_conflict",
                        asset_id=asset_id,
                        candidate_id=candidate_id,
                        details={
                            "inferred": inferred,
                            "normalized": normalized,
                        },
                    )
                )

        elif inferred and not normalized:
            summary.missing_normalized += 1
            issues.append(
                IdentityIssue(
                    severity="info",
                    code="missing_normalized_identity",
                    asset_id=asset_id,
                    candidate_id=candidate_id,
                    details={"inferred": inferred},
                )
            )

        elif normalized and not inferred:
            summary.missing_inferred += 1
            issues.append(
                IdentityIssue(
                    severity="info",
                    code="missing_inferred_identity",
                    asset_id=asset_id,
                    candidate_id=candidate_id,
                    details={"normalized": normalized},
                )
            )

        else:
            summary.fully_missing += 1
            issues.append(
                IdentityIssue(
                    severity="warning",
                    code="no_identity_detected",
                    asset_id=asset_id,
                    candidate_id=candidate_id,
                )
            )

    summary.consistent_identity = summary.conflicts == 0

    return {
        "summary": asdict(summary),
        "issues": [asdict(i) for i in issues],
    }


__all__ = [
    "verify_identity_consistency",
]