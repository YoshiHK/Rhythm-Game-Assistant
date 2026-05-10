# Phase 7 — Games Recommendations

**Status Additive · Downstream‑Only · Reversible · Non‑Blocking**
**Status:** Design‑Locked ✅, Engineering Complete ✅  

---

## 1. Overview

Phase 7 introduces **game‑level recommendations** to the Rhythm Game Assistant.

Unlike earlier phases that operate at the **chart / song / tip** level,
Phase 7 operates at the **meta‑game discovery layer**:

> **Which rhythm games should a player explore next — and why?**

Phase 7 adds **new discovery intelligence** while remaining:

- ✅ downstream‑only
- ✅ additive
- ✅ explainable
- ✅ non‑intrusive to existing semantics

Phase 7 **never alters**:

- song recommendations,
- chart analysis,
- tips logic,
- or personalization semantics from completed phases.

---

## 2. What Phase 7 Is NOT

Phase 7 is **explicitly NOT**:

- ❌ a tips generation phase
- ❌ a chart analysis phase
- ❌ a personalization override phase
- ❌ a learning or experimentation engine
- ❌ a platform hardening phase
- ❌ a UI redesign phase

All upstream phases (1–6) remain authoritative and unchanged.

---

## 3. Inputs and Outputs

### 3.1 Inputs (Consumed Only)

Phase 7 consumes **existing, stabilized artifacts only**:

- player profile and preferences (Phase 4 / 4.5),
- player completion‑rate submissions and history,
- song and game recommendation history,
- game registry and enablement status,
- batch difficulty profiles emitted by ingestion (Phase 3),
- invocation context and observability hooks (Phase 6).

**Phase 7 MUST NOT introduce new upstream dependencies.**

---

### 3.2 Outputs (Side‑Effect Free)

Phase 7 produces:

- ranked **game recommendations**,
- human‑readable **explanations** (“why this game”),
- recommendation history records,
- feedback events forwarded to Phase 5,
- semantic observability signals.

All outputs are **additive** and **side‑effect free**
with respect to Phases 1–6.

---

## 4. Architectural Position

|[ Phase 1–4.5 ] | Analysis, Tips, Personalization, Localization |  ← Locked
|[ Phase 5     ] | Learning & Productionization                  | ← Locked
|[ Phase 6     ] | Platform Hardening & Scale                    | ← Locked
──────────────────────────────────────────────────────────────
|[ Phase 7     ] | Games Recommendations (Discovery Layer)       |
|[ UI / Client ] | Discovery Surfaces                            |

Phase 7 is a **meta‑recommendation layer**, not a core pipeline stage.

Failure or disablement of Phase 7 must **never affect** earlier phases.

---

## 5. Core Subsystems

### 5.1 Registry & Catalog (Inputs)

- **Registry**
  - Authoritative list of games and enablement status.
  - Read‑only adapter over `games.json`.

- **Catalog**
  - Optional, additive presentation metadata.
  - UI‑facing only (display names, grouping, hints).
  - Absence must never break Phase 7.

---

### 5.2 Routing (Runtime Coordinator)

- **`router.py`**
  - The **single Phase 7 runtime entrypoint**.
  - Coordinates:
    - candidate selection,
    - ranking,
    - explanation attachment,
    - feedback and observability emission.
  - **Coordinator‑only**:
    - no learning,
    - no eligibility logic,
    - no runtime version switching.
  - Fully **non‑blocking** and failure‑isolated.

---

### 5.3 Ranking (Authoritative)

- **`ranker.py`**
  - Single authoritative ranking implementation at runtime.
  - Properties:
    - deterministic,
    - auditable,
    - explainable,
    - no I/O,
    - no runtime versioning.
  - Protected by CI checks for:
    - determinism,
    - scoring availability,
    - non‑degenerate score distributions.

Evolution occurs through **implementation updates only**.

---

### 5.4 Explanation (Bounded)

- **`explanation_engine.py`**
  - Translates structured ranking signals into
    presentation‑safe explanations.
  - Bounded, deterministic, i18n‑ready.
  - No free‑form generation required.

Every recommendation MUST be explainable.

---

### 5.5 Feedback (Forward‑Only)

- **Feedback Layer**
  - Captures user interactions with recommendations.
  - Emits structured events forward to Phase 5.
  - Observational only:
    - no runtime influence,
    - no closed loop inside Phase 7.

---

### 5.6 Observability (Semantic)

- **Observability Layer**
  - Emits semantic metrics:
    - coverage,
    - explainability completeness,
    - degradation signals.
  - Phase 6 owns transport, storage, alerting.

---

### 5.7 Utilities

- **Utils Layer**
  - Pure, mechanical helpers (time, validation, serialization).
  - No domain logic.
  - Safe to import from any Phase 7 module.

---

## 6. Eligibility and Governance

### 6.1 Eligibility Policy (CI‑Only)

- **`eligibility_policy.py`**
  - Contains explicit exclusions for games that are enabled
    but not yet recommendable.
  - Used by CI checks only.
  - **Never imported by runtime logic**.
  - Prevents silent removal from discovery.

---

### 6.2 CI Guarantees (Phase 7)

Phase 7 is protected by CI guardrails enforcing:

- ✅ contract‑level payload shape and non‑blocking behavior,
- ✅ deterministic ranking outputs,
- ✅ catalog safety and presentation robustness,
- ✅ eligibility coverage (no silent exclusion),
- ✅ data readiness for recommendable games,
- ✅ scoring availability,
- ✅ non‑degenerate score distributions,
- ✅ explainability surface coverage.

CI explicitly stops at **safety and contract guarantees**.
Quality and outcome evaluation belong to Phase 5 and Phase 6.

---

## 7. Invariants

Phase 7 preserves the following invariants:

- game recommendations are **advisory**, not prescriptive;
- they never suppress or override song‑level outputs;
- they exist as a **parallel discovery channel**;
- Phase 1–6 contracts remain intact;
- Phase 6 remains the sole operational gatekeeper.

---

## 8. Extensibility

Phase 7 is intentionally designed to allow:

- richer player capability modeling,
- more expressive game profiles,
- improved ranking heuristics,
- explanation expansion,
- feedback‑driven refinement,

**without breaking upstream contracts
or introducing runtime versioning.**

---

## 9. Summary

Phase 7 **IS**:

✅ additive  
✅ explainable  
✅ downstream‑only  
✅ reversible  
✅ non‑blocking  

Phase 7 **IS NOT**:

❌ semantic‑breaking  
❌ opaque  
❌ upstream‑mutating  

**Phase 7 defines the top‑level discovery loop of the product.**
