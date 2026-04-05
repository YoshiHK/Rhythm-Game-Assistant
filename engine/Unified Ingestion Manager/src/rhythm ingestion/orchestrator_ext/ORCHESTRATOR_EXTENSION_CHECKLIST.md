# ORCHESTRATOR_EXTENSION_CHECKLIST.md

**Purpose:**  
Define the minimum conditions under which the Orchestrator Extension can be
considered **stable, correct, and ready for long‑term steady‑state operation**
(≈10–25 rhythm game models).

This checklist is **authoritative** and applies to:
- adding a new game
- enabling new orchestration features
- entering Phase 4.5+
- declaring Phase 5 readiness

---

## 0. Non‑Negotiable Rule (Must Always Hold)

> **Completed semantic phases MUST NOT be modified.  
> Wiring between phases MAY evolve freely.**

If any item below violates this rule, it is **invalid by definition**.

---

## 1. Phase Boundary Integrity ✅

### Required
- [ ] No changes to Phase 1 logic (detection, tagging, inference)
- [ ] No changes to Phase 2 logic (severity, selection, narrative)
- [ ] No changes to Phase 4 personalization logic
- [ ] No orchestration code imports Phase 1/2/4 implementation details
- [ ] No gameplay heuristics appear in orchestrator extension modules

### Validation Signal
- Orchestration modules only depend on:
  - `types.py`
  - `reason_codes.py`
  - `interfaces.py`
  - configuration / schemas

---

## 2. Control‑Plane Separation ✅

### Required
- [ ] Orchestrator Extension is **control‑plane only**
- [ ] All decisions are *about execution*, not *content*
- [ ] STOP / DEGRADED decisions are explicit and reasoned
- [ ] No silent fallback paths exist

### Validation Signal
- Any early exit produces:
  - `decision`
  - `stage`
  - `reason_code`

---

## 3. Feature Flag Discipline ✅

### Required
- [ ] All extension behavior is gated by `FeatureFlags`
- [ ] Default flags preserve legacy behavior (pass‑through)
- [ ] Flags are orthogonal (no hidden coupling)
- [ ] Flag digest contributes to `RunKey`

### Validation Signal
- Turning **all flags OFF** yields identical behavior to pre‑extension orchestration

---

## 4. Run Identity & Determinism ✅

### Required
- [ ] Every run computes a deterministic `RunKey`
- [ ] `RunKey` includes:
  - game_id
  - chart_id
  - difficulty (if applicable)
  - adapter version
  - pipeline version
  - feature flag digest
- [ ] Same inputs → same RunKey

### Validation Signal
- Duplicate ingestion attempts dedupe cleanly
- Retry does not change identity

---

## 5. STOP / DEGRADED Semantics ✅

### Required
- [ ] All STOP decisions include a stable `reason_code`
- [ ] DEGRADED runs are explicitly marked
- [ ] DEGRADED never silently behaves like ALLOW
- [ ] Reason codes are drawn from `reason_codes.py` only

### Validation Signal
- A human can answer:  
  **“Why didn’t tips generate?”**  
  by reading a single field.

---

## 6. Multi‑Game Safety ✅ (≤25 Games)

### Required
- [ ] No `if game_id == ...` logic in orchestration
- [ ] Per‑game differences expressed via configuration
- [ ] Failures in one game do not impact others
- [ ] Circuit breakers (if enabled) are scoped per game

### Validation Signal
- Adding a new game does not require touching:
  - existing game adapters
  - orchestration core logic

---

## 7. RunPlan Simplicity ✅

### Required
- [ ] RunPlan is declarative, not inferred
- [ ] Stage order is explicit and deterministic
- [ ] No hidden dynamic DAG logic
- [ ] Capability matrix is informational unless gated

### Validation Signal
- A developer can list all stages for a run by inspection

---

## 8. Stabilization Guarantees ✅

### Required (Recommended Steady‑State)
- [ ] Exceptions are caught and converted to STOP
- [ ] Retry is bounded and explicit
- [ ] Circuit breaker state is isolated
- [ ] No crash propagates past orchestrator boundary

### Validation Signal
- Worst‑case behavior = clean STOP with reason code

---

## 9. Observability & Reporting ✅

### Required
- [ ] Structured `RunReport` is emitted when enabled
- [ ] CLI JSON surfaces STOP / DEGRADED fields
- [ ] Schema validation exists (CI or runtime)
- [ ] Reporting logic does not affect execution

### Validation Signal
- Reports can be validated without running gameplay logic

---

## 10. Schema & Contract Enforcement ✅

### Required
- [ ] JSON Schemas exist for:
  - RunReport
  - CLI JSON projection
- [ ] Schema validator is non‑blocking
- [ ] Fallback structural checks exist if jsonschema is unavailable

### Validation Signal
- CI can fail fast on malformed orchestration output

---

## 11. Localization & Phase 4.5 Readiness ✅

### Required Before Phase 4.5
- [ ] Orchestration is locale‑agnostic
- [ ] Templates and narratives are wired, not embedded
- [ ] Localization affects presentation, not semantics
- [ ] Locale routing is treated as wiring

### Validation Signal
- Adding a locale does not modify Phase 1–4 logic

---

## 12. Production Readiness (Phase 5 Gate) ✅

### Required Before Phase 5
- [ ] All above sections are satisfied
- [ ] RunReport coverage is complete
- [ ] STOP reasons are stable and documented
- [ ] Orchestration failures are explainable to non‑engineers

---

## 13. Explicit Anti‑Patterns 🚫

The following are **never allowed**:

- ❌ Semantic fixes inside orchestration
- ❌ Game‑specific branching in orchestrator core
- ❌ Silent retries or silent fallback
- ❌ Mutating canonical payload meaning
- ❌ Fixing “just one game” by breaking the rule

---

## 14. Final Steady‑State Declaration

If **all items above are satisfied**, the Orchestrator Extension is considered:

✅ Stable  
✅ Correct  
✅ Scalable within realistic bounds  
✅ Ready for long‑term maintenance  

---

**This checklist is the operational contract of the Orchestrator Extension.**