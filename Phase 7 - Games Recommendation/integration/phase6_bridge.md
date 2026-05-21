# Phase 6 ↔ Phase 7 Bridge

This document defines how **Phase 6 (Platform Hardening)** invokes
**Phase 7 (Games Recommendations)**.

---

## Invocation Rule (Hard)

> **Phase 7 MUST be invoked only via Phase 6.**

Direct invocation from:
- UI clients
- SDKs
- Partner integrations

is **explicitly forbidden**.

---

## Invocation Flow

Client / UI / Partner
        │
        ▼
Phase 6 API / Router
        │
        │  (auth, guards, rate limits, observability)
        ▼
Phase 7 Router
        │
        ▼
Phase 7 Ranking + Explanation

---

## Invocation Timing

Phase 6 may invoke Phase 7:

synchronously (e.g. on recommendation request),
asynchronously (e.g. on profile update),
or lazily (e.g. cached discovery refresh).

Phase 7 MUST NOT assume any specific timing model.

---

## Failure Semantics

If Phase 7:

errors,
times out,
or is disabled,

Phase 6 MUST:

isolate the failure,
return degraded or empty discovery results,
continue serving all upstream functionality.

---

## Data Contract

Phase 6 provides:

player identifier
locale
invocation context
optional player signals

Phase 7 returns:

game recommendations
explanations
diagnostics metadata

Phase 6 remains responsible for:

response shaping
logging
client-facing guarantees
