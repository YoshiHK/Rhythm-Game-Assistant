# Phase 7 — Games Recommendations

**Status:** Design‑Locked · Ranker v1 Frozen  
**Phase Role:** Expansion Pack / Meta‑Discovery Layer  
**Invariant:** Additive · Downstream‑Only · Reversible

---

## 1. Overview

Phase 7 introduces **game‑level recommendations** to the Rhythm Game Assistant.

Unlike earlier phases that operate at the **chart / song / tip** level, Phase 7 operates at the **meta‑game discovery layer**:

> **Which rhythm games should a player try or focus on next — and why?**

Phase 7 adds *new product intelligence* while remaining:

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
- ❌ a platform hardening phase  
- ❌ a UI redesign phase  

All upstream phases (1–6) remain authoritative and unchanged.

---

## 3. Inputs and Outputs

### 3.1 Inputs (Consumed Only)

Phase 7 consumes **existing artifacts only**:

- Player profile and preferences (Phase 4 / 4.5)
- Player completion‑rate submissions and history
- Song recommendation history
- Game registry and enablement status
- Batch difficulty profiles emitted by ingestion (Phase 3)
- Operational guarantees and telemetry (Phase 6)

**Phase 7 MUST NOT introduce new upstream dependencies.**

---

### 3.2 Outputs (Side‑Effect Free)

Phase 7 produces:

- Ranked **game recommendations**
- Human‑readable **explanations** (“why this game”)
- Games Recommendation History records
- Feedback signals forwarded to Phase 5 learning loops

All outputs are **side‑effect free** with respect to Phases 1–6.

---

## 4. Architectural Position


[ Phase 1–4.5 ]  Analysis, Tips, Localization   ← Locked
[ Phase 5     ]  Learning & Contracts           ← Locked
[ Phase 6     ]  Platform Hardening              ← Locked
────────────────────────────────────────────────────
[ Phase 7     ]  Games Recommendations (Discovery)
[ UI / Client ]  Games Recommendation Surfaces

Phase 7 is a **meta‑recommendation layer**, not a core pipeline stage.

Failure or disablement of Phase 7 must **never affect** earlier phases.

---

## 5. Core Subsystems (v1)

### 5.1 Registry & Catalog

- **`registry.py` / `registry_loader.py`**  
  Authoritative list of games and enablement status.

- **`catalog.py` / `catalog_loader.py`**  
  Presentation metadata (display names, localization, UI hints).

- **`catalog_merge.py`**  
  Merges registry + catalog with:
  - locale fallback chains,
  - locale alias support,
  - deterministic display resolution.

---

### 5.2 Router (Entry Point)

- **`router.py`**

The **single Phase 7 entrypoint**.

Responsibilities:
- Registry filtering
- Ranker invocation
- Result shaping
- Failure isolation

Phase 7 routing must never block upstream flows.

---

### 5.3 Ranker (Frozen v1)

- **`ranker_v1.py`**

Deterministic, explainable baseline ranker.

Properties:
- Versioned (`v1`)
- Auditable
- CI‑validated for:
  - eligibility coverage
  - data readiness
  - scoring availability
  - score diversity (including per‑player scenarios)

This ranker establishes the **Phase 7 recommendation contract**.

---

### 5.4 Explanation Engine (Stub)

- **`explanation_engine.py`**

Defines the **explanation contract only**.

Explanation logic is intentionally deferred, but:
- every recommendation MUST be explainable,
- integration with Phase 4.5 i18n is required when implemented.

---

### 5.5 Build & Types

- **`build.py`**  
  Wiring factory for Phase 7 (config + registry + ranker).

- **`types.py`**  
  Frozen contracts:
  - `RecommendationContext`
  - `RecommendationItem`
  - `RecommendationResult`
  - `RunMode`

These types define the **stable interface** for Phase 7 consumers.

---

## 6. Eligibility and Governance

### 6.1 Eligibility Policy

- **`eligibility_policy.py`**

Contains **explicit exclusions** for games that are enabled but not yet recommendable.

- Used by CI checks only
- Not imported by runtime logic
- Prevents silent removal from discovery

---

### 6.2 CI Guarantees (Phase 7)

Phase 7 is protected by CI checks enforcing:

1. ✅ Catalog presentation correctness  
2. ✅ Catalog completeness  
3. ✅ Recommendation eligibility coverage  
4. ✅ Eligibility × data readiness  
5. ✅ Eligibility × scoring availability  
6. ✅ Eligibility × **score diversity**
   - includes **per‑player profile scenarios**
   - enforces deterministic outputs

These guarantees ensure Phase 7 is safe to freeze and evolve.

Phase 7 CI explicitly stops at safety and contract guarantees.
Quality and outcome validation belong to Phase 5 and Phase 6.

---

## 7. Invariants

Phase 7 preserves the following invariants:

- Game recommendations are **advisory**, not prescriptive
- They never suppress or override song‑level outputs
- They exist as a **parallel discovery channel**
- Phase 3–6 contracts remain intact
- Phase 6 remains the sole operational gatekeeper

---

## 8. Extensibility (Future Phases)

Phase 7 is intentionally designed to allow:

- richer player capability modeling,
- more expressive game profiles,
- learned rankers (Phase 5 integration),
- explanation engine expansion,
- feedback‑driven refinement,

**without breaking the v1 contract**.

---

## 9. Summary

Phase 7 is:

- ✅ additive  
- ✅ explainable  
- ✅ downstream‑only  
- ✅ reversible  

Phase 7 is NOT:

- ❌ semantic‑breaking  
- ❌ opaque  
- ❌ upstream‑mutating  

**Phase 7 defines the top‑level discovery loop of the product.**