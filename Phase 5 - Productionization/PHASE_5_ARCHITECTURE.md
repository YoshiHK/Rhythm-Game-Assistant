# PHASE_5_ARCHITECTURE.md

## Phase 5 — Productionization Architecture

**Status on:**  **Status:** Draft (Aligned with PHASE_5_SPEC.md)  
- Phase 3 Canonical Ingestion (Locked)  
- Phase 4 Personalization (Locked)  
- Phase 4.5 Localization (Locked)  

**Invariant:** Phase 5 is downstream-only and non-semantic.

---

## 1. Architectural Role

Phase 5 sits **above** personalization and localization, and **beside** the UI.

Its role is to:
- observe outcomes,
- improve models offline,
- expose stable recommendation contracts,
- prepare the system for scale.

---

## 2. High-Level Data Flow

[ Phase 4 / 4.5 Outputs ]
│
▼
[ Phase 5 Entry ]
│
├─► Feedback Aggregation
│
├─► Curator Review & Gold Labels
│
├─► Offline Training & Validation
│
├─► Recommendation Layer (Song-level)
│
├─► Practice / Session Integration (Optional)
│
└─► Metrics & Experimentation
▼
[ Phase 5 Artifacts ]

---

## 3. Feedback & Signals Layer

Responsibilities:
- collect player interaction signals
- normalize outcome events
- link signals to provenance IDs

This layer is **append-only**.

---

## 4. Curator & Learning Layer

Responsibilities:
- surface review queues
- manage gold labels
- generate training datasets

No runtime decisions are made here.

---

## 5. Offline Training & Promotion

Responsibilities:
- train candidate models
- evaluate against benchmarks
- promote via staged rollout
- support rollback

All models remain **presentation-only**.

---

## 6. Recommendation Layer (Song-Level)

Responsibilities:
- expose recommendation APIs
- attach rationale metadata
- enforce read-only contracts

This layer does not own UI.

---

## 7. Practice & In-Session Integration

Optional sub-layer:
- drill mapping
- opt-in hints
- telemetry capture

Must be disable-able per user.

---

## 8. Observability & Experimentation

Responsibilities:
- define metrics
- run controlled experiments
- enforce safety constraints

No semantic changes permitted.

---

## 9. Relationship to UI and Softr

- Phase 5 exposes APIs
- UI / Softr consume outputs
- UI must not override decisions

---

## 10. Architectural Summary

Phase 5 is:
✅ downstream-only  
✅ explainable  
✅ offline-learning-first  
✅ recommendation-safe  

Phase 5 is NOT:
❌ a semantic authority  
❌ a real-time decision engine  

---

**End of PHASE_5_ARCHITECTURE.md**
