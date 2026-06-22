"""
writers.verification

System-level verification layer.

### Responsibilities
- global system integrity checks
- DB completeness validation
- cross-layer consistency verification
- gating for destructive operations (e.g. safe_delete)

### Design rules
- verification is read-only (no mutation)
- operates on persisted system state (DBs)
- must be deterministic
- must not depend on transient artifacts
"""

from __future__ import annotations

from typing import Any


# --------------------------------------------------
# Core verification entrypoint (lazy loader)
# --------------------------------------------------

def __getattr__(name: str) -> Any:
    """
    Lazy export to avoid eager imports of heavy verification modules.

    This preserves:
    - fast module import
    - isolation between verification tools
    - no unnecessary DB connections
    """

    # --------------------------------------------------
    # Existing (Path B / legacy verification)
    # --------------------------------------------------
    if name == "verify_full_bundle":
        from .verify_full_bundle import verify_full_bundle
        return verify_full_bundle

    if name == "verify_full_bundle_cli":
        from .verify_full_bundle import cli_main
        return cli_main

    # --------------------------------------------------
    # NEW (Path A strict DB verification)
    # --------------------------------------------------
    if name == "verify_runtime_bundle_strict":
        from .verify_runtime_bundle_strict import verify_runtime_bundle_strict
        return verify_runtime_bundle_strict

    if name == "verify_runtime_bundle_strict_cli":
        from .verify_runtime_bundle_strict import cli_main
        return cli_main

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# --------------------------------------------------
# Public API
# --------------------------------------------------

__all__ = [
    # Path B (existing)
    "verify_full_bundle",
    "verify_full_bundle_cli",

    # Path A (new strict verification)
    "verify_runtime_bundle_strict",
    "verify_runtime_bundle_strict_cli",
]