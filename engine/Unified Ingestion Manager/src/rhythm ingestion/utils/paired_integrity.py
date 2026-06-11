"""
paired_integrity.py

Purpose:
- Content-level integrity helpers for file scan / metadata stamping
- Pipeline-level integrity checks for scan -> ingestion -> tips consistency

Notes:
- Keep legacy helpers that file_scan.py depends on
- Add run_integrity_check() for runtime pipeline validation
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


# ------------------------------------------------------------
# Legacy / content-level helpers
# ------------------------------------------------------------
def canonical_dumps(obj: Any) -> str:
    """
    Stable JSON serialization for hashing / comparison.
    """
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def compute_content_hash_sha256(obj: Any) -> str:
    """
    Compute a stable SHA256 hash for JSON-serializable content.
    """
    normalized = canonical_dumps(obj)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def stamp_integrity(
    payload: Dict[str, Any],
    *,
    schema_version: int = 1,
    prev_content_hash_sha256: Optional[str] = None,
    pair_content_hash_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Attach integrity metadata to a payload.
    """
    content_hash = compute_content_hash_sha256(payload)

    payload["integrity"] = {
        "hash_algo": "sha256",
        "schema_version": schema_version,
        "content_hash_sha256": content_hash,
        "prev_content_hash_sha256": prev_content_hash_sha256,
        "pair_content_hash_sha256": pair_content_hash_sha256,
    }
    return payload


def verify_integrity(payload: Dict[str, Any]) -> bool:
    """
    Verify whether the payload's stored integrity hash matches its current content.
    """
    if not isinstance(payload, dict):
        return False

    integrity = payload.get("integrity")
    if not isinstance(integrity, dict):
        return False

    expected_hash = integrity.get("content_hash_sha256")
    if not expected_hash:
        return False

    payload_copy = dict(payload)
    payload_copy.pop("integrity", None)

    actual_hash = compute_content_hash_sha256(payload_copy)
    return actual_hash == expected_hash


