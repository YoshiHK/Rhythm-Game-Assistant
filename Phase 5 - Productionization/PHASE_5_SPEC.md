# PHASE_5_SPEC.md

## Phase 5 — Productionization & Learning Loop

**Status:** Draft (Design-Locked, Not Implemented)  
**Upstream Dependencies:**  
- Phase 1 — Foundation & Workflow ✅  
- Phase 2 — Enhancement ✅  
- Phase 3 — Unified Ingestion Manager ✅  
- Phase 4 — Personalization ✅  
- Phase 4.5 — Localization ✅  

**Non‑Negotiable Rule:** *Do not modify anything in Completed Phases.*

---

## 0. Positioning

Phase 5 defines the **productionization layer** of the Rhythm Game Assistant.

It exists to **close the loop** between:
- explainable tips (Phase 4),
- localized presentation (Phase 4.5),
- and measurable player outcomes.

Phase 5 **does not reinterpret gameplay semantics**.  
It improves *how the system learns and recommends*, not *what tips mean*.

---

## 1. Purpose

Phase 5 exists to:

- turn personalized tips into a **measurable learning system**,
- enable **offline improvement** via curator-backed feedback,
- productionize **song recommendations** as a stable contract,
- prepare the system for scale, experimentation, and trust.

It answers:

> “Given correct and explainable advice, how do we improve outcomes over time?”

---

## 2. Phase Boundary

### Inputs (from Phase 4 / 4.5 only)
- rendered tips text
- selected elements and summaries
- personalization provenance
- locale metadata
- player interaction signals (implicit or explicit)

### Outputs
- recommendation artifacts (song-level)
- feedback datasets
- offline-trained models
- metrics and observability signals

Phase 5 MUST NOT:
- modify element selection
- modify severity, score, or guidance
- alter Phase‑4 outputs at runtime

---

## 3. Invariants

### 3.1 Semantic Immutability
Phase 5 MUST NOT change:
- gameplay advice meaning
- element definitions
- severity labels
- personalization decisions

### 3.2 Offline Learning Only
- All learning occurs **offline**
- No live or online learning is permitted
- Promotion requires validation and rollback safety

### 3.3 Explainability Preservation
- Recommendations MUST carry rationale metadata
- Feedback MUST be linkable to provenance IDs

---

## 4. Core Responsibilities

### 4.1 Feedback Aggregation
- capture tip outcomes (used / ignored / failed)
- capture recommendation outcomes (played / skipped)
- surface signals for curator review

### 4.2 Curator Gold & Labeling
- scale curator review queues
- produce gold labels for retraining
- track disagreement and uncertainty

### 4.3 Offline Retraining & Model Ops
- build training datasets
- validate candidate models
- promote models via gated rollout

### 4.4 Recommendation Productionization
- define song recommendation contracts
- expose read-only recommendation APIs
- attach rationale and provenance metadata

Recommendation Productionization defines contracts and learning signals; it does not implement UI‑level recommendation logic.

### 4.5 Practice & In‑Session Integration (Optional)
- map tips to drills
- enable opt‑in in‑session hints
- record session telemetry (non‑intrusive)

### 4.6 Measurement & Experimentation
- define success metrics
- run A/B tests (presentation-only)
- enforce feature flags and safety bounds

---

## 5. What Phase 5 Is NOT

Phase 5 is NOT:
- a gameplay analysis phase
- a personalization rewrite
- a localization phase
- a game recommendation phase
- a platform hardening phase

---

## 6. Relationship to Later Phases

- Phase 6 hardens what Phase 5 proves
- Phase 7 expands recommendations from songs → games

Phase 5 MUST remain stable and explainable before Phase 7 begins.

---

## 7. Contract Closure

Phase 5 is:
✅ downstream-only  
✅ non-semantic  
✅ explainable  
✅ offline-learning-only  
✅ safe by default  

Phase 5 is NOT:
❌ a live-learning system  
❌ a judgment authority  

---

**End of PHASE_5_SPEC.md**