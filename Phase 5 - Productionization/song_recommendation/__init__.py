"""
Phase 5 — Song Recommendation Learning (Offline Only)

This package implements the **offline learning pipeline**
for Song Recommendations.

Pipeline:
    feedback → aggregation → features → training → evaluation → artifacts → deployment_gate

Contract (Non-Negotiable):

- Offline ONLY (Phase 5)
- Deterministic execution (same input => same output)
- No dependency on Phase 6 runtime
- No gameplay semantics (tips, taxonomy, severity, narrative)
- No runtime learning or adaptation
- Outputs are introduced via deployment only

Updated Guarantees:

- Full pipeline traceability:
  feature_schema_version → training_schema_version → artifacts
- Evaluation MUST precede deployment eligibility
- Deployment MUST pass deployment_gate

Responsibilities:

- Aggregate feedback signals
- Construct selection-level features
- Calibrate selector heuristics (no models)
- Evaluate quality and guard regressions
- Produce deployment-safe artifacts

Non-Responsibilities:

- Runtime recommendation
- Feedback emission
- Request routing
- UI / presentation
- Online personalization

Phase Boundary:

- Consumes: Phase 6 feedback (forward-only)
- Produces: static artifacts for deployment
- Enforced by deployment_gate

This package defines a **closed, deterministic learning system**.
"""

__all__ = [
    # Intentionally minimal
    # Submodules expose aggregation, features, training, evaluation, artifacts, deployment
]