# CI — Continuous Invariants

This folder enforces **system invariants**, not model correctness.

## What CI protects
- Phase boundaries (no upstream semantic access)
- Deterministic personalization and localization contracts
- API surface stability for Softr integration

## What CI does NOT do
- Run chart ingestion
- Execute Phase 1–3 pipelines
- Train models

CI exists to ensure **completed phases remain immutable**.
