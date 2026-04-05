"""Phase 4 CI: Deterministic Core Invariants

Purpose
-------
Phase 4 must not modify the deterministic core (Phases 1–3). This check is intentionally
non-semantic: it validates that the Phase 4 runtime can be imported and that deterministic
mode entrypoints exist.

How this test works
-------------------
- Verifies expected Phase 4 modules and key files are present.
- Attempts to import runtime modules.

NOTE
----
This is a contract-level CI check (structure + importability). It does not judge
personalization quality.
"""

import sys
from pathlib import Path


def fail(msg: str) -> None:
    print(f"CI FAIL: {msg}")
    raise SystemExit(1)


def main() -> int:
    # Expected Phase-4 runtime modules/files in repo root (contract surface)
    required_files = [
        'phase4_personalization_runtime.py',
        'phase4_runtime_wrapper.py',
        'safe_adjustment.py',
        'narrative_module_v3.py',
    ]

    for f in required_files:
        if not Path(f).exists():
            fail(f"Missing required Phase 4 file: {f}")

    # Importability checks (best-effort; avoid over-specifying symbols)
    try:
        import importlib
        importlib.import_module('phase4_personalization_runtime')
        importlib.import_module('safe_adjustment')
        importlib.import_module('narrative_module_v3')
    except Exception as e:
        fail(f"Failed to import Phase 4 module(s): {e}")

    print('CI PASS: Phase 4 deterministic-core contract files exist and are importable')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
