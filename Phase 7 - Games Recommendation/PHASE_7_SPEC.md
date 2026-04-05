# PHASE_7_SPEC.md
## Phase 7 — Games Recommendations (Expansion Pack)

**Status:** Draft (Design‑Locked, Not Implemented)  
**Upstream Dependencies:**  
- Phase 5 — Productionization ✅  
- Phase 6 — Platform Hardening and Scale ✅  

**Non‑Negotiable Rule:** *Do not modify anything in Completed Phases.*

---

## 0. Positioning

Phase 7 introduces **game‑level recommendations** to the Rhythm Game Assistant.

Unlike earlier phases, which operate at the **chart / song / tip** level, Phase 7 operates at the **meta‑game discovery level**:
> *Which rhythm games should a player try or focus on next, and why?*

Phase 7 **adds new product intelligence** while remaining:
- downstream‑only,
- additive,
- explainable,
- and non‑intrusive to existing semantics.

---

## 1. Purpose

Phase 7 exists to:

- recommend suitable rhythm games based on:
  - demonstrated player skill,
  - preferences,
  - and historical performance;
- guide cross‑game discovery in a multi‑game ecosystem;
- reduce churn caused by poor game–player fit;
- establish a top‑level discovery loop above song recommendations.

It answers:
> “Which games should this player consider next, given what we already know?”

---

## 2. Phase Boundary

### 2.1 Inputs

Phase 7 consumes **existing artifacts only**:

- Player profile and preferences (Phase 4 / 4.5)
- Player completion‑rate submissions and history
- Song recommendation history
- Game registry and enablement status
- Batch difficulty profiles emitted by ingestion (Phase 3)
- Operational guarantees and telemetry (Phase 6)

Phase 7 MUST NOT introduce new upstream dependencies.

---

### 2.2 Outputs

Phase 7 produces:

- Ranked game recommendations
- Human‑readable explanations (“why this game”)
- Games Recommendation History records
- Feedback signals for Phase 5 learning loops

Outputs are **side‑effect free** with respect to Phases 1–6.

---

### 2.3 Explicit Prohibitions

Phase 7 MUST NOT:

- alter song or chart recommendations;
- change tips meaning, severity, or narrative logic;
- redefine difficulty labels or taxonomies;
- inject logic into Phases 1–6;
- bypass Phase 6 enforcement or observability.

---

## 3. Invariants

### 3.1 Semantic Isolation

- Game recommendations are **advisory**, not prescriptive.
- They never suppress or override song‑level outputs.
- They exist as a parallel discovery channel.

---

### 3.2 Contract Preservation

- Phase 3 ingestion outputs remain authoritative.
- Phase 4 / 4.5 personalization outputs remain authoritative.
- Phase 5 learning contracts remain intact.
- Phase 6 remains the sole operational gatekeeper.

---

### 3.3 Explainability Requirement

Every recommendation MUST be explainable using:

- player evidence,
- game capability signals,
- and transparent scoring logic.

Opaque or black‑box recommendations are not permitted in Phase 7.

---

## 4. Core Responsibilities

### 4.1 Player Capability Modeling

- Derive a **player capability profile** from:
  - completion rates,
  - difficulty progression,
  - pattern exposure,
  - stamina and consistency proxies.
- Deterministic and versioned in v1.

---

### 4.2 Game Capability Modeling

- Represent each game using:
  - batch difficulty profiles,
  - dominant pattern categories,
  - structural characteristics where available.
- No re‑analysis of raw charts is allowed.

---

### 4.3 Matching and Ranking

- Compute player–game fit using:
  - skill alignment,
  - pattern affinity,
  - progression suitability,
  - novelty vs familiarity balance.
- Ranking logic MUST be versioned and auditable.

---

### 4.4 Explanation Generation

- Generate concise, localized explanations covering:
  - skill fit,
  - progression rationale,
  - preference alignment.
- Must integrate with Phase 4.5 i18n infrastructure.

---

### 4.5 Feedback Capture

- Record:
  - acceptance,
  - dismissal,
  - “already play” signals.
- Forward signals to Phase 5 learning pipelines.

---

## 5. What Phase 7 Is NOT

Phase 7 is NOT:

- a tips generation phase;
- a chart analysis phase;
- a personalization override phase;
- a platform hardening phase;
- a UI redesign phase.

---

## 6. Relationship to Other Phases

- Phase 7 builds on Phase 6 guarantees.
- Phase 7 may emit learning signals to Phase 5.
- Phase 7 does not unlock new upstream behavior.

---

## 7. Contract Closure

Phase 7 is:
✅ additive  
✅ explainable  
✅ downstream‑only  
✅ reversible  

Phase 7 is NOT:
❌ semantic‑breaking  
❌ opaque  
❌ upstream‑mutating  

---

**End of PHASE_7_SPEC.md**
