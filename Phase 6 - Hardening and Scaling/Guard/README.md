# Phase 6 – Guards Package

This package defines the **Guards layer** for Phase 6 (Platform Hardening and Scale).

Purpose:
- Enforce non-semantic safety, reliability, and integrity constraints
- Protect Phase 5 artifacts and orchestrator execution
- Prevent abuse, leakage, and operational failure

Non-negotiable rules:
- Downstream-only (must not affect Phase 1–5 behavior)
- No gameplay, personalization, or recommendation semantics
- Guards may block, delay, or route — but never reinterpret
