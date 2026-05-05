## PHASE_5_SPEC.md
### Phase 5 — Productionization & Learning Loop

**Status:** Design‑Locked (Not Implemented)  
**Non‑Negotiable Rule:** _Do not modify anything in Completed Phases._

---

## 0. Positioning

Phase 5 defines the **productionization and learning loop**
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

## 2. Phase Boundary

### Inputs (from Phases 4 / 4.5 only)
- rendered tips and summaries
- selected elements
- personalization provenance
- locale metadata
- player interaction signals

### Outputs
- feedback datasets
- gold labels
- trained model artifacts
- recommendation responses
- metrics and observability signals

Phase 5 MUST NOT:
- modify element selection or severity
- perform live or online learning
- deploy or activate models

---

## 3. Invariants

### 3.1 Semantic Immutability
Phase 5 MUST NOT change:
- gameplay advice meaning
- element definitions
- severity labels
- personalization outcomes

### 3.2 Offline Learning Only
- All learning occurs offline
- All promotions require Phase 6 lifecycle approval

### 3.3 Explainability Preservation
- Recommendations MUST carry rationale
- All signals MUST link to provenance IDs

---

## 4. Core Responsibilities

### 4.1 Feedback Aggregation
- capture player and system outcomes
- normalize feedback signals
- prepare curator review inputs

### 4.2 Curator Gold & Labeling
- scale human review
- generate gold labels
- track disagreement and confidence

### 4.3 Offline Retrain & Model Ops
- build training datasets
- train and validate candidate models
- register artifacts for promotion

### 4.4 Recommendation Productionization
- define song‑level recommendation contracts
- expose read‑only APIs with rationale

### 4.5 Practice Integration (Optional)
- map tips to drills
- enable opt‑in in‑session hints
- record practice telemetry

### 4.6 Observability & Experimentation
- define metrics
- run presentation‑only experiments
- enforce feature flag safety

### 4.7 Marketplace Layer
- define creator participation
- manage content catalogs
- emit monetization telemetry

### 4.8 Safety / Legal / Anti‑Cheat
- define unacceptable behaviors
- record safety signals
- escalate evidence to Phase 6

---

## 5. What Phase 5 Is NOT

Phase 5 is NOT:
- a gameplay analysis phase
- a personalization rewrite
- a live‑learning system
- a platform enforcement layer

---

## 6. Relationship to Later Phases

- Phase 6 hardens and governs Phase 5 outputs
- Phase 7 expands recommendations from songs → games

Phase 5 MUST remain stable and explainable before Phase 7 begins.

---

## 7. Contract Closure

Phase 5 is:
✅ downstream‑only  
✅ non‑semantic  
✅ explainable  
✅ offline‑learning‑only  
✅ safe by default  

Phase 5 is NOT:
❌ a judgment authority  

**End of PHASE_5_SPEC.md**