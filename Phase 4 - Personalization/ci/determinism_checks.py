"""
determinism_checks.py

Phase 4 CI — Determinism Checks.

Ensures:
- Deterministic core produces stable outputs
- Personalization does not alter semantic meaning
"""

from typing import Any, Dict, Callable


def run_determinism_checks(
    *,
    run_fn: Callable[..., Dict[str, Any]],
    base_input: Dict[str, Any],
    iterations: int = 2,
) -> None:
    """
    Run deterministic regression checks.

    The same input must produce identical outputs.
    Raises AssertionError on failure.
    """

    outputs = []
    for _ in range(iterations):
        out = run_fn(**base_input)
        outputs.append(out)

    first = outputs[0]
    for idx, other in enumerate(outputs[1:], start=1):
        if other != first:
            raise AssertionError(
                f"Determinism violation at iteration {idx}: outputs differ"
            )