import importlib

REQUIRED_RUNTIME_MODULES = [
    "phase4_personalization_runtime",
    "phase4_runtime_wrapper",
    "safe_adjustment",
    "narrative_module_v3",
]


def test_required_runtime_modules_importable():
    for mod_name in REQUIRED_RUNTIME_MODULES:
        try:
            importlib.import_module(mod_name)
        except Exception as e:
            raise AssertionError(
                f"Failed to import required module '{mod_name}': {e}"
            )