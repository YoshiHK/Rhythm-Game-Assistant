# PHASE_7_ARCHITECTURE.md# PHASE_7 7 — Games Recommendations Architecture

**Status:** Design‑Locked  
**Invariants:** Additive · Downstream‑Only · Reversible · Non‑Blocking

---

## 1. Architectural Role

Phase 7 is a **meta‑recommendation and discovery layer**.

It operates **above** song‑level recommendations and tips,
answering the question:

> **Which rhythm games should a player explore next, and why?**

Phase 7 is explicitly **not** part of:
- gameplay analysis,
- tips generation,
- personalization adjustment,
- learning or experimentation,
- or platform enforcement.

---

## 2. High‑Level Placement

[ Phase 1–4.5 ]  Analysis, Tips, Personalization, Localization  ← Locked
[ Phase 5     ]  Learning & Productionization                  ← Locked
[ Phase 6     ]  Platform Hardening & Scale                    ← Locked
──────────────────────────────────────────────────────────────
[ Phase 7     ]  Games Recommendations (Discovery Layer)
[ UI / Client ]  Discovery Surfaces

Phase 7 is **downstream‑only** and **non‑blocking**:
failure or removal must never affect earlier phases.

---

## 3. Core Subsystems

### 3.1 Registry & Catalog (Inputs)

- **Registry**
  - Authoritative list of games and enablement status.
  - Read‑only adapter over `games.json`.

- **Catalog**
  - Optional, additive presentation metadata.
  - UI‑facing only (display names, icons, grouping).
  - Absence must never break Phase 7.

---

### 3.2 Routing (Coordinator)

- Single runtime entrypoint.
- Orchestrates:
  - candidate selection,
  - ranking,
  - explanation,
  - side‑channel emission (feedback, observability).
- **Coordinator only**:
  - no learning,
  - no eligibility logic,
  - no runtime version switching.

---

### 3.3 Ranking (Authoritative)

- Single deterministic ranker implementation at runtime.
- Properties:
  - deterministic,
  - auditable,
  - explainable,
  - no I/O,
  - no runtime versioning.
- Evolution occurs via **implementation updates**, not schema switching.

---

### 3.4 Explanation (Bounded)

- Translates structured ranking signals into
  presentation‑safe explanations.
- Bounded, deterministic, i18n‑ready.
- No free‑form generation required.

---

### 3.5 Feedback (Forward‑Only)

- Captures user interactions with recommendations.
- Emits structured events forward to Phase 5.
- Observational only:
  - no runtime influence,
  - no closed loop inside Phase 7.

---

### 3.6 Observability (Semantic)

- Emits semantic metrics:
  - coverage,
  - explainability completeness,
  - degradation signals.
- Phase 6 owns transport, storage, alerting.

---

## 4. Integration Model

- Phase 7 is invoked **only via Phase 6**.
- Phase 6 owns:
  - authentication,
  - authorization,
  - rate limiting,
  - lifecycle control,
  - failure isolation.

Phase 7 never assumes transport or persistence guarantees.

---

## 5. Failure Semantics

- Phase 7 failures are **isolated**.
- On failure or disablement:
  - return empty recommendations,
  - emit observability signals,
  - never block upstream flows.

---

## 6. Architectural Summary

Phase 7 **IS**:
- a discovery layer,
- a recommender,
- explainable,
- additive and reversible.

Phase 7 **IS NOT**:
- a platform layer,
- a learning engine,
- a personalization override,
- a semantic rewrite.

**End of PHASE_7_ARCHITECTURE.md**