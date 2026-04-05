# Phase 5 – Offline Retraining & Model Ops

This folder defines the **Offline Retraining & Model Operations** subsystem for Phase 5 (Productionization).

Purpose:
- Transform curator gold labels and feedback datasets into improved models
- Enforce validation, promotion, and rollback safety
- Preserve Phase 4 explainability and non-semantic guarantees

Non-negotiable rules:
- Offline learning only (no live updates)
- Downstream-only (must not affect Phase 1–4.5 behavior)
- Promotion requires validation and rollback plan
- Models are presentation-only
