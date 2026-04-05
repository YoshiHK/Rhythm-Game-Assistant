# Phase 5 – Recommendation Layer (Song-Level)

This package defines the **Recommendation Layer** for Phase 5.

Scope:
- Defines the *API contract* consumed by Softr
- Provides explainable, provenance-linked recommendation artifacts
- Does NOT implement UI logic or ranking logic

Non-negotiable rules:
- Read-only API surface
- Downstream-only (must not affect Phase 1–4.5 behavior)
- Recommendation logic remains in Softr
- Phase 5 provides data, not decisions
