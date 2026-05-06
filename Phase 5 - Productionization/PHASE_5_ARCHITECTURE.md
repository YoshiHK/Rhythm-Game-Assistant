# Phase 5 — Productionization Architecture

**Status:** Design‑Locked (Aligned with PHASE_5_SPEC.md)  
**Invariant:** Phase 5 is downstream‑only, non‑semantic, and offline‑learning‑only.

---

## 1. Architectural Role

Phase 5 sits **downstream of personalization and localization (Phases 1–4.5)** and **upstream of platform hardening (Phase 6)**.

Its role is to:
- Observe runtime outcomes
- Convert feedback into learning signals
- Improve models offline
- Expose stable recommendation contracts
- Prepare the system for scale and governance

Phase 5 never interprets gameplay semantics.

---

## 2. High‑Level Data Flow

```
┌─────────────────────────────┐
│ Phase 4 / 4.5 Outputs       │
└─────────────────────────────┘
              ▼
        Phase 5 Entry
              │
        ┌─────┴─────┬─────────┬──────────┬─────────┬──────────┬─────────┬──────────┐
        │           │         │          │         │          │         │          │
        ▼           ▼         ▼          ▼         ▼          ▼         ▼          ▼
    Feedback    Curator   Offline    Recommend. Practice  Observ.  Marketplace  Safety/
    Aggregation  Gold &   Retrain &   Layer     Integration & Exp.   Layer       Legal
                Labeling  Model Ops  (Song-Lvl)  (Opt-In)                       Signals
        │           │         │          │         │          │         │          │
        └─────┬─────┴─────────┴──────────┴─────────┴──────────┴─────────┴──────────┘
              ▼
      Phase 5 Artifacts
```

---

## 3. Feedback & Signals Layer

**Responsibilities:**
- Collect player and system interaction signals
- Normalize and group feedback by provenance
- Preserve append‑only audit trails

No judgment or scoring occurs here.

---

## 4. Curator & Learning Layer

**Responsibilities:**
- Surface curator review queues
- Manage gold labels and disagreement
- Construct versioned training datasets

All decisions are human‑in‑the‑loop.

---

## 5. Offline Retraining & Model Ops

**Responsibilities:**
- Train candidate models offline
- Validate against benchmarks
- Register model artifacts
- Submit promotion candidates to Phase 6

Phase 5 never deploys models.

---

## 6. Recommendation Layer (Song‑Level)

**Responsibilities:**
- Expose stable, read‑only recommendation APIs
- Attach rationale and provenance metadata

This layer owns contracts, not UI behavior.

---

## 7. Practice & In‑Session Integration

**Optional sub‑layer:**
- Practice mapping and drills
- Opt‑in in‑session hints
- Non‑judgmental practice telemetry

All features must be user‑disableable.

---

## 8. Observability & Experimentation

**Responsibilities:**
- Define canonical metrics
- Run presentation‑only experiments
- Enforce feature flags and safety bounds

No semantic changes are permitted.

---

## 9. Marketplace Layer

**Responsibilities:**
- Define creator participation rules
- Manage content catalog references
- Support monetization signals

Marketplace logic never affects ranking.

---

## 10. Safety / Legal / Anti‑Cheat Signals

**Responsibilities:**
- Define unacceptable behaviors
- Record safety‑relevant events
- Escalate evidence to Phase 6

Phase 5 never enforces penalties.

---

## 11. Architectural Summary

| | |
|---|---|
| **Phase 5 IS:** | ✅ Downstream‑only<br/>✅ Explainable<br/>✅ Offline‑learning‑first<br/>✅ Recommendation‑safe |
| **Phase 5 IS NOT:** | ❌ A semantic authority<br/>❌ A real‑time decision engine |

---

**End of PHASE_5_ARCHITECTURE.md**