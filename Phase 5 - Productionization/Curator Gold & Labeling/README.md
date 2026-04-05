# Phase 5 – Curator Gold & Labeling

This folder defines the **Curator Gold & Labeling subsystem** for Phase 5 (Productionization).

Purpose:
- Convert raw feedback signals into high-quality gold labels
- Preserve explainability by anchoring labels to Phase 4 provenance
- Provide authoritative datasets for offline retraining and evaluation

Non-negotiable rules:
- Downstream-only (must not affect Phase 1–4.5 behavior)
- Human-in-the-loop required
- Labels are append-only and versioned
- No runtime decision-making
