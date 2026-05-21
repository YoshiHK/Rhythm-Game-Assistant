
## PHASE_7_ARCHITECTURE.md

### Phase 7 — Games Recommendations Architecture

**Status:** Design‑Locked  
**Invariants:** Additive · Downstream‑Only · Reversible · Non‑Blocking

---

### 1. Architectural Role

Phase 7 is a **meta‑recommendation and discovery layer**.

It operates **above** song‑level recommendations and tips,
answering the question:

**Which rhythm games should a player explore next, and why?**

Phase 7 is explicitly **not** part of:

- gameplay analysis,
- tips generation,
- personalization adjustment,
- runtime learning or experimentation,
- platform enforcement.

---

### 2. High‑Level Placement

[ Phase 1–4.5 ]  Analysis, Tips, Personalization, Localization  (Locked)
[ Phase 5     ]  Learning & Productionization                  (Locked)
[ Phase 6     ]  Platform Hardening & Routing                  (Locked)
[ Phase 7     ]  Games Recommendations (Discovery Layer)
[ UI / Client ]  Discovery Surfaces

Phase 7 is **downstream‑only** and **non‑blocking**:
failure or removal must never affect earlier phases.

---

### 3. Core Subsystems

#### 3.1 Registry & Catalog (Inputs)

- **Registry**
  - Authoritative list of games and enablement status.
  - Read‑only adapter over games.json.

- **Catalog**
  - Optional, additive presentation metadata.
  - UI‑facing only.
  - Absence must never break Phase 7.

---

#### 3.2 Routing (Coordinator)

- Single runtime entrypoint.
- Orchestrates:
  - candidate selection,
  - ranking,
  - explanation,
  - side‑channel emission (feedback, observability).

Coordinator only:
- no learning,
- no runtime version switching,
- no I/O.

---

#### 3.3 Ranking (Authoritative)

- Single deterministic ranker implementation at runtime.
- Properties:
  - deterministic,
  - auditable,
  - explainable,
  - no I/O.
- Ranking behavior MAY evolve only via deployment.

---

#### 3.4 Explanation (Bounded)

- Translates structured ranking signals into
  presentation‑safe explanations.
- Bounded, deterministic, i18n‑ready.

---

#### 3.5 Feedback (Forward‑Only)

- Captures user interactions with recommendations.
- Emits structured feedback events.
- Observational only:
  - no runtime influence,
  - no closed loop inside Phase 7.

---

#### 3.6 Learning Loop (Cross‑Phase)

The learning loop spans multiple phases:

Phase 7  ── emit feedback ──▶  Phase 5
Phase 5  ── offline learning / calibration ──▶  Deployment
Deployment ── updated ranker / parameters ──▶  Phase 7

Key properties:
- No runtime learning in Phase 7.
- No feedback consumption in Phase 7.
- Phase 6 governs rollout, rollback, and isolation.

---

#### 3.7 Observability (Semantic)

- Emits semantic metrics:
  - coverage,
  - explainability completeness,
  - degradation signals.
- Phase 6 owns transport, storage, and alerting.

---

### 4. Integration Model

- Phase 7 is invoked **only via Phase 6**.
- Phase 6 owns:
  - authentication,
  - authorization,
  - rate limiting,
  - lifecycle control,
  - failure isolation.

Phase 7 never assumes transport or persistence guarantees.

---

### 5. Failure Semantics

- Phase 7 failures are **isolated**.
- On failure or disablement:
  - return empty recommendations,
  - emit observability signals,
  - never block upstream flows.

---

### 6. Architectural Summary

Phase 7 **IS**:
- a discovery layer,
- a recommender,
- explainable,
- learning‑enabled (offline),
- additive and reversible.

Phase 7 **IS NOT**:
- a platform layer,
- a runtime learning engine,
- a personalization override,
- a semantic rewrite.

---

**End of PHASE_7_ARCHITECTURE.md**