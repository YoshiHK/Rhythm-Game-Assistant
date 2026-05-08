# Phase 6 — Lifecycle Management Layer

The Lifecycle Management layer governs **model and deployment state**
as part of Phase 6 (Platform Hardening and Scale).

This layer ensures that:
- only valid model versions are executed,
- deployments respect environment and stage constraints,
- rollback and promotion boundaries are enforced.

This layer MUST NOT:
- perform model training,
- run inference,
- modify gameplay semantics,
- or alter recommendation logic.

Lifecycle Management exists to answer:
> “Given the current model and deployment state, is this execution allowed?”

---

## Design Principles

### 1. Non‑Semantic by Contract
Lifecycle logic does not understand:
- chart data,
- player behavior,
- tips or severity,
- personalization outcomes.

It only understands **version, stage, and deployment state**.

### 2. Trigger‑Aware, Not Trigger‑Driven
Execution intent (scheduled / manual / external) is normalized upstream
by the Trigger Router.

Trigger type may influence:
- whether strict version constraints apply,
- whether rollback paths are allowed.

Lifecycle Management does NOT schedule execution.

---

## Components

### version_policy.py
**Policy / Guard**

- Defines which model and API versions are permitted.
- Blocks deprecated or incompatible versions.
- Provides declarative version constraints only.

### model_lifecycle_router.py
**Routing Gate**

- Evaluates model lifecycle state (e.g. active, pinned, deprecated).
- Determines whether execution may proceed with the requested model.
- Does not select models or retrain.

### deployment_router.py
**Routing Gate**

- Evaluates deployment context (environment, region, stage).
- Ensures execution respects rollout and rollback boundaries.
- Does not provision or migrate infrastructure.

---

## Execution Model

1. Execution intent is normalized by Trigger Router.
2. Version Policy evaluates version validity.
3. Lifecycle routers evaluate model and deployment state.
4. Execution is allowed or blocked.

At no point does this layer:
- trigger training,
- promote models,
- or override Phase 5 contracts.

---

## Invariants

- Manual execution is explicit and auditable.
- Deprecated models are never silently executed.
- Rollback paths are reversible and logged.
- Phase 1–5 semantics remain immutable.

---

Lifecycle Management protects system stability,
not product intelligence.
