# Phase 5 — Productionization Architecture

**Status:** Design‑Locked (Aligned with PHASE_5_SPEC.md)  
**Invariant:** Phase 5 is downstream‑only, non‑semantic, and offline‑learning‑only.

---

# Phase 5 — Productionization Architecture

**Status:** Design‑Locked (Aligned with PHASE_5_SPEC.md)  
**Invariant:** Phase 5 is downstream‑only, non‑semantic, and offline‑learning‑only.

---

## Event Entry Layer (NEW)

All pipelines MUST begin with structured events constructed by builders.

DO NOT:
- ingest raw payloads directly
- infer structure inside pipelines

All ingestion MUST occur via:

- feedback_event_builder
- telemetry_event_builder
- marketplace_event_builder
- safety_event_builder

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

```
Phase 4 / 4.5 Outputs
↓
Phase 5 Entry
↓
+----------------------+--------------------+--------------------+
| Feedback Aggregation | Curator & Labeling |  Offline Retraining|
+----------------------+--------------------+--------------------+
↓
+----------------------+--------------------+--------------------+
| Recommendation Layer | Practice (Opt‑In)  |  Observability     |
+----------------------+--------------------+--------------------+
↓
+----------------------+--------------------+
| Marketplace          | Safety / Legal     |
+----------------------+--------------------+
↓
Phase 5 Artifacts
```

---

## 3. Feedback & Signals Layer

**Responsibilities:**
- collect player and system interaction signals,
- normalize and group feedback by provenance,
- preserve append‑only audit trails.

No judgment or scoring occurs here.

---

## 4. Curator & Learning Layer

**Responsibilities:**
- surface curator review queues,
- manage gold labels and disagreement,
- construct versioned training datasets.

All decisions are human‑in‑the‑loop.

---

## 5. Offline Retraining & Model Ops

**Responsibilities:**
- train candidate models offline,
- validate against benchmarks,
- register model artifacts,
- submit promotion candidates to Phase 6.

Phase 5 never deploys models.

---

## 6. Recommendation Layer (Song‑Level)

**Responsibilities:**
- expose stable, read‑only recommendation contracts,
- attach rationale and provenance metadata.

This layer owns contracts, not UI behavior.

---

## 7. Song Recommendation Learning Sub‑Architecture

Song Recommendation learning is implemented as a **dedicated Phase 5 pipeline**.

**Key properties:**
- fully offline,
- deterministic,
- non‑semantic,
- deployment‑only outputs.

**Pipeline structure:**
- feedback aggregation,
- feature construction,
- heuristic calibration,
- evaluation with regression guards,
- static artifact generation.

This sub‑architecture does not bypass curator‑backed learning;
it complements it for song‑level selection quality.

---

## 8. Practice & In‑Session Integration (Optional)

**Responsibilities:**
- practice mapping and drills,
- opt‑in in‑session hints,
- non‑judgmental practice telemetry.

All features must be user‑disableable.

---

## 9. Observability & Experimentation

**Responsibilities:**
- define canonical metrics,
- run presentation‑only experiments,
- enforce feature flags and safety bounds.

No semantic changes are permitted.

---

## 10. Marketplace Layer

**Responsibilities:**
- define creator participation rules,
- manage content catalog references,
- support monetization signals.

Marketplace logic never affects ranking.

---

## 11. Safety / Legal / Anti‑Cheat Signals

**Responsibilities:**
- define unacceptable behaviors,
- record safety‑relevant events,
- escalate evidence to Phase 6.

Phase 5 never enforces penalties.

---

## 12. Architectural Summary

**Phase 5 IS:**
- downstream‑only,
- explainable,
- offline‑learning‑first,
- recommendation‑safe.

**Phase 5 IS NOT:**
- a semantic authority,
- a real‑time decision engine.

---

**End of PHASE_5_ARCHITECTURE.md**