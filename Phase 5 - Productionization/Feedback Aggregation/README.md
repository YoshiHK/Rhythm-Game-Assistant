# Phase 5 – Feedback Aggregation

This folder defines the **Feedback Aggregation subsystem** for Phase 5 (Productionization).

Purpose:
- Collect player interaction signals related to tips and recommendations
- Preserve explainability by linking feedback to Phase 4 provenance
- Provide curator- and model-facing datasets for offline learning

Non-negotiable rules:
- Downstream-only (must not affect Phase 1–4 behavior)
- Append-only (no mutation of historical records)
- No semantic reinterpretation
