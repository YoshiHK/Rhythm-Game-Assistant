import importlib

GUARDRAIL_SYMBOLS = (
    "apply_safe_adjustment",
    "ADJUSTMENT_BOUNDS",
    "MAX_DELTA",
    "BOUND_CONFIG",
)


def test_safe_adjustment_module_importable():
    try:
        mod = importlib.import_module("safe_adjustment")
    except Exception as e:
        raise AssertionError(f"Failed to import safe_adjustment: {e}")


def test_safe_adjustment_guardrails_present():
    mod = importlib.import_module("safe_adjustment")

    available = dir(mod)

    for sym in GUARDRAIL_SYMBOLS:
        assert sym in available, f"Missing guardrail symbol: {sym}"