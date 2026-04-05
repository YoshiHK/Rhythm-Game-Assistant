"""Phase 4 CI: Safe Adjustment Bounds

Purpose
-------
Validates that Phase 4 includes a "safe adjustment" layer and that it exposes
some explicit bound/guardrail surface.

This is a structural check:
- safe_adjustment.py exists and imports
- module exposes at least one of common bound/guardrail identifiers

The goal is to prevent silent removal of guardrails.
"""

import importlib


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    raise SystemExit(1)


def main() -> int:
    try:
        mod = importlib.import_module('safe_adjustment')
    except Exception as e:
        fail(f"Failed to import safe_adjustment: {e}")

    # Look for any reasonable guardrail symbol without over-constraining implementation.
    candidates = [
        'MAX_DELTA',
        'DEFAULT_BOUNDS',
        'BOUNDS',
        'clamp',
        'clamp_value',
        'apply_safe_adjustment',
        'apply_safe_adjustments',
        'SafeAdjustment',
    ]

    if not any(hasattr(mod, name) for name in candidates):
        fail(
            'safe_adjustment module does not expose any expected guardrail symbol. '
            'Add a bound constant or a clamp/apply function to make guardrails explicit.'
        )

    print('CI PASS: Safe adjustment guardrail surface detected')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
