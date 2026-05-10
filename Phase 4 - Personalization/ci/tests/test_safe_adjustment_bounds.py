"""
Phase 4 CI — Safe Adjustment Bounds (Design-Locked)

Purpose:
- Ensure Phase 4 includes an explicit safe-adjustment guardrail layer
- Prevent silent removal or hollowing-out of adjustment bounds

This is a STRUCTURAL test.
It does not execute safe-adjustment logic.
"""

import importlib
import sys
from typing import Iterable


# Symbols that indicate presence of a guardrail / bound surface
GUARDRAIL_SYMBOLS: Iterable[str] = (
    "apply_safe_adjustment",
    "ADJUSTMENT_BOUNDS",
    "MAX_DELTA",
    "BOUND_CONFIG",
)


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    raise SystemExit(1)


def main() -> int:
    try:
        mod = importlib.import_module("safe_adjustment")
    except Exception as e:
        fail(f"Failed to import safe_adjustment module: {e}")

    present = [name for name in GUARDRAIL_SYMBOLS if hasattr(mod, name)]

    if not present:
        fail(
            "safe_adjustment module exposes no recognizable guardrail symbols "
            f"(expected one of {list(GUARDRAIL_SYMBOLS)})"
        )

    print(
        "CI PASS: safe_adjustment guardrail surface present "
        f"(detected={present})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())