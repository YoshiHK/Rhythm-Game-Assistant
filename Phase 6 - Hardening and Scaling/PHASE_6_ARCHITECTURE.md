### PHASE_6_ARCHITECTURE.md

## Phase 6 — Platform Hardening Architecture

**Status:** Draft (Aligned with PHASE_6_SPEC.md)  
**Invariant:** Phase 6 is downstream‑only and non‑semantic.

---

## 1. Architectural Role

Phase 6 acts as the **operational control plane** of the system.

It does not define _what_ recommendations or tips mean.  
It defines **when, where, and under what conditions** execution is allowed.

Phase 6 is the only phase that:
- receives external runtime traffic,
- applies guards and governance,
- coordinates routing across recommendation domains,
- and enforces failure isolation.

All semantic meaning remains owned by completed phases.

---

## 2. High‑Level Placement

[ Phase 1–4.5 (Analysis & Presentation) ]  ← Locked
[ Phase 5 (Learning & Contracts) ]         ← Locked
───────────────────┼──────────────────
▼
[ Phase 6 (Hardening, Routing & Scale) ]
│
│  [ Song Recommendation (Phase 6 domain) ]
│  [ Game Recommendation (Phase 7) ]
│
[ UI / Softr / Partners ]

Song Recommendations operate as a Phase 6 runtime domain
with **offline learning support**.

Feedback emitted by the Song Recommendation domain
is forwarded to Phase 5 for aggregation and training.

Phase 6 never consumes learning outputs directly.

---

## 3. Execution Subsystems

Phase 6 is composed of **explicit, single‑purpose subsystems**.

### 3.1 Router
- Single runtime entrypoint for all requests.
- Normalizes triggers into immutable routing contexts.
- Applies guards and routing policy.
- Dispatches to domain handlers.

### 3.2 Guards
- Enforce safety, reliability, and compliance constraints.
- Produce explicit ALLOW / STOP / DEGRADED decisions.
- Never interpret recommendation semantics.

### 3.3 Lifecycle
- Govern model and configuration rollout.
- Enforce version pinning and rollback safety.
- Prevent partial or mixed deployments.

### 3.4 Observability
- Emit structured health and diagnostic signals.
- Support alerting, SLO tracking, and audits.
- Do not influence execution behavior.

### 3.5 Cost & Capacity
- Enforce resource budgets and quotas.
- Support scaling decisions without semantic impact.

### 3.6 Integration
- Define SDK, partner, and API boundaries.
- Ensure backward compatibility and isolation.

---

## 4. Routing Domains

Phase 6 defines **explicit routing domains** based on request mode.

### 4.1 Song Recommendation Routing
- mode = `"songs"`
- Routed to the Phase 6 Song Recommendation domain.
- Deterministic selection and response shaping.
- Forward‑only feedback emission.

### 4.2 Game Recommendation Routing
- mode = `"games"`
- Routed to the Phase 7 Game Recommendation domain.
- Deterministic ranking and explanation.
- Feedback emitted directly by Phase 7.

Routing decisions:
- are non‑semantic,
- are policy‑driven,
- do not branch on learning flags,
- and do not consume feedback outcomes.

---

## 5. Song Recommendation Architecture

Song Recommendations operate as a **Phase 6 runtime domain**.

### 5.1 Core Characteristics
- Deterministic execution
- No I/O beyond controlled artifacts
- No learning or adaptation at runtime

### 5.2 Key Components
- Request Normalizer
- Game Capability Resolver
- Catalog Loader (read‑only)
- Deterministic Catalog Selector
- Response Shaper
- Forward‑Only Feedback Layer

This domain emits exposure metadata and feedback
to support **offline learning in Phase 5**.

---

## 6. Learning Loop Integration (Offline Only)

Phase 6 is **learning‑aware but not learning‑capable**.

Song Recommendation learning spans phases as follows:

### 6.1 Phase 6 (Runtime)
- Emits exposure metadata (`set_id`, `rank`, diagnostics).
- Emits forward‑only feedback events.
- Does not read or apply learning outcomes.

### 6.2 Phase 5 (Offline)
- Aggregates feedback and diagnostics.
- Learns selection heuristics (e.g. window widening).
- Produces updated static parameters.

### 6.3 Deployment
- Introduces learned changes via versioned rollout.
- Guarantees reversibility and auditability.

At no point does Phase 6:
- perform training,
- adjust selection logic dynamically,
- or branch on learning flags.

---

## 7. Failure Semantics

Phase 6 failures are **isolated and explicit**.

On failure:
- execution MUST STOP or enter DEGRADED mode,
- the reason MUST be recorded,
- no partial semantic execution is allowed.

Failures in:
- Song Recommendation
- Game Recommendation
- Feedback emission

must never affect:
- tips generation,
- personalization,
- or upstream pipelines.

---

## 8. Architecture Closure

Phase 6 establishes a **stable, enforceable runtime boundary**.

It guarantees:
- semantic immutability,
- deterministic routing,
- offline‑only learning,
- and safe extensibility.

Once validated, Phase 6 becomes:
- the sole runtime gatekeeper,
- the foundation for Phase 7 expansion,
- and a permanent boundary between execution and learning.

---

**End of PHASE_6_ARCHITECTURE.md**