## ORCHESTRATOR_EXTENSION_ARCHITECTURE.md

**Title:** Orchestrator Extension — Control‑Plane Architecture  
**Scope:** Phase 3 (Unified Ingestion Manager) and downstream phases  
**Status:** Design‑Locked (Steady‑State)  
**Compatibility Rule:**  
**Do not modify completed semantic phases. Wiring between phases remains flexible.**

---

### 1. Purpose

This document defines the **architectural role** of the Orchestrator Extension.

It explains:
- why completed semantic phases are frozen,
- why orchestration remains evolvable,
- how control‑plane concerns are absorbed safely,
- and how the system scales to a realistic ceiling of **~10–25 rhythm game models**.

This document is **descriptive**, not aspirational.
It reflects the **current, implemented steady‑state**.

---

### 2. Architectural Principle (The One‑Line Rule)

> **Do not modify completed phases, but wiring between phases remains flexible.**

#### Interpretation

- **Completed phases are semantic**
  - they define meaning, inference, and user‑visible behavior.
- **Wiring is control‑plane**
  - it defines ordering, gating, retries, fallbacks, observability, and safety.

The Orchestrator Extension exists **solely** to evolve the control‑plane
without contaminating semantics.

---

### 3. Phase Classification

#### 3.1 Semantic Phases (Frozen Once Correct)

These phases MUST NOT be modified after validation:

| Phase | Responsibility |
|-----|---------------|
| Phase 1 | Core detection, tagging, and structure inference |
| Phase 2 | Severity, selection, guidance, narrative |
| Phase 4 | Personalization logic and safe adjustment |

**Rationale:**
- Determinism
- Reproducibility
- Trust and regression safety
- Model training stability

Any change here risks **semantic drift**.

---

#### 3.2 Control‑Plane Phases (Evolvable)

| Phase | Responsibility |
|-----|---------------|
| Phase 3 | Orchestration, ingestion, validation, routing |
| Phase 4.5 | Localization orchestration |
| Phase 5 | Productionization, observability, experimentation |
| Phase 6 | Platform hardening and reliability |
| Phase 7 | Expansion (recommendation orchestration) |

These phases may evolve **indefinitely**, provided they do not alter semantic outputs.

---

### 4. Orchestrator Extension Role

The Orchestrator Extension is the **control‑plane backbone** of the system.

It is responsible for:

#### 4.1 Execution Coordination
- Run modes (`ingest`, `tips`, `personalized`, `full`)
- Stage ordering
- Declarative run plans

#### 4.2 Gating & Decision Semantics
- Unified `ALLOW / STOP / DEGRADED`
- Stable reason codes
- Explicit failure causes (no silent fallback)

#### 4.3 Stabilization
- Deterministic RunKey
- Bounded retries
- Circuit breakers / isolation
- Exception → STOP conversion

#### 4.4 Observability
- Structured RunReport
- CLI JSON surfacing
- Schema‑validated outputs
- QA / CI enforcement hooks

#### 4.5 Multi‑Game Safety
- Per‑game defaults via configuration
- Capability introspection
- Failure isolation
- No `if game_id == ...` branching

---

### 5. What the Extension MUST NOT Do

The extension MUST NOT:
- implement gameplay logic,
- alter Phase 1–2 detection, scoring, or narrative,
- alter Phase 4 personalization decisions,
- mutate canonical payload semantics,
- introduce heuristics that change tip meaning.

Violating these rules collapses the phase boundary.

---

### 6. Why Wiring Is Allowed to Be Flexible

#### 6.1 Control‑Plane Complexity Is Additive

As the system grows:
- more games,
- more locales,
- more personalization modes,
- more production constraints,

complexity accumulates **around** the pipeline, not inside it.

Wiring flexibility absorbs this complexity safely.

#### 6.2 Semantic Correctness Is Cumulative

Once semantic behavior is correct:
- it should remain stable,
- all future work should wrap, not modify it.

This preserves:
- user trust,
- reproducibility,
- debuggability,
- training consistency.

---

### 7. Scale Assumptions (Realistic)

This architecture assumes:
- **≤25 meaningful rhythm game models**
- Games are high‑value, not long‑tail
- Coordination complexity dominates algorithmic complexity

The Orchestrator Extension is explicitly sized for this reality.

---

### 8. Steady‑State Feature Posture

#### 8.1 Always‑On (Recommended)
- Reasoned STOP / DEGRADED gates
- Structured RunReport
- Schema validation (at least in CI)
- Deterministic RunKey
- Per‑game defaults

#### 8.2 Optional / Environment‑Dependent
- Retries
- Circuit breakers
- Metrics emission
- Strict preflight enforcement

#### 8.3 Never Allowed
- Semantic logic in orchestration
- Game‑specific branching
- Silent fallbacks

---

### 9. Relationship to Downstream Phases

| Phase | Extension Responsibility |
|-----|--------------------------|
| Phase 4.5 | Locale routing and QA gating |
| Phase 5 | Observability and reliability wiring |
| Phase 6 | Platform safety and SLO wiring |
| Phase 7 | Recommendation orchestration only |

The extension enables these phases **without reopening completed work**.

---

### 10. Summary

The Orchestrator Extension formalizes a core truth:

> **Semantic correctness must be preserved.  
> Operational complexity must be absorbed elsewhere.**

This document defines the **steady‑state architecture**.