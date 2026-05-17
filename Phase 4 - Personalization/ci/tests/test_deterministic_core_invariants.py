import importlib

REQUIRED_RUNTIME_MODULES = [
    "runtime.runtime_wrapper",
    "runtime.personalization_core",
    "runtime.decision_router",
    "runtime.adjustment_router",
    "safe_adjustment.apply_adjustment",
    "safe_adjustment.adjustment_constraints",
    "narrative.narrative_v3_bridge",
]

def test_required_runtime_modules_importable():
    for mod_name in REQUIRED_RUNTIME_MODULES:
        try:
            importlib.import_module(mod_name)
        except Exception as e:
            raise AssertionError(f"Failed to import required module '{mod_name}': {e}")


def test_required_runtime_modules_importable():
    for mod_name in REQUIRED_RUNTIME_MODULES:
        try:
            importlib.import_module(mod_name)
        except Exception as e:
            raise AssertionError(
                f"Failed to import required module '{mod_name}': {e}"
            )