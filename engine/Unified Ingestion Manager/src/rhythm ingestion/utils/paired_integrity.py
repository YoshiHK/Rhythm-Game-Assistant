from __future__ import annotations
"""Integrity helpers for paired run artefacts (tips_meta + file_scan_state).

This module is CONTROL-PLANE / OBSERVABILITY only.
It does not alter gameplay semantics, analysis logic, personalization, or localization.

## Integrity model
We define a *content hash* as SHA-256 over canonical JSON serialization of the payload
with the top-level key 'integrity' removed.

This avoids circular dependencies because the hash does not include itself.

Each report may include:
  integrity = {
    "hash_algo": "sha256",
    "schema_version": 1,
    "content_hash_sha256": <computed>,
    "prev_content_hash_sha256": <optional>,
    "pair_content_hash_sha256": <optional>
  }

- prev_content_hash_sha256: optional chaining within the same artefact stream
- pair_content_hash_sha256: optional reference to the paired artefact's content hash

Verification recomputes the content hash and compares it to integrity.content_hash_sha256.
"""

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Dict, Optional, Tuple


def canonical_dumps(obj: Any) -> str:
    """Deterministic JSON serialization."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def compute_content_hash_sha256(payload: Dict[str, Any]) -> str:
    """SHA-256 over canonical JSON with 'integrity' removed."""
    tmp = deepcopy(payload)
    tmp.pop("integrity", None)
    return hashlib.sha256(canonical_dumps(tmp).encode("utf-8")).hexdigest()


def stamp_integrity(
    payload: Dict[str, Any],
    *,
    prev_content_hash_sha256: Optional[str] = None,
    pair_content_hash_sha256: Optional[str] = None,
    schema_version: int = 1,
) -> Dict[str, Any]:
    """Attach/overwrite the integrity block and return the payload."""
    ch = compute_content_hash_sha256(payload)
    payload["integrity"] = {
        "hash_algo": "sha256",
        "schema_version": schema_version,
        "content_hash_sha256": ch,
        "prev_content_hash_sha256": prev_content_hash_sha256,
        "pair_content_hash_sha256": pair_content_hash_sha256,
    }
    return payload


def verify_integrity(payload: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
    """Verify content hash matches.

    Returns (ok, computed_hash, declared_hash).
    """
    computed = compute_content_hash_sha256(payload)
    declared = None
    if isinstance(payload.get("integrity"), dict):
        declared = payload["integrity"].get("content_hash_sha256")
    return (declared == computed), computed, declared


def verify_pairing(
    tips_meta: Dict[str, Any],
    scan_state: Dict[str, Any],
) -> Dict[str, Any]:
    """Verify cross-references between paired artefacts.

    Checks:
    - run_id matches (if both present)
    - each side's pair_content_hash_sha256 matches the other's computed content hash (if present)

    Returns a diagnostic dict.
    """
    diag: Dict[str, Any] = {"run_id_match": None, "tips_meta": {}, "scan_state": {}}

    run_a = tips_meta.get("run_id")
    run_b = scan_state.get("run_id")
    if run_a is not None and run_b is not None:
        diag["run_id_match"] = (run_a == run_b)

    ok_a, ch_a, dh_a = verify_integrity(tips_meta)
    ok_b, ch_b, dh_b = verify_integrity(scan_state)

    diag["tips_meta"]["integrity_ok"] = ok_a
    diag["tips_meta"]["computed_content_hash"] = ch_a
    diag["tips_meta"]["declared_content_hash"] = dh_a

    diag["scan_state"]["integrity_ok"] = ok_b
    diag["scan_state"]["computed_content_hash"] = ch_b
    diag["scan_state"]["declared_content_hash"] = dh_b

    pair_a = None
    pair_b = None
    if isinstance(tips_meta.get("integrity"), dict):
        pair_a = tips_meta["integrity"].get("pair_content_hash_sha256")
    if isinstance(scan_state.get("integrity"), dict):
        pair_b = scan_state["integrity"].get("pair_content_hash_sha256")

    diag["tips_meta"]["pair_hash_matches_scan_state"] = (pair_a == ch_b) if pair_a else None
    diag["scan_state"]["pair_hash_matches_tips_meta"] = (pair_b == ch_a) if pair_b else None

    return diag
