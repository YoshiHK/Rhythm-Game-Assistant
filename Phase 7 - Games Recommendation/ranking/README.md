# Phase 7 — Ranking Layer

This directory implements the **single authoritative ranking logic** for
Phase 7 – Games Recommendations.

## Design constraints (non-negotiable)
- Downstream-only: MUST NOT trigger analysis, ingestion, or training.
- Non-semantic: MUST NOT change tips meaning or upstream semantics.
- Deterministic: same inputs => same outputs.
- Explainable: emit structured, bounded reasons. No free-form generation required.
- No I/O: ranking performs no file/network/database access.

## Runtime rule
There is exactly **one authoritative ranking implementation** at runtime.
Evolution occurs through implementation updates, not runtime version selection.

## Outputs
The ranker returns contract-shaped recommendation items suitable for routing
and explanation layers.