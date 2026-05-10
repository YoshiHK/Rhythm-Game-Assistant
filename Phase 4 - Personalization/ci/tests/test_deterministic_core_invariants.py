"""
Phase 4 CI — Deterministic Core Invariants (Design-Locked)

Purpose:
- Ensure Phase 4 does not break or mutate the deterministic core (Phase 1–3)
- Validate existence and importability of Phase 4 runtime wiring

This test is STRUCTURAL ONLY.
It does not execute personalization logic.
"""

from pathlib import Path
import importlib
import sys


REQUIRED_RUNTIME_MODULES = [
    "phase4_personalization_runtime",
    "phase4_runtime_wrapper",
    "safe_adjustment",
    "narrative_module_v3",
]


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    sys.exit(1)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]

    # --- 1. Files must exist
    for name in REQUIRED_RUNTIME_MODULES:
        found = list(repo_root.rglob(f"{name}.py"))
        if not found:
            fail(f"Missing required Phase 4 runtime module: {name}.py")

    # --- 2. Modules must be importable
    for name in REQUIRED_RUNTIME_MODULES:
        try:
            importlib.import_module(name)
        except Exception as e:
            fail(f"Failed to import Phase 4 runtime module '{name}': {e}")

    print("CI PASS: Phase 4 deterministic core invariants preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())