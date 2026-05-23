# Phase 7 — Routing Layer

This directory implements the **single runtime entrypoint**
for **Phase 7 – Games Recommendations**.

Routing is a **coordinator**, not a decision engine.

---

## Purpose

The Routing Layer answers one question only:

> **How are Phase 7 components orchestrated safely at runtime?**

It coordinates:
- registry filtering,
- ranking invocation,
- explanation attachment,
- and side-channel emission (feedback, observability),

without owning any of those responsibilities.

---

## Core Responsibilities

✅ The Routing Layer MAY:
- select candidate game IDs via the registry + routing policy
- invoke the ranker (single authoritative implementation)
- invoke the explanation engine (optional, non-blocking)
- return contract-shaped recommendation responses
- emit feedback and observability payloads via injected sinks

✅ All operations MUST be:
- deterministic (given the same inputs),
- non-blocking,
- presentation-safe.

---

## Explicit Prohibitions

The Routing Layer MUST NOT:

- implement ranking logic
- implement learning or experimentation
- import eligibility policies (CI-only governance)
- perform runtime version switching
- mutate upstream artifacts (Phases 1–6)
- assume ownership of transport, retry, or persistence

Violations of these rules are architectural errors.

---

## Runtime Entry Rule (Hard)

> **Phase 7 routing is invoked via Phase 6 only.**

Direct calls from:
- UI clients,
- SDKs,
- batch jobs,
- or partners

are not permitted.

Phase 6 owns:
- authentication,
- authorization,
- rate limiting,
- lifecycle control,
- and failure isolation.

---

## Components

- `router.py`
  - Single Phase 7 runtime coordinator
  - Failure-isolated / non-blocking
  - Uses injected ranker, explainer, and collectors

- `routing_context.py`
  - Presentation-safe context (player_id, locale, top_k, platform)
  - No feature flags or eligibility logic

- `routing_policy.py`
  - Declarative, non-semantic candidate shaping
  - Uses registry metadata only
  - Errors must never block routing

---

## Relationship to Other Layers

- **Registry**
  - Defines which games exist and their status
- **Eligibility**
  - CI-only governance (not imported here)
- **Ranking**
  - Single authoritative scoring implementation
- **Explanation**
  - Bounded, i18n-ready rationale attachment
- **Feedback / Observability**
  - Emitted as side-channels only, never affecting outputs
- **Phase 6**
  - Sole runtime gateway and operational owner

---

## Architectural Invariant

If the entire Routing Layer is removed or disabled:

- Upstream phases must continue to function unchanged.
- Phase 7 produces no output, but does not break the platform.

This layer exists to **coordinate safely**, not to decide outcomes.