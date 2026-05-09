"""
Phase 2 Severity Layer (Stage 5.1 / Track A)

This package implements the Phase 2 enhancement layer for
severity, score, and section coverage inference.

Responsibilities:
- Build on top of Phase 1 baseline severity inference
- Apply midpoint overrides and feature-based blending
- Preserve canonical severity labels by default

Hard rules:
- No modification of Phase 1 semantics
- Deterministic execution only
- No personalization or player context
"""

__all__ = [
    "severity_engine",
    "coverage_calculator",
    "calibration_bridge",
    "feature_blender",
]