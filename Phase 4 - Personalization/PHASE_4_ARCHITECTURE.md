
# PHASE_4_ARCHITECTURE.md
## Phase 4 — Personalization & Presentation Architecture

**Status:** Draft (Aligned with PHASE_4_SPEC.md)

**Depends on:**
- Phase 1–2 Analytical Pipelines (Locked)
- Phase 3 Unified Ingestion Manager (Locked)

**Invariant:** Phase 4 is downstream-only and non-destructive.

---

## 1. Architectural Role

Phase 4 sits **above** the Unified Ingestion Manager (Phase 3) and **below** the user interface.

Its role is to:
- personalize presentation,
- select ordering and phrasing,
- provide explainable, player-aware outputs.

Phase 4 does **not** participate in gameplay analysis.

---

## 2. High-Level Data Flow


Phase 4 preserves a complete explainability chain across all layers:

decision_source → model_outputs → applied_adjustments → provenance


```
[ Phase 3 Outputs ]
    │
    │  canonical payload
    │  canonical rows
    │  elements skeleton
    │  provenance
    ▼
[ Phase 4 Entry ]
    │
    ├─► Decision Gates
    │       │
    │       ├─ disabled → deterministic path
    │       └─ enabled  → personalization path
    │
    ├─► Model Inference Layer (optional)
    │       │
    │       ├─ ranking weights
    │       ├─ template selection
    │       └─ variant choice
    │
    ├─► Safe Adjustment Application
    │       │
    │       └─ non-destructive transforms
    │
    ├─► Narrative Module v3
    │       │
    │       └─ localized rendering
    │
    ▼
[ Phase 4 Output ]
    tip text + provenance
```

---

## 3. Phase 4 Entry Layer

### Responsibilities
- Accept Phase 3 outputs
- Accept optional player context
- Select engine mode

### Inputs
- canonical_payload
- canonical_row(s)
- elements_skeleton
- provenance
- player_id (optional)
- engine_mode flag

No mutation occurs at entry.

---

## 4. Decision Gate Layer

Decision gates are **rule-based and deterministic**.

They evaluate:
- player opt-in
- feature flags
- cohort eligibility
- safety constraints

If any gate fails:
- personalization is skipped
- deterministic output is used

Gate outcomes are recorded in provenance.

---

## 5. Model Inference Layer (Optional)

Models in Phase 4 are **assistive only**.

### Allowed Outputs
- per-element reweighting scalars
- narrative template IDs
- variant IDs

### Architectural Constraints
- models never see raw chart data
- models never modify elements
- models never emit free-form text

All model outputs are advisory.

### 5.1 Traceability Contract

If the Model Inference Layer produces outputs:

- those outputs MUST be passed unchanged to the Safe Adjustment Layer
- any filtering or rejection MUST be recorded in provenance
- model outputs MUST NOT be silently ignored

If the Model Inference Layer is skipped, provenance MUST reflect rule-based execution.

---

## 6. Safe Adjustment Layer

This layer applies personalization effects **without semantic mutation**.

Allowed adjustments:
- reorder elements
- apply scalar weights
- select narrative template

Prohibited actions:
- changing severity
- adding or removing elements
- rewriting guidance

All adjustments are reversible.

### 6.1 Adjustment Consistency

All applied adjustments MUST:

- originate from either deterministic rules or model outputs
- be explicitly recorded in applied_adjustments
- be reflected consistently in provenance

Phase 4 MUST NOT apply presentation changes that are not traceable.

---

## 7. Narrative Module v3

Narrative Module v3 is a **pure renderer**.

### Inputs
- elements skeleton (unchanged)
- selected template ID
- locale
- difficulty label

### Guarantees
- word budget enforcement
- tone consistency
- template-bound variation only

Narrative v3 never alters gameplay meaning.

---

## 8. Output Assembly Layer

Phase 4 outputs:
- rendered tips text
- unchanged elements skeleton
- full personalization provenance

These outputs are passed to the UI layer.

The Output Assembly Layer is responsible for:

- final consistency validation between:
  - model outputs
  - applied adjustments
  - provenance
- attaching model metadata when available

### 8.1 Model Metadata (Optional)

Phase 4 MAY attach model metadata to provenance.

If present, model metadata MUST:

- be well-formed
- align with decision_source
- identify the model’s role in presentation

Model metadata MUST NOT be required for deterministic execution.

---

## 9. Logging & Telemetry

Phase 4 emits structured events for:
- request metadata
- decision gates
- model outputs
- adjustments applied
- user interactions

Logs are append-only and audit-safe.

---

## 10. Feedback & Curation Path

User feedback and flags are:
- captured asynchronously
- linked to provenance
- surfaced for curator review

Curator actions never affect live behavior.

---

## 11. Offline Training & Promotion

- training is offline only
- datasets are versioned
- promotion uses staging + canary
- rollback is always possible

No online learning exists in Phase 4.

---

## 12. Safety & Failure Isolation

Phase 4 guarantees:
- deterministic fallback
- no upstream impact
- no hard dependency on models

Failures in explainability, traceability, or metadata attachment MUST result in deterministic fallback.

---

## 13. Relationship to UI

Phase 4 provides:
- casual vs expert variants
- explainability metadata
- localized text

The UI is responsible for presentation only.

---

## 14. Architectural Summary

Phase 4 is:
✅ downstream-only
✅ non-destructive
✅ explainable by construction
✅ fully traceable across layers
✅ model-optional
✅ safe by default

---

**End of PHASE_4_ARCHITECTURE.md**
