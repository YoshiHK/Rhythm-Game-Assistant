## PHASE 4 SPEC
### Phase 4 — Personalization & Presentation

**Status:** ✅ Normative (Contract Locked)

**Upstream Dependencies:**
- Phase 1 — Foundation & Workflow ✅
- Phase 2 — Enhancement ✅
- Phase 3 — Unified Ingestion Manager ✅

**Non‑Negotiable Rule:**  
**Phase 4 MUST NOT modify anything in Completed Phases.**

---

### 0. Positioning

Phase 4 defines the **personalization and presentation layer** of the system.

It operates strictly downstream of Phase 3 and consumes only:
- canonical payloads
- canonical rows
- elements skeletons
- upstream provenance

Phase 4 personalizes **how results are shown**, never **what they mean**.

---

### 1. Purpose

Phase 4 exists to:
- adapt presentation to player context
- improve clarity and engagement
- preserve determinism, auditability, and trust

---

### 2. Phase Boundary

#### Inputs (from Phase 3 only)
- canonical payload
- canonical row(s)
- elements skeleton
- upstream provenance

#### Outputs
- rendered tips text
- presentation metadata
- Phase 4 provenance

**Phase 4 MUST NOT mutate Phase 3 artifacts.**

---

### 3. Invariants (Normative)

#### 3.1 Semantic Immutability

Phase 4 MUST NOT modify:
- detected elements
- severity labels
- scores
- training items
- section coverage
- guidance text

#### 3.2 Deterministic Fallback

- A deterministic, non-personalized output MUST always exist.
- Personalization MUST be optional and reversible.

#### 3.3 Non‑Destructive Adjustments Only

Phase 4 MAY:
- reorder elements
- reweight rankings
- select narrative templates
- select phrasing variants

Phase 4 MUST NOT:
- create elements
- delete elements
- rewrite gameplay meaning

---

### 4. Engine Modes

- **deterministic**: no personalization
- **personalized**: gated, explainable personalization
- **debug**: deterministic output with full provenance

---

### 5. Personalization Decision Gates

Personalization MAY occur only if all gates pass:
- feature flag enabled
- player opt-in
- required context available
- safety constraints satisfied

Gate outcomes MUST be recorded in provenance.

---

### 6. Safe Adjustment Interface

Allowed adjustments:
- element ordering
- scalar reweighting
- narrative template selection
- variant selection

Adjustments MUST:
- be additive
- be reversible
- preserve Phase 2 meaning

---

### 7. Provenance & Explainability

Every Phase 4 output MUST include provenance explaining:
- decision source
- gate outcomes
- applied adjustments
- template and variant IDs

No personalization is allowed without explainability.

---

### 8. Models (Constraints)

Models in Phase 4 are presentation-only.

Allowed:
- ranking
- template selection
- variant selection

Prohibited:
- gameplay detection
- severity modification
- free-form text generation

---

### 9. Narrative Module v3

Narrative v3:
- renders template-bound text
- enforces tone and word budgets
- attaches template/variant metadata

Narrative v3 MUST NOT alter gameplay guidance.

---

### 10. Logging, Feedback, and Curation

Phase 4 MUST emit:
- structured event logs
- feedback capture records

Feedback and curator actions:
- are offline only
- MUST NOT affect live behavior

---

### 11. Contract Closure

Phase 4 is:
✅ downstream-only  
✅ non-destructive  
✅ deterministic by default  
✅ explainable by construction  

Phase 4 is NOT:
❌ an analysis phase  
❌ a semantic rewrite  
❌ a live-learning system  

**End of PHASE_4_SPEC.md**
``
