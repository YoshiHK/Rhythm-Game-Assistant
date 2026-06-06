# PHASE_5_SPEC.md

## Phase 5 — Productionization & Learning Loop

**Status:** Design‑Locked (Not Implemented)  
**Non‑Negotiable Rule:** *Do not modify anything in Completed Phases.*

---

## 0. Positioning

Phase 5 defines the **productionization and offline learning loop**
of the Rhythm Game Assistant.

It closes the loop between:
- explainable tips (Phase 4),
- localized presentation (Phase 4.5),
- and measurable player outcomes.

Phase 5 improves **how the system learns and delivers recommendations**,
not **what gameplay advice means**.

---

## 1. Purpose

Phase 5 exists to:

- convert feedback into curator‑backed learning signals,
- improve models safely via offline retraining,
- productionize song‑level recommendations as stable contracts,
- enable guided practice, experimentation, and monetization,
- prepare the system for governance and scale.

---

### Entry Contract

Phase 5 accepts ONLY structured events.

All inputs MUST:
- follow event schema
- include provenance_id
- be generated via builders

Raw signals MUST NOT enter Phase 5 pipelines directly.

## 2. Phase Boundary

### 2.1 Inputs (from Phases 4 / 4.5 only)

- rendered tips and summaries
- selected elements
- personalization provenance
- locale metadata
- player interaction signals

### 2.2 Outputs

- feedback datasets
- gold labels
- trained model artifacts
- recommendation responses
- metrics and observability signals

Phase 5 MUST NOT:
- modify element selection or severity,
- perform live or online learning,
- deploy or activate models.

---

## 3. Invariants

### 3.1 Semantic Immutability

Phase 5 MUST NOT change:
- gameplay advice meaning,
- element definitions,
- severity labels,
- personalization outcomes.

### 3.2 Offline & Deterministic Learning Only

- All learning occurs offline.
- Learning outputs MUST be deterministic and auditable.
- All promotions require Phase 6 lifecycle approval.
- No runtime adaptation is permitted.

### 3.3 Explainability Preservation

- Recommendations MUST carry rationale.
- All learning signals MUST link to provenance IDs.

---

## 4. Core Responsibilities

### 4.1 Feedback Aggregation
- capture player and system outcomes,
- normalize feedback signals,
- prepare curator review inputs.

### 4.2 Curator Gold & Labeling
- scale human review,
- generate gold labels,
- track disagreement and confidence.

### 4.3 Offline Retrain & Model Ops
- build training datasets,
- train and validate candidate models,
- register artifacts for promotion.

### 4.4 Recommendation Productionization
- define song‑level recommendation contracts,
- expose read‑only APIs with rationale.

### 4.5 Practice Integration (Optional)
- map tips to drills,
- enable opt‑in in‑session hints,
- record practice telemetry.

### 4.6 Observability & Experimentation
- define metrics,
- run presentation‑only experiments,
- enforce feature flag safety.

### 4.7 Marketplace Layer
- define creator participation,
- manage content catalogs,
- emit monetization telemetry.

### 4.8 Safety / Legal / Anti‑Cheat
- define unacceptable behaviors,
- record safety signals,
- escalate evidence to Phase 6.

---

## 5. Song Recommendation Learning Loop (Offline Only)

Song Recommendation learning is a **first‑class Phase 5 learning pipeline**.

It operates as a **fully offline, deterministic loop**:

Phase 6 Runtime
→ feedback emission (exposure + outcomes)
Phase 5 Learning
→ aggregation
→ feature construction
→ heuristic calibration
→ evaluation & regression guards
→ static artifact generation
Deployment
→ Phase 6 configuration update

This loop:
- does not modify gameplay semantics,
- does not perform runtime learning,
- produces deployment‑only static artifacts,
- is guarded by CI‑enforced determinism.

---

## 6. What Phase 5 Is NOT

Phase 5 is NOT:
- a gameplay analysis phase,
- a personalization rewrite,
- a live‑learning system,
- a platform enforcement layer.

---

## 7. Relationship to Later Phases

- Phase 6 hardens and governs Phase 5 outputs.
- Phase 7 expands recommendations from songs → games.

Phase 5 MUST remain stable, deterministic, and explainable
before Phase 7 begins.

---

## 8. Contract Closure

Phase 5 is:

✅ downstream‑only  
✅ non‑semantic  
✅ explainable  
✅ offline‑learning‑only  
✅ deterministic by contract  

Phase 5 is NOT:

❌ a judgment authority  

**End of PHASE_5_SPEC.md**