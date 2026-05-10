# PHASE_7_SPEC.md
## Phase 7 — Games Recommendations (Expansion**Upstream Dependencies:** Phase 1–6 (Read‑Only)## Phase 7 — Games Recommendations (Expansion Pack)

**Non‑Negotiable Rule:**  
> **Do not modify anything in Completed Phases.**

---

## 0. Positioning

Phase 7 introduces **game‑level recommendations**
to the Rhythm Game Assistant.

Unlike earlier phases that operate at the chart / song / tip level,
Phase 7 operates at the **meta‑game discovery level**.

---

## 1. Purpose

Phase 7 exists to:

- recommend suitable rhythm games based on:
  - demonstrated player capability,
  - preferences,
  - historical interaction;
- guide cross‑game discovery in a multi‑game ecosystem;
- reduce churn caused by poor game–player fit;
- establish a discovery loop above song recommendations.

---

## 2. Phase Boundary

### 2.1 Inputs (Consumed Only)

Phase 7 MAY consume:

- player profile and preferences (Phase 4 / 4.5),
- player history and completion‑rate summaries,
- song and game recommendation history,
- game registry and catalog metadata,
- batch difficulty profiles (Phase 3),
- invocation context and observability hooks (Phase 6).

Phase 7 MUST NOT introduce new upstream dependencies.

---

### 2.2 Outputs (Side‑Effect Free)

Phase 7 produces:

- ranked game recommendations,
- human‑readable explanations,
- recommendation history records,
- feedback events forwarded to Phase 5,
- semantic observability signals.

All outputs are additive and side‑effect free
with respect to Phases 1–6.

---

### 2.3 Explicit Prohibitions

Phase 7 MUST NOT:

- alter song or chart recommendations;
- change tips meaning, severity, or narrative;
- redefine difficulty taxonomies;
- import or mutate Phase 1–6 logic;
- bypass Phase 6 enforcement;
- perform runtime version switching.

---

## 3. Invariants

### 3.1 Semantic Isolation

- Game recommendations are **advisory**, not prescriptive.
- They never suppress or override song‑level outputs.
- They exist as a parallel discovery channel.

---

### 3.2 Contract Preservation

- Phase 7 uses **versionless contracts**.
- Evolution occurs via implementation updates only.
- Backward compatibility is enforced by CI, not runtime branching.

---

### 3.3 Explainability Requirement

Every recommendation MUST be explainable using:

- player evidence,
- game capability signals,
- deterministic scoring logic.

Opaque or black‑box recommendations are not permitted.

---

## 4. Core Responsibilities

Phase 7 is responsible for:

1. Player capability modeling (deterministic).
2. Game capability modeling (from stabilized artifacts).
3. Matching and ranking (single authoritative ranker).
4. Explanation generation (bounded, i18n‑ready).
5. Feedback capture (forward‑only).
6. Observability emission (semantic metrics only).

---

## 5. What Phase 7 Is NOT

Phase 7 is NOT:

- a tips generation phase;
- a chart analysis phase;
- a personalization override;
- a learning or experimentation engine;
- a platform hardening phase.

---

## 6. Relationship to Other Phases

- Phase 7 builds on Phase 6 guarantees.
- Phase 7 emits signals to Phase 5.
- Phase 7 does not unlock new upstream behavior.

---

## 7. Contract Closure

Phase 7 is:

✅ additive  
✅ explainable  
✅ downstream‑only  
✅ reversible  
✅ non‑blocking  

Phase 7 is NOT:

❌ semantic‑breaking  
❌ opaque  
❌ upstream‑mutating  

**End of PHASE_7_SPEC.md**
``

**Status:** Design‑Locked  
