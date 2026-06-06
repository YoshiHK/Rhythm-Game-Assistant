"""
Phase 5 — Song Recommendation Learning
Deployment Gate Layer

This package enforces deployment eligibility for Phase 5 outputs.

Scope:
- Validate pipeline results
- Enforce regression guards
- Produce deployment decisions

Contract:
- Offline only
- Deterministic
- No runtime dependency
- No mutation of learning artifacts

Role:
evaluation → ✅ deployment_gate → deployment
"""

from .deployment_gate import (
    DeploymentGateConfig,
    DeploymentDecision,
    evaluate_deployment_eligibility,
)

__all__ = [
    "DeploymentGateConfig",
    "DeploymentDecision",
    "evaluate_deployment_eligibility",
]