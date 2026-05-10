## ORCHESTRATOR_EXTENSION_CHECKLIST.md

**Purpose:**  
Define the minimum conditions under which the Orchestrator Extension is considered
**stable, correct, and ready for long‑term steady‑state operation** (≈10–25 games).

This checklist is **authoritative**.

---

### 0. Non‑Negotiable Rule

> **Completed semantic phases MUST NOT be modified.  
> Wiring between phases MAY evolve freely.**

Any violation invalidates the extension by definition.

---

### 1. Phase Boundary Integrity ✅

**Required**
- No changes to Phase 1 logic
- No changes to Phase 2 logic
- No changes to Phase 4 logic
- Orchestration imports no Phase 1/2/4 implementations
- No gameplay heuristics in extension modules

**Validation**
- Extension depends only on:
  - `types.py`
  - `reason_codes.py`
  - `interfaces.py`
  - configuration and schemas

---

### 2. Control‑Plane Separation ✅

**Required**
- Orchestrator Extension is control‑plane only
- Decisions concern execution, not content
- STOP / DEGRADED are explicit and reasoned
- No silent fallback

**Validation**
- Any early exit produces:
  - decision
  - stage
  - reason_code

---

### 3. Feature Flag Discipline ✅

**Required**
- All extension behavior gated by FeatureFlags
- Defaults preserve legacy behavior
- Flags are orthogonal
- Flag digest contributes to RunKey

**Validation**
- All flags OFF ⇒ identical behavior to pre‑extension

---

### 4. Run Identity & Determinism ✅

**Required**
- Deterministic RunKey per run
- RunKey includes:
  - game_id
  - chart_id
  - difficulty (if any)
  - adapter version
  - pipeline version
  - feature flag digest

**Validation**
- Same inputs ⇒ same RunKey
- Retries do not change identity

---

### 5. STOP / DEGRADED Semantics ✅

**Required**
- All STOP decisions include stable reason_code
- DEGRADED runs explicitly marked
- No silent downgrade

**Validation**
- A human can answer:
  **“Why didn’t tips generate?”** by reading one field.

---

### 6. Multi‑Game Safety ✅

**Required**
- No `if game_id == ...` logic
- Per‑game differences via config
- Failures isolated per game
- Circuit breakers scoped per game

---

### 7. RunPlan Simplicity ✅

**Required**
- Declarative run plan
- Explicit stage order
- No hidden DAG inference

---

### 8. Stabilization Guarantees ✅

**Required**
- Exceptions converted to STOP
- Retry bounded and explicit
- Circuit breaker isolated
- No crash escapes orchestrator

---

### 9. Observability & Reporting ✅

**Required**
- Structured RunReport available
- CLI JSON surfaces STOP / DEGRADED
- Schema validation exists
- Reporting is non‑blocking

---

### 10. Schema & Contract Enforcement ✅

**Required**
- JSON schemas exist for:
  - RunReport
  - CLI projection
- Fallback structural checks exist

---

### 11. Localization Readiness ✅

**Required**
- Orchestration locale‑agnostic
- Localization is wiring only
- No semantic impact

---

### 12. Production Readiness ✅

**Required**
- All above satisfied
- STOP reasons stable and documented
- Failures explainable to non‑engineers

---

### 13. Explicit Anti‑Patterns 🚫

Never allowed:
- Semantic fixes in orchestration
- Game‑specific branching
- Silent retries
- Canonical payload mutation

---

### 14. Steady‑State Declaration

If all items pass, the Orchestrator Extension is:

✅ Stable  
✅ Correct  
✅ Scalable within bounds  
✅ Ready for long‑term maintenance