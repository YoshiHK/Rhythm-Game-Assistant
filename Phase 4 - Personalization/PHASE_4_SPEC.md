
# PHASE_4_SPEC.md
## Phase 4 — Personalization & Presentation

**Status:** Draft (Ready for Lock Review)

**Upstream Dependencies:**
- Phase 1 — Foundation & Workflow ✅
- Phase 2 — Enhancement ✅
- Phase 3 — Unified Ingestion Manager ✅ (`UMI_SPEC.md`, `UMI_INTERFACES.md`)

**Non‑Negotiable Rule:** *Do not modify anything in Completed Phases.*

---

## 0. Positioning

Phase 4 defines the **personalization and presentation layer** of the Rhythm Game Assistant.

It operates strictly **downstream of Phase 3** and consumes only:
- canonical payloads,
- canonical rows,
- elements skeletons,
- and provenance emitted by Phases 1–3.

Phase 4 **never reinterprets gameplay semantics**. It personalizes *how results are shown*, not *what the results mean*.

---

## 1. Purpose

Phase 4 exists to:
- adapt tips to individual player context,
- improve clarity and engagement,
- preserve determinism, auditability, and trust.

It answers:
> “Given the analytical truth, how should this be presented to this player?”

---

## 2. Phase Boundary

### Inputs (from Phase 3 only)
- Canonical payload
- Canonical row(s)
- Elements skeleton (Phase‑2 output)
- Provenance (Phase‑2 + Phase‑3)

### Outputs
- Rendered tips text
- Presentation metadata
- Personalization provenance

Phase 4 MUST NOT mutate Phase‑3 artifacts.

---

## 3. Invariants

### 3.1 Semantic Immutability
Phase 4 MUST NOT modify:
- detected elements
- severity labels
- scores
- training items
- section coverage

### 3.2 Deterministic Fallback
- A deterministic (non‑personalized) output MUST always be available.
- Personalization is optional and reversible.

### 3.3 Non‑Destructive Adjustments Only
Phase 4 MAY:
- reorder elements
- reweight rankings
- select narrative templates
- choose phrasing variants

Phase 4 MUST NOT create, delete, or rewrite elements.

---

## 4. Engine Modes

### 4.1 Deterministic Mode
- Personalization disabled
- Output equals Phase‑2 narrative

### 4.2 Personalized Mode
- Decision gates evaluated
- Non‑destructive personalization applied
- Deterministic fallback guaranteed

### 4.3 Debug / Audit Mode (optional)
- Deterministic output
- Full decision provenance emitted

---

## 5. Personalization Decision Gates

Personalization MAY occur only if:
- feature flag enabled
- player opted‑in
- required context available
- no safety constraint violated

Gate outcomes MUST be recorded.

---

## 6. Safe Adjustment Interface

Allowed adjustments:
- element ordering
- scalar reweighting
- narrative template selection

Adjustments MUST:
- be additive
- be reversible
- preserve Phase‑2 meaning

### 6.1 Adjustment Traceability (Normative)

All adjustments applied in Phase 4 MUST be traceable across the following layers:

- Model advisory outputs (if any)
- Applied adjustments
- Phase‑4 provenance

If an adjustment is suggested by a model and applied, it MUST be recorded consistently in all applicable layers.
If a model suggestion is dropped or filtered, this MUST be reflected in provenance.

---

## 7. Provenance & Explainability

Every Phase‑4 output MUST include provenance sufficient to explain:

- why this tip
- why this order
- why this phrasing

### 7.1 Required Provenance Fields

Required provenance fields include:

- engine_mode
- gate outcomes
- decision_source (rule | model)
- applied adjustments
- template_id / variant_id
- model identifier(s) (opaque)

### 7.2 Explainability Chain (Normative)

Phase 4 MUST preserve a complete explainability chain:

decision_source → model_outputs → applied_adjustments → provenance

Rules:

- If decision_source = "model":
  - model_outputs MUST be present
  - applied_adjustments MUST reflect the model outputs (after safety filtering)
- If decision_source = "rule":
  - model_outputs MUST be empty
  - applied_adjustments MUST be empty

Any divergence MUST be explicitly recorded in provenance.

### 7.3 Ordering and Ranking Consistency

If a model suggests an element ordering or ranking:

- The rendered output MUST respect that ordering (modulo safety filtering)
- The applied adjustment MUST match the filtered model suggestion
- Provenance MUST record the final applied ordering

Phase 4 MUST NOT silently reorder elements without provenance.

### 7.4 Model Metadata (Optional, Forward-Compatible)

Phase‑4 provenance MAY include model metadata such as:

- model_id
- model_version
- model_role

If model metadata is present:

- it MUST be well‑formed
- it MUST be consistent with decision_source
- when decision_source = "model", model_role MUST be present

Model metadata is optional and MUST NOT be required for deterministic operation.


---

## 8. Model Roles and Constraints

### Allowed
- element re‑ranking
- template selection
- phrasing variant selection

### Prohibited
- gameplay detection
- severity modification
- free‑form text generation

All models are presentation‑only and MUST NOT operate without producing explainable provenance.

---

## 9. Narrative Module v3 Contract

Narrative v3:
- renders text from templates
- enforces word budgets and tone rules
- attaches template and variant metadata

Narrative v3 MUST NOT alter gameplay guidance.

---

## 10. Logging & Feedback

Phase 4 MUST log:
- request ID
- payload hash
- engine mode
- adjustments applied
- template / variant IDs

Feedback:
- is stored with provenance
- does not affect live behavior

---

## 11. Curator & Retraining Loop

- Human curation provides gold labels
- Retraining is offline only
- Promotion requires validation and rollback safety

---

## 12. Safety Guarantees

Phase 4 guarantees:
- no upstream impact
- no hard failures
- deterministic fallback at all times

---

## 13. Contract Closure

Phase 4 is:
✅ downstream‑only
✅ non‑destructive
✅ explainable
✅ safe by default

Phase 4 is NOT:
❌ an analysis phase
❌ a semantic rewrite
❌ a live‑learning system

---

**End of PHASE_4_SPEC.md**
