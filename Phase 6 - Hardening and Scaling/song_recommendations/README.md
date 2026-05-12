# Song Recommendation Layer (Phase 6)

## Scope

This layer is the **Phase 6 routing domain** for song recommendations.

It coordinates:
- Request normalization
- Game capability resolution
- Deterministic recommendation orchestration
- Persistence and rotation policy
- Response shaping

It does NOT perform gameplay analysis or personalization.

## Responsibilities

- Act as the single coordination surface for song recommendations
- Resolve game capability and difficulty ordering
- Maintain deterministic behavior across requests
- Enforce platform‑level safety and policy constraints

## Explicit Non‑Responsibilities

This layer MUST NOT:
- Analyze charts
- Interpret gameplay mechanics
- Model player skill
- Rank games or songs semantically
- Perform localization logic

All semantic computation is delegated to downstream phases.

## Architectural Notes

- Difficulty tiers and completion labels are opaque strings
- Ordering is derived solely from game capability fixtures
- Multi‑game support is achieved through configuration, not branching logic