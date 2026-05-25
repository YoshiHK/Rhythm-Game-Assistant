# Platform Overview

**Status:** Design‑Locked ✅  
**Perspective:** Platform / Operations (Phase 6)  
**Scope:** End‑to‑End Runtime System (Phase 1–7)

---

## 1. Purpose

This document provides a **platform‑level view** of the system.

It answers:
- how the system is invoked at runtime,
- where operational responsibility lives,
- how failures are isolated,
- and how new capabilities (e.g. Phase 7) are added safely.

This document does **not** describe gameplay logic or algorithm internals.

---

## 2. Platform Boundary (Phase 6)

> ✅ **Phase 6 is the ONLY runtime gatekeeper.**

All external requests—UI, SDK, partner, or automation—enter through Phase 6.

Phase 6 owns:
- API surface
- authentication and authorization
- request normalization
- rate limiting
- lifecycle control
- failure isolation
- platform‑level observability

No other phase may be invoked directly at runtime.

### Platform Capabilities (Explicit)

The platform provides the following system-level capabilities:

#### Recommendation Layer
- Song-level recommendations via deterministic pipelines
- Game-level discovery via Phase 7 (optional, injected)
- Structured tips generation with explanation support

#### Intelligence Layer
- Multi-vector personalization (Phase 4)
- Multi-vector localization (Phase 4.5)
- Offline learning loop (Phase 5, non-runtime)

#### Platform Layer
- Multi-game support via centralized registry (games.json)
- Capability gating per game (enablement & learning readiness)
- Orchestrated execution via OrchestratorBridge
- Deterministic and reproducible outputs

#### Operational Layer
- Single-entry runtime surface (Phase 6)
- Secure request boundary with traceability
- CI-governed structure and regression protection
- Structured observability signals (CI SUMMARY)

These capabilities span multiple phases and are enforced at the platform level.


---

## 3. Routing Truth (Authoritative)

> ✅ **The authoritative routing topology is defined in:**  
> **`Repo_Routing_Skeleton.txt`**

This file defines:
- legal runtime entrypoints,
- cross‑phase invocation rules,
- forbidden routing paths,
- current Phase 1–7 wiring.

If code, diagrams, or documentation disagree,
**the routing skeleton is authoritative**.

---

## 4. Runtime Invocation Model

From a platform perspective, all runtime flows follow this pattern:

Client / UI / Partner
→ Phase 6 API (auth, guards, normalization)
→ Routed Phase (3 / 4 / 7)
→ Response


Phase 6 enforces:
- authentication and authorization
- abuse prevention
- partner boundaries
- compliance constraints

Lower phases must assume:
- requests are already authenticated
- security checks are complete

---

## 12. Evolution Rules (Platform)

The platform may evolve by:
- adding new routing paths (via skeleton update),
- enabling new control‑plane features,
- introducing new expansion phases.

The platform MUST NOT evolve by:
- modifying completed semantic phases,
- introducing runtime version switching,
- bypassing Phase 6.

---

## 13. Summary

From a platform perspective:

- ✅ Phase 6 is the single runtime gate
- ✅ Routing truth is centralized
- ✅ Semantic meaning is protected
- ✅ Expansion is safe and reversible
- ✅ The system is operable at scale

For routing and invocation questions,  
**always consult `Repo_Routing_Skeleton.txt` first.**
