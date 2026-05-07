## PHASE_4_ARCHITECTURE.md
### Phase 4 — Personalization & Presentation Architecture

**Status:** ✅ Implementation‑Aligned  
**Invariant:** Phase 4 is downstream‑only and non‑destructive.

---

## 1. Architectural Role

Phase 4 sits **above Phase 3 (Unified Ingestion Manager)** and **below the UI layer**.

Its responsibility is to personalize **presentation only**, while preserving analytical truth.

Phase 4:
- adapts ordering and phrasing
- selects narrative templates and variants
- emits explainable, auditable outputs

Phase 4 does **not** participate in gameplay analysis.

---

## 2. High‑Level Flow

### 2.1 End‑to‑End Runtime Flow (Normative)

Phase 3 Outputs
  ├─ canonical payload
  ├─ canonical rows
  ├─ elements skeleton
  └─ upstream provenance
        │
        ▼
[ Phase 4 Runtime Entry ]
        │
        ├─ (1) Personalization Decision (rule‑based)
        │       ├─ gates fail → deterministic path
        │       └─ gates pass → personalization path
        │
        ├─ (2) Model Inference (optional, advisory)
        │
        ├─ (3) Safe Adjustment (non‑destructive)
        │
        ├─ (4) Narrative Module v3 (pure renderer)
        │
        ▼
[ Phase 4 Output ]
  ├─ rendered tips text
  ├─ presentation metadata
  └─ full provenance

Failure Rule
Any failure or invariant violation MUST result in deterministic fallback.

---

## 3. Decision Layer
Decision gates are:

deterministic
rule‑based
fully recorded in provenance

If any gate fails:

personalization is skipped
deterministic output is used

---

## 4. Inference Layer (Optional)
The inference layer:

is advisory only
never emits free‑form text
never modifies elements

Possible outputs:

ranking weights
narrative template ID
variant ID

If inference is skipped, provenance MUST reflect rule‑based execution.

---

## 5. Safe Adjustment Layer
This layer applies presentation‑only changes.
Allowed:

element ordering
scalar weighting
template / variant selection

Prohibited:

semantic modification
element creation or deletion

All applied adjustments MUST be recorded.

---

## 6. Narrative Module v3
Narrative v3:

renders template‑bound text
enforces tone and word budgets
attaches template / variant metadata

Narrative v3 never alters gameplay meaning.

---

## 7. Events and Feedback
Phase 4 emits:

structured, append‑only events
feedback capture records

Events and feedback:

never affect runtime behavior
are used for audit and offline learning only.

---

## 8. Curator Loop
Curators:

review outputs
provide gold labels
trigger offline retraining

Promotion is manual and reversible.

---

## 9. CI Enforcement
CI enforces:

determinism
safety (non‑destructive)
explainability

Any violation blocks deployment.

---

## 10. Architectural Summary
Phase 4 is:

✅ deterministic by default
✅ personalization‑optional
✅ explainable end‑to‑end
✅ safe and auditable

---

End of PHASE_4_ARCHITECTURE.md
