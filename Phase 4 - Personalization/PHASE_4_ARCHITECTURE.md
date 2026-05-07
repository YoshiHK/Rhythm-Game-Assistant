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

```text
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

## 3. Architectural Summary

Phase 4 is:
✅ deterministic by default
✅ personalization‑optional
✅ explainable end‑to‑end
✅ safe and auditable

End of PHASE_4_ARCHITECTURE.md