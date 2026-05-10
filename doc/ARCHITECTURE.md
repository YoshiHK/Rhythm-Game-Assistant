# System Architecture

**Status:** Design‑Locked ✅  
**Scope:** Phase 1–7 (End‑to‑End)  
**Compatibility Rule:**  
> **Completed semantic phases MUST NOT be modified.  
> Wiring between phases MAY evolve freely.**

---

## 1. Architectural Intent

This system is designed as a **multi‑phase, deterministic recommendation platform**
for rhythm game players.

Its core guarantees are:

- semantic correctness,
- deterministic outputs,
- explainability,
- and long‑term evolvability without regression.

---

## 2. Phase Model (High‑Level)

| Phase | Role | Mutability |
|------|-----|------------|
| Phase 1 | Foundation (detection & structure) | Frozen |
| Phase 2 | Enhancement (severity, narrative) | Frozen |
| Phase 3 | Unified Ingestion Manager (orchestration) | Evolvable |
| Phase 4 | Personalization | Frozen |
| Phase 4.5 | Localization | Evolvable |
| Phase 5 | Productionization & learning | Evolvable |
| Phase 6 | Platform hardening (runtime gate) | Evolvable |
| Phase 7 | Games recommendations (discovery) | Evolvable |

**Rule:**  
Semantic phases are frozen once correct.  
Control‑plane phases absorb operational complexity.

---

## 3. Routing Truth (Authoritative)

> ✅ **The authoritative source of routing topology is:**  
> **`Repo_Routing_Skeleton.txt`**

This file defines:

- the only legal runtime entrypoints,
- which phase may call which,
- which flows are forbidden,
- and how Phase 1–7 are wired **today**.

### Why This Matters

- Architecture diagrams are descriptive, not normative.
- Code comments drift.
- The routing skeleton is the **single source of truth**.

If a routing path exists in code but not in `Repo_Routing_Skeleton.txt`,
**the skeleton wins**.

---

## 4. Runtime Entry Rule (Non‑Negotiable)

- **Phase 6 is the ONLY runtime gatekeeper.**
- No UI / SDK / client may invoke any other phase directly.
- All runtime calls pass through Phase 6 API wiring.

This rule is enforced by:
- API surface design,
- OrchestratorBridge boundaries,
- CI and code review discipline.

---

## 5. Control‑Plane vs Semantic Plane

### Semantic Plane (Frozen)
- Phase 1: detection, tagging, structure
- Phase 2: severity, selection, narrative
- Phase 4: personalization decisions

These define **meaning** and must not change.

### Control‑Plane (Evolvable)
- Phase 3 orchestration
- Phase 4.5 localization
- Phase 5 learning
- Phase 6 platform hardening
- Phase 7 discovery

These define **ordering, safety, routing, and scale**.

---

## 6. Orchestrator Extension

The Orchestrator Extension is part of **Phase 3 control‑plane**.

It provides:
- a stable execution boundary (`OrchestratorBridge`),
- deterministic RunKey,
- STOP / DEGRADED semantics,
- retries and circuit breakers (opt‑in),
- structured observability.

It MUST NOT:
- implement gameplay logic,
- modify Phase 1–2 or Phase 4 semantics.

---

## 7. Phase 7 in Context

Phase 7 adds **game‑level discovery**, not gameplay advice.

Properties:
- runtime entry via Phase 6 only,
- non‑blocking and reversible,
- emits feedback to Phase 5,
- never mutates upstream phases.

---

## 8. Change Discipline

- No runtime versioning.
- No parallel routing truths.
- Deprecated routing paths are removed, not archived.
- Structural routing changes require architectural review,
  **but are not runtime breaking by default**.

---

## 9. Summary

- ✅ Semantic meaning is protected.
- ✅ Operational complexity is isolated.
- ✅ Routing truth is centralized.
- ✅ The system can evolve without entropy.

**For routing questions, always consult `Repo_Routing_Skeleton.txt`.**