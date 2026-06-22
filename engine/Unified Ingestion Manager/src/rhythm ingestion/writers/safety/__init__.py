"""
writers.safety

Safety layer for destructive or high-risk operations.

### Responsibilities
- gated file deletion (post-verification)
- pruning policies and safeguards
- reversible operations (quarantine instead of delete)

### Design rules
- must be verification-gated
- must support dry-run
- must never perform implicit destructive actions
- policy-driven behavior only (no hidden heuristics)
"""

# --------------------------------------------------
# Safe deletion / pruning
# --------------------------------------------------

from .safe_delete_candidates import (
    safe_delete_candidates,
    prune_verified_chart_files,
    cli_main as safe_delete_candidates_cli,
)

# --------------------------------------------------
# Public API
# --------------------------------------------------

__all__ = [
    "safe_delete_candidates",
    "prune_verified_chart_files",
    "safe_delete_candidates_cli",
]