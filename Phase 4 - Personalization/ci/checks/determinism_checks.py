"""
determinism_checks.py
Phase 4 CI — Determinism Checks (Design-Locked)

Purpose:
- Ensure Phase 4 personalization is deterministic
- Ensure identical inputs always produce identical outputs

This module enforces a hard determinism invariant.
Any violation here is an architectural error.
"""

from typing import Any, Dict, Callable, List
import json
import hashlib


def _stable_hash(payload: Dict[str, Any]) -> str:
    """
    Compute a stable hash for a JSON-serializable payload.

    - Keys are sorted
    - No reliance on object identity
    - Deterministic across runs
    """
    try:
        canonical = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
        )
    except Exception as e:
        raise AssertionError(
            f"Phase 4 determinism violation: output is not JSON-serializable ({e})"
        )

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def run_determinism_checks(
    *,
    run_fn: Callable[..., Dict[str, Any]],
    base_input: Dict[str, Any],
    iterations: int = 2,
) -> None:
    """
    Run deterministic regression checks for Phase 4.

    Enforced invariants:
    1. run_fn must return a JSON-serializable dict
    2. Identical inputs must yield identical outputs
    3. No hidden randomness is allowed

    Parameters:
    - run_fn: callable Phase 4 runtime entry (injected by CI runner)
    - base_input: canonical input dict
    - iterations: number of repeated executions (default=2)
    """

    if iterations < 2:
        raise ValueError("determinism_checks requires iterations >= 2")

    hashes: List[str] = []

    for i in range(iterations):
        try:
            output = run_fn(**base_input)
        except Exception as e:
            raise AssertionError(
                f"Phase 4 determinism violation: runtime error on iteration {i} ({e})"
            )

        if not isinstance(output, dict):
            raise AssertionError(
                "Phase 4 determinism violation: output must be a dict"
            )

        h = _stable_hash(output)
        hashes.append(h)

    first = hashes[0]
    for idx, h in enumerate(hashes[1:], start=1):
        if h != first:
            raise AssertionError(
                "Phase 4 determinism violation: outputs differ across identical runs "
                f"(iteration 0 hash={first}, iteration {idx} hash={h})"
            )
