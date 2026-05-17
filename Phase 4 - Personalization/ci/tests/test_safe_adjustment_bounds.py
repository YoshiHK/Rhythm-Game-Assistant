"""
Phase 4 CI — Safe Adjustment Bounds (Design-Locked)

Purpose:
- Ensure Phase 4 includes an explicit safe-adjustment guardrail layer.
- Ensure canonical entrypoint and constraints surface exist.

This is STRUCTURAL ONLY (no runtime execution).
"""

import importlib


def test_safe_adjustment_modules_importable():
    importlib.import_module("safe_adjustment.apply_adjustment")
    importlib.import_module("safe_adjustment.adjustment_constraints")


def test_safe_adjustment_guardrails_present():
    mod = importlib.import_module("safe_adjustment.apply_adjustment")

    assert hasattr(mod, "apply_safe_adjustment"), "Missing guardrail symbol: apply_safe_adjustment"
    assert callable(getattr(mod, "apply_safe_adjustment")), "apply_safe_adjustment must be callable"

    # Backward-compat alias is nice-to-have; keep it optional:
    # assert hasattr(mod, "apply_safe_adjustments")

    cons = importlib.import_module("safe_adjustment.adjustment_constraints")
    assert hasattr(cons, "validate_directives"), "Missing constraints validator: validate_directives"
    assert callable(getattr(cons, "validate_directives")), "validate_directives must be callable"