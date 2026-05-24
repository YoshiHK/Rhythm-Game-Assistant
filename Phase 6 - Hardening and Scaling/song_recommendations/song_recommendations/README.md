
# Phase 6 — Song Recommendations

**Status:** Additive · Deterministic · Non‑Semantic · Learning‑Safe  
**Design Status:** Design‑Locked ✅ · Engineering In‑Progress ✅

---

## 1. Purpose

The Song Recommendation domain provides **deterministic song selection**
for rhythm game players, under Phase 6 platform governance.

It answers the question:

> **Which songs should a player practice next — right now — and why?**

This domain focuses on **selection and presentation**, not gameplay meaning.

---

## 2. What This Domain IS

Song Recommendation **IS**:

- A **runtime orchestration domain** under Phase 6
- Deterministic and reproducible
- Non‑semantic (no gameplay judgment)
- Additive to existing tips and analysis pipelines
- Safe to observe and learn from (offline)

---

## 3. What This Domain Is NOT

Song Recommendation **IS NOT**:

- ❌ a tips generation system
- ❌ a chart analysis pipeline
- ❌ a personalization inference engine
- ❌ a runtime learning or experimentation system
- ❌ a replacement for Phase 1–4 outputs

All gameplay semantics remain owned by completed phases.

---

## 4. Architectural Position

[ Phase 1–4.5 ]  Analysis · Tips · Personalization · Localization   ← Locked
[ Phase 5     ]  Offline Learning & Productionization               ← Locked
[ Phase 6     ]  Platform Hardening & Runtime Routing                ← Gatekeeper
────────────────────────────────────────────────────────────────────
[ Song Recommendation Domain ]  (mode="songs")
[ UI / Client ]

Failure or disablement of Song Recommendations
**must never affect upstream phases**.

---

## 5. Core Components

### 5.1 Catalog Loader
- Loads canonical song artifacts from offline ingestion
- Read‑only, deterministic
- Emits catalog fingerprint for diagnostics

### 5.2 Catalog Selector
- Deterministic selection based on numeric proximity windows
- No ranking, no randomness
- Emits **selection diagnostics only**:
  - window used
  - widen step
  - producer proximity

### 5.3 Coordinator
- Orchestrates request normalization, selection, response shaping
- No learning, no inference
- Fully governed by Phase 6 routing

### 5.4 Response Shaper
- Assembles API‑safe response
- Adds stable recommendation_set_id
- Adds per‑item exposure rank
- Passes through diagnostics without interpretation

### 5.5 Feedback Layer
- Captures user reactions to song recommendations
- Emits forward‑only feedback events
- Does not influence runtime behavior

---

## 6. Learning Loop Contract (Song Recommendations)

Song Recommendations support a **strictly offline learning loop**.

### Runtime (Phase 6)
- Selection is deterministic
- Feedback is emitted but never consumed
- No model inference or adaptation

### Offline (Phase 5)
- Feedback is aggregated and analyzed
- Learnable targets include:
  - window widening effectiveness
  - tier targeting accuracy
  - producer diversity trade‑offs
- Forbidden learning targets:
  - tips content
  - taxonomy
  - severity
  - gameplay semantics

### Deployment
- Learned changes are introduced via deployment only
- No runtime parameter tuning is permitted

---

## 7. Invariants

The following invariants MUST always hold:

- Song recommendations never alter tips semantics
- Song recommendations never suppress analysis outputs
- Runtime selection remains deterministic
- Learning is offline only
- Phase 6 remains the sole operational gatekeeper

Violating any of these breaks phase boundaries.

---

## 8. Design Intent

This domain exists to make Song Recommendations:

✅ useful to players  
✅ safe to evolve  
✅ safe to audit  
✅ safe to learn from  

without making them unsafe to run.

---

**Learning is allowed.  Runtime adaptation is not.**