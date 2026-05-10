# System Specification (API & Integration)

**Status:** Design‑Locked ✅  
**Perspective:** External API & Platform (Phase 6)  
**Scope:** Runtime Integration (Phase 1–7)

---

## 1. Purpose

This document defines the **external system contract**:
- what clients may call,
- what responses they may receive,
- and what guarantees the platform provides.

It does **not** define internal algorithms or phase implementations.

---

## 2. Non‑Negotiable System Rules

- ✅ Completed semantic phases (Phase 1, 2, 4) MUST NOT be modified.
- ✅ Phase 6 is the **only runtime entrypoint**.
- ✅ Routing topology is defined in `Repo_Routing_Skeleton.txt`.
- ✅ STOP / DEGRADED are valid outcomes.
- ✅ No runtime version switching.

If any integration violates these rules, it is **architecturally invalid**.

---

## 3. API Entry Point (Phase 6)

### 3.1 Unified Recommendation Endpoint

All runtime requests enter via **Phase 6 API**.

POST /api/v1/recommend

Phase 6 is responsible for:
- authentication & authorization,
- request normalization,
- routing to internal phases,
- failure isolation,
- observability emission.

No client may call internal phases directly.

---

### 3.2 Request Shape (Logical)

The API accepts a **unified recommendation request**.

Conceptual fields include:

- `game_id` (string, required)
- `mode` (string)
  - `"songs"` — song‑level tips
  - `"games"` — game discovery (Phase 7)
- `locale` (string)
- `max_items` (integer)
- optional player context:
  - user id
  - player signals
  - preferences
  - evidence
  - client metadata

> The exact wire format is defined by the API implementation.  
> This spec defines **behavioral guarantees**, not JSON minutiae.

---

## 4. Runtime Routing Behavior

### 4.1 Songs Recommendation Flow

When `mode = "songs"`:

Client
→ Phase 6 API
→ Phase 3 Orchestrator
→ Phase 1 → Phase 2
→ Phase 4 Personalization
→ Phase 4.5 Localization
→ Response

Properties:
- deterministic
- explainable
- semantic meaning preserved
- localization affects presentation only

---

### 4.2 Games Recommendation Flow (Phase 7)

When `mode = "games"`:

Client
→ Phase 6 API
→ Phase 7 Router
→ Matching & Ranking
→ Explanation
→ Feedback / Observability (async)
→ Response

Properties:
- discovery only
- non‑blocking
- reversible
- does not alter song‑level recommendations

---

## 5. Response Semantics

### 5.1 Success Responses

A successful response may include:
- one or more recommendation items,
- explanations or rationale,
- provenance and diagnostics metadata.

---

### 5.2 STOP / DEGRADED Responses

STOP or DEGRADED responses are **valid**.

They must be:
- explicit,
- explainable,
- machine‑readable.

A client must be able to determine:
- **what stopped**, and
- **why**.

Worst‑case behavior:
> Clean STOP with reason code and observability signal.

---

## 6. Failure Isolation Guarantees

The platform guarantees:

- failures are isolated to a phase,
- no upstream phase is mutated,
- no crash propagates to the client,
- retries and fallbacks are explicit (never silent).

Phase 6 never retries blindly.
Control‑plane logic governs recovery.

---

## 7. Security & Trust Model

- All requests are authenticated at Phase 6.
- Lower phases assume requests are already authorized.
- Phase 6 enforces:
  - abuse prevention,
  - partner boundaries,
  - compliance constraints.

Security logic must not leak into semantic phases.

---

## 8. Observability & Feedback

The platform emits:
- structured run reports (when enabled),
- STOP / DEGRADED reason codes,
- metrics and diagnostics,
- feedback signals for offline learning (Phase 5).

Observability:
- is additive,
- must not affect execution semantics,
- must not block responses.

---

## 9. Relationship to Learning (Phase 5)

Phase 5 operates **outside the runtime path**.

- No online learning.
- No runtime model updates.
- Feedback flows asynchronously.
- Phase 6 never waits on Phase 5.

---

## 10. Versioning & Evolution Policy

- No runtime API version branching.
- No semantic version negotiation.
- Evolution is **additive and gated**.
- Routing changes are reflected by updating:
  - `Repo_Routing_Skeleton.txt`
  - relevant documentation.

---

## 11. What This Spec Does NOT Cover

This spec intentionally excludes:
- Phase 1–2 algorithms,
- personalization model internals,
- learning pipelines,
- UI rendering details.

Those belong to phase‑specific documentation.

---

## 12. Summary

This API spec guarantees:

- ✅ a single runtime entrypoint,
- ✅ stable and explainable behavior,
- ✅ strict phase boundaries,
- ✅ safe expansion via Phase 7,
- ✅ long‑term maintainability.

For routing behavior,  
**`Repo_Routing_Skeleton.txt` is authoritative.**