def verify_pairing(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """
    Verify whether two payloads are a paired version of each other by comparing
    normalized content hashes (excluding integrity blocks).
    """
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False

    a_copy = dict(a)
    b_copy = dict(b)

    a_copy.pop("integrity", None)
    b_copy.pop("integrity", None)

    return compute_content_hash_sha256(a_copy) == compute_content_hash_sha256(b_copy)


# ------------------------------------------------------------
# Scan artifact loader
# ------------------------------------------------------------
def _load_json_from_scan_result(scan_result: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Resolve the file_scan_state JSON from runtime result['scan'].
    Expected runtime shape:
      {"status": "...", "output": "path/to/file_scan_state.json"}
    """
    if not isinstance(scan_result, dict):
        return None

    scan_path = scan_result.get("output")
    if not scan_path:
        return None

    try:
        return json.loads(Path(scan_path).read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_json_from_tips_result(tips_result: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Resolve the tips_meta JSON from runtime result['tips'].
    Expected runtime shape:
      {"status": "...", "output": "path/to/tips_meta.json"}
    """
    if not isinstance(tips_result, dict):
        return None

    tips_path = tips_result.get("output")
    if not tips_path:
        return None

    try:
        return json.loads(Path(tips_path).read_text(encoding="utf-8"))
    except Exception:
        return None


# ------------------------------------------------------------
# 1) Layer checks
# ------------------------------------------------------------
def _check_scan(scan_result: Optional[Dict[str, Any]]) -> List[str]:
    issues: List[str] = []

    if scan_result is None:
        issues.append("scan_result is None")
        return issues

    if scan_result.get("status") != "completed":
        issues.append("scan not completed")
        return issues

    scan_data = _load_json_from_scan_result(scan_result)
    if scan_data is None:
        issues.append("scan artifact could not be read")
        return issues

    summary = scan_data.get("summary")
    if not isinstance(summary, dict):
        issues.append("scan summary missing or invalid")
        return issues

    if summary.get("total_files") is None:
        issues.append("scan.summary.total_files missing")

    return issues


def _check_ingestion(rows_count: int) -> List[str]:
    issues: List[str] = []

    if rows_count == 0:
        issues.append("no ingestion rows")

    return issues


def _check_tips(tips_result: Optional[Dict[str, Any]]) -> List[str]:
    issues: List[str] = []

    if tips_result is None:
        issues.append("tips_result is None")
        return issues

    if tips_result.get("status") != "completed":
        issues.append("tips not completed")
        return issues

    tips_data = _load_json_from_tips_result(tips_result)
    if tips_data is None:
        issues.append("tips artifact could not be read")
        return issues

    if tips_data.get("report_type") != "tips_meta":
        issues.append("tips artifact report_type invalid")

    return issues


# ------------------------------------------------------------
# 2) Cross-layer checks (UPDATED)
# ------------------------------------------------------------

def _compute_drop_rate(scan_total: int, ingestion_rows: int) -> float:
    if not scan_total or scan_total <= 0:
        return 0.0
    return max(0.0, (scan_total - ingestion_rows) / scan_total)


def _check_scan_vs_ingestion(
    scan_result: Optional[Dict[str, Any]],
    ingestion_rows: int,
    *,
    allowed_drop_ratio: float = 0.02,  # ✅ 2% tolerance
) -> List[str]:

    issues: List[str] = []

    scan_data = _load_json_from_scan_result(scan_result)
    if scan_data is None:
        issues.append("cannot verify scan vs ingestion (scan artifact unreadable)")
        return issues

    try:
        scan_total = scan_data.get("summary", {}).get("total_files")

        if scan_total is None:
            issues.append("scan.summary.total_files missing")
            return issues

        if ingestion_rows == 0:
            issues.append("ingestion produced zero rows")
            return issues

        drop_rate = _compute_drop_rate(scan_total, ingestion_rows)

        if drop_rate > allowed_drop_ratio:
            issues.append(
                f"scan ({scan_total}) vs ingestion ({ingestion_rows}) drop_rate={drop_rate:.4f} exceeds threshold"
            )

    except Exception:
        issues.append("scan structure invalid")

    return issues


def _check_ingestion_vs_tips(
    ingestion_rows: int,
    tips_result: Optional[Dict[str, Any]],
    *,
    allowed_mismatch: int = 10,
) -> List[str]:

    issues: List[str] = []

    tips_data = _load_json_from_tips_result(tips_result)
    if tips_data is None:
        issues.append("cannot verify ingestion vs tips (tips artifact unreadable)")
        return issues

    try:
        tips_total = tips_data.get("summary", {}).get("total_charts")

        if tips_total is None:
            issues.append("tips.summary.total_charts missing")
            return issues

        if abs(tips_total - ingestion_rows) > allowed_mismatch:
            issues.append(
                f"ingestion ({ingestion_rows}) != tips ({tips_total}) beyond tolerance"
            )

    except Exception:
        issues.append("tips structure invalid")

    return issues


def _check_scan_vs_tips(
    scan_result: Optional[Dict[str, Any]],
    tips_result: Optional[Dict[str, Any]],
    *,
    allowed_drop_ratio: float = 0.02,
) -> List[str]:

    issues: List[str] = []

    scan_data = _load_json_from_scan_result(scan_result)
    tips_data = _load_json_from_tips_result(tips_result)

    if scan_data is None or tips_data is None:
        issues.append("cannot verify scan vs tips (artifact unreadable)")
        return issues

    try:
        scan_total = scan_data.get("summary", {}).get("total_files")
        tips_total = tips_data.get("summary", {}).get("total_charts")

        if scan_total is None or tips_total is None:
            issues.append("scan/tips summary missing")
            return issues

        drop_rate = _compute_drop_rate(scan_total, tips_total)

        if drop_rate > allowed_drop_ratio:
            issues.append(
                f"scan ({scan_total}) vs tips ({tips_total}) drop_rate={drop_rate:.4f} exceeds threshold"
            )

    except Exception:
        issues.append("scan/tips structure invalid")

    return issues


# ------------------------------------------------------------
# 2.5) Phase 5 / 7 checks (UPDATED)
# ------------------------------------------------------------

def _check_ingestion_vs_song_recommendation(
    ingestion_rows,
    song_rec_result,
    *,
    allowed_mismatch: int = 0,
):

    issues = []

    if not song_rec_result:
        return issues

    try:
        rec_data = json.loads(
            Path(song_rec_result.get("output")).read_text(encoding="utf-8")
        )

        rec_total = rec_data.get("summary", {}).get("total_rows")

        if rec_total is None:
            return issues

        if abs(rec_total - ingestion_rows) > allowed_mismatch:
            issues.append(
                f"ingestion ({ingestion_rows}) != song_recommendation ({rec_total})"
            )

    except Exception:
        issues.append("song_recommendation structure invalid")

    return issues


def _check_ingestion_vs_recommendation(
    ingestion_rows,
    recommendation_result,
    *,
    allowed_mismatch: int = 0,
):

    issues = []

    if not recommendation_result:
        return issues

    try:
        rec_data = json.loads(
            Path(recommendation_result.get("output")).read_text(encoding="utf-8")
        )

        rec_total = rec_data.get("summary", {}).get("total_rows")

        if rec_total is None:
            return issues

        if abs(rec_total - ingestion_rows) > allowed_mismatch:
            issues.append(
                f"ingestion ({ingestion_rows}) != recommendation ({rec_total})"
            )

    except Exception:
        issues.append("recommendation structure invalid")

    return issues


# ------------------------------------------------------------
# 3) Main entry (UPDATED)
# ------------------------------------------------------------

def run_integrity_check(
    *,
    scan_result: Optional[Dict[str, Any]],
    ingestion_rows: int,
    tips_result: Optional[Dict[str, Any]],
    song_recommendation_result=None,
    recommendation_result=None,
) -> Dict[str, Any]:

    issues: List[str] = []

    issues += _check_scan_vs_ingestion(scan_result, ingestion_rows)
    issues += _check_ingestion_vs_tips(ingestion_rows, tips_result)
    issues += _check_scan_vs_tips(scan_result, tips_result)

    if song_recommendation_result:
        issues += _check_ingestion_vs_song_recommendation(
            ingestion_rows, song_recommendation_result
        )

    if recommendation_result:
        issues += _check_ingestion_vs_recommendation(
            ingestion_rows, recommendation_result
        )

    scan_data = _load_json_from_scan_result(scan_result)
    scan_total = None
    if scan_data:
        scan_total = scan_data.get("summary", {}).get("total_files")

    metrics = {
        "ingestion_rows": ingestion_rows,
        "scan_total": scan_total,
    }

    if scan_total:
        metrics["drop_rate"] = _compute_drop_rate(scan_total, ingestion_rows)

    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "metrics": metrics,
    }