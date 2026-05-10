# Orchestrator Extension (Control‑Plane)

**Status:** Design‑Locked ✅  
**Scope:** Phase 3 (Unified Ingestion Manager) control plane  
**Compatibility Rule:**  
> **Do not modify completed semantic phases.  
> Wiring between phases may evolve freely.**

---

## 1. What This Is

The **Orchestrator Extension** is the **control‑plane layer** that wraps the
existing orchestrator without modifying it.

Its purpose is to absorb **operational complexity**—not to add gameplay logic.

It provides:
- a **stable execution boundary**,
- deterministic run identity,
- explicit STOP / DEGRADED semantics,
- retries and isolation,
- structured observability outputs.

If all feature flags are disabled, behavior is a **thin pass‑through**.

---

## 2. What This Is NOT

The Orchestrator Extension is **explicitly NOT**:

- ❌ gameplay logic
- ❌ tip generation logic
- ❌ personalization logic
- ❌ heuristic tuning layer
- ❌ per‑game branching logic

It MUST NOT:
- change Phase 1–2 detection, scoring, or narrative,
- change Phase 4 personalization behavior,
- mutate canonical payload semantics.

Violating these rules collapses the phase boundary.

---

## 3. Architectural Position

```
API / Phase 6
↓
OrchestratorBridge   ← stable control‑plane boundary
↓
[ optional ] OrchestratorStabilizer
↓
core.run(...) / core.ingest(...)
↓
Completed semantic phases (unchanged)
```

Key properties:
- **Single stable entrypoint:** `OrchestratorBridge.run(...)`
- **Boundary contract:** `mode` is accepted as a string
- **No runtime versioning**
- **No Phase 1/2/4 imports**

---

## 4. Core Responsibilities

### 4.1 Execution Coordination
- Run modes: `ingest`, `tips`, `personalized`, `full`
- Declarative stage ordering
- Optional RunPlan assembly (additive)

### 4.2 Gating & Decision Semantics
- Unified decisions: `ALLOW / STOP / DEGRADED`
- Stable, machine‑readable `reason_code`
- No silent fallback paths

### 4.3 Stabilization
- Deterministic RunKey
- Bounded retries (opt‑in)
- Circuit breakers (opt‑in)
- Exception → STOP conversion

### 4.4 Observability
- Structured `RunReport`
- CLI JSON projection
- JSON schema enforcement
- CI / QA validation hooks

### 4.5 Multi‑Game Safety
- Per‑game defaults via configuration
- Capability introspection (informational)
- Failure isolation
- No `if game_id == ...` sprawl

---

## 5. Stable Public Surface

The **only stable public surface** is:

from rhythm_ingestion.orchestrator_ext import (
    OrchestratorBridge,
    wrap_orchestrator,
    OrchestratorExtensionConfig,
    FeatureFlags,
)

Entry Behavior

- wrap_orchestrator(core, config) → OrchestratorBridge
- ✅ All flags OFF → thin pass‑through
- ✅ Any flag ON → stabilizer may apply
- Wrapped core may expose:

  - .run(...) ✅ required
  - .recommend(...) ✅ optional (API usage)

---

## 6. Run Identity & Determinism

Every run computes a deterministic RunKey based on:

- game_id
- chart_id
- difficulty (if present)
- adapter version
- pipeline version
- feature flag digest

Properties:

- same inputs ⇒ same RunKey
- retries do not change identity
- safe for deduplication and idempotency

---

## 7. STOP / DEGRADED Semantics

STOP and DEGRADED are valid outcomes
Any STOP / DEGRADED must include:

- stage
- decision
- reason_code



A human must be able to answer:

“Why didn’t tips generate?”

by reading one field.

---

## 8. Schemas & Contracts

The extension defines control‑plane schemas:

- orchestrator_run_report.schema.json
- orchestrator_cli_result.schema.json

Properties:

- STOP / DEGRADED are legal outputs
- Schemas are additive
- Validation is non‑blocking
- Minimal structural fallback exists if jsonschema is unavailable

---

## 9. Feature Flags

All extension behavior is gated by FeatureFlags.
Rules:

- Defaults preserve legacy behavior
- Flags are orthogonal
- Flag digest contributes to RunKey
- No hidden coupling

Turning all flags OFF must yield behavior identical to pre‑extension orchestration.

---

## 10. Scale Assumptions

This architecture is designed for:

- ~10–25 meaningful rhythm game models
- high‑value games, not long‑tail
- coordination complexity > algorithmic complexity

It is not designed for unbounded horizontal scale—and does not need to be.

---

## 11. Relationship to Other Phases

| Phase | Relationship |
|---|---|
| Phase 1-2 | Semantic core (frozen) |
| Phase 4 | Personalization (frozen) |
| Phase 4.5 | Locale routing via wiring |
| Phase 5 | Observability & reliability |
| Phase 6 | Platform gate & safety |
| Phase 7 | Recommendation orchestration only |

The extension enables evolution without reopening completed work.

---

## 12. Steady‑State Declaration

When the checklist is satisfied:
✅ Semantic phases preserved
✅ Control‑plane isolated
✅ STOP reasons explicit
✅ Deterministic and explainable
✅ Safe for long‑term maintenance

The Orchestrator Extension is considered Design‑Locked.