# System Specification (Phases 1–7)

This document defines the **system-wide contract** of the Rhythm Game Assistant.

## 1) Phase boundaries (normative)

### Phase 1–2: Analytical pipelines (tips generation)
- Inputs: chart exports / structured payloads.
- Outputs (per chart): `tips_text` (2 paragraphs) + canonical per-chart summary.
- Outputs (batch): batch summary.

Phase 2 extends Phase 1 with Track A–D **non-breaking** upgrades: calibrated scoring, selection diversity, guidance phrasing upgrades, narrative word-budget control, while preserving schema shapes.

### Phase 3: Unified Ingestion Manager (UMI)
UMI is the deterministic, auditable orchestration layer between Phase 1–2 pipelines and downstream consumers.
UMI MUST:
- route files to the correct game adapter,
- produce canonical rows and canonical payloads,
- invoke validators,
- invoke Phase 1–2 without altering logic,
- gate optional tips generation via capability config,
- persist outputs and emit batch summaries / run reports.

UMI MUST NOT:
- contain gameplay analysis logic,
- re-implement Phase 1/2,
- decide severity/selection/narrative meaning,
- embed game-specific heuristics,
- perform personalization.

### Phase 4: Personalization & Presentation
Phase 4 consumes only Phase 3 outputs and may apply **non-destructive** presentation adjustments.
Phase 4 MUST NOT modify detected elements, severity labels, scores, training items, or section coverage.
Phase 4 MUST provide deterministic fallback.

### Phase 4.5: Localization & Language Adaptation
Phase 4.5 localizes finalized Phase 4 output.
It MUST NOT alter meaning, intent, ordering/emphasis, severity, or personalization decisions.
It MUST provide deterministic fallback and provenance.

### Phase 5: Productionization & Learning Loop
Phase 5 closes the loop via feedback aggregation, curator labeling, and **offline-only** learning.
Phase 5 MUST NOT alter Phase 4 outputs at runtime and MUST NOT modify semantic meaning.

### Phase 6: Platform Hardening and Scale
Phase 6 hardens the system for reliability, security, compliance, and scale **without changing semantics**.
Phase 6 MUST NOT reinterpret gameplay advice, alter personalization/localization outputs, introduce new learning logic, or override Phase 5 contracts.

### Phase 7: Games Recommendations (Expansion Pack)
Phase 7 adds game-level recommendations as a **downstream-only, additive, explainable, reversible** discovery layer.
Phase 7 MUST NOT:
- alter song/chart recommendations,
- change tips meaning/severity/narrative logic,
- redefine difficulty labels/taxonomies,
- inject logic into Phases 1–6,
- bypass Phase 6 enforcement/observability.

## 2) Invariants (system-wide)
- **Semantic immutability:** gameplay meaning and upstream semantics are preserved; downstream phases do not rewrite earlier phase meaning.
- **Determinism:** deterministic fallback paths exist (notably Phase 4 and Phase 4.5, and UMI dry-run equivalence).
- **Explainability:** outputs are explainable via provenance and transparent scoring logic (especially Phases 4 and 7).
- **Offline learning only:** any learning is offline and promoted via gated rollout (Phase 5).

