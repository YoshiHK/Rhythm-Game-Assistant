## PHASE_5_ARCHITECTURE.md
### Phase 5 — Productionization Architecture

**Status:** Design‑Locked (Aligned with PHASE_5_SPEC.md)  
**Invariant:** Phase 5 is downstream‑only, non‑semantic, and offline‑learning‑only.

---

## 1. Architectural Role

Phase 5 sits **downstream of personalization and localization (Phases 1–4.5)**  
and **upstream of platform hardening (Phase 6)**.

Its role is to:
- observe runtime outcomes,
- convert feedback into learning signals,
- improve models offline,
- expose stable recommendation contracts,
- prepare the system for scale and governance.

Phase 5 never interprets gameplay semantics.

---

## 2. High‑Level Data Flow

[ Phase 4 / 4.5 Outputs ]
│
▼
Phase 5 Entry
│
├─► Feedback Aggregation
│
├─► Curator Gold & Labeling
│
├─► Offline Retrain & Model Ops
│
├─► Recommendation Layer (Song‑Level)
│
├─► Practice Integration (Optional, Opt‑In)
│
├─► Observability & Experimentation
│
├─► Marketplace Layer (Creators & Monetization)
│
└─► Safety / Legal / Anti‑Cheat Signals
▼
[ Phase 5 Artifacts ]

---

## 3. Feedback & Signals Layer

Responsibilities:
- collect player and system interaction signals,
- normalize and group feedback by provenance,
- preserve append‑only audit trails.

No judgment or scoring occurs here.

---

## 4. Curator & Learning Layer

Responsibilities:
- surface curator review queues,
- manage gold labels and disagreement,
- construct versioned training datasets.

All decisions are human‑in‑the‑loop.

---

## 5. Offline Retraining & Model Ops

Responsibilities:
- train candidate models offline,
- validate against benchmarks,
- register model artifacts,
- submit promotion candidates to Phase 6.

Phase 5 never deploys models.

---

## 6. Recommendation Layer (Song‑Level)

Responsibilities:
- expose stable, read‑only recommendation APIs,
- attach rationale and provenance metadata.

This layer owns contracts, not UI behavior.

---

## 7. Practice & In‑Session Integration

Optional sub‑layer:
- practice mapping and drills,
- opt‑in in‑session hints,
- non‑judgmental practice telemetry.

All features must be user‑disableable.

---

## 8. Observability & Experimentation

Responsibilities:
- define canonical metrics,
- run presentation‑only experiments,
- enforce feature flags and safety bounds.

No semantic changes are permitted.

---

## 9. Marketplace Layer

Responsibilities:
- define creator participation rules,
- manage content catalog references,
- support monetization signals.

Marketplace logic never affects ranking.

---

## 10. Safety / Legal / Anti‑Cheat Signals

Responsibilities:
- define unacceptable behaviors,
- record safety‑relevant events,
- escalate evidence to Phase 6.

Phase 5 never enforces penalties.

---

## 11. Architectural Summary

Phase 5 is:
✅ downstream‑only  
✅ explainable  
✅ offline‑learning‑first  
✅ recommendation‑safe  

Phase 5 is NOT:
❌ a semantic authority  
❌ a real‑time decision engine  

**End of PHASE_5_ARCHITECTURE.md**
