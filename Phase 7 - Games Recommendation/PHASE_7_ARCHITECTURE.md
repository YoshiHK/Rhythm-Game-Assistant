# PHASE_7_ARCHITECTURE.md
## Phase 7 — Games Recommendation Architecture

**Status:** Draft (Aligned with PHASE_7_SPEC.md)  
**Invariant:** Phase 7 is additive and downstream‑only.

---

## 1. Architectural Role

Phase 7 is a **meta‑recommendation and discovery layer**.

It consumes stabilized outputs from prior phases and produces
**game‑level guidance**, without participating in:

- gameplay analysis,
- tips generation,
- personalization adjustment,
- or platform enforcement.

---

## 2. High‑Level Placement

[ Phase 1–4.5 (Analysis & Presentation) ] ← Locked
│
[ Phase 5 (Learning & Contracts) ] ← Locked
│
[ Phase 6 (Hardening & Scale) ] ← Locked
│
──────────────────┼──────────────────
▼
[ Phase 7 (Games Recommendations) ]
│
[ UI / Softr / Client Discovery Surfaces ]

---

## 3. Core Subsystems

### 3.1 Player Profile Encoder

Responsibilities:
- Transform player history into a capability vector
- Capture skill, consistency, and exposure signals
- Deterministic and versioned

No inference logic from earlier phases is reused or modified.

---

### 3.2 Game Profile Encoder

Responsibilities:
- Convert batch difficulty profiles into game vectors
- Represent each game in a shared comparison space
- One profile per game (optionally per difficulty band)

---

### 3.3 Recommendation Ranker

Responsibilities:
- Compute player–game fit scores
- Apply constraints (platform, locale, availability)
- Produce ranked candidate lists
- Maintain scoring version lineage

---

### 3.4 Explanation Engine

Responsibilities:
- Translate scoring signals into human‑readable rationales
- Bind explanations to i18n templates
- Ensure every recommendation is explainable

---

### 3.5 Feedback & Telemetry Sink

Responsibilities:
- Record user interactions with recommendations
- Emit metrics to Phase 6 observability
- Feed Phase 5 learning pipelines

---

## 4. Integration Model

- Phase 7 may execute:
  - post‑ingestion,
  - post‑request,
  - or asynchronously on profile updates.
- Execution is non‑blocking to core flows.
- Failure or disablement of Phase 7 must not affect earlier phases.

---

## 5. Architectural Summary

Phase 7 is:
✅ a discovery layer  
✅ a recommender  
✅ explainable  

Phase 7 is NOT:
❌ a platform layer  
❌ a hardening layer  
❌ a semantic rewrite  

---

**End of PHASE_7_ARCHITECTURE.md**