# Phase 7 — Utils Layer

This directory contains **pure utility helpers** used by Phase 7.

---

## Purpose

The Utils Layer exists to provide **mechanical helpers** that:

- reduce duplication,
- improve readability,
- and standardize common low-level behavior.

It must never introduce domain logic.

---

## Hard Rules

Utilities in this layer MUST:

- ✅ be pure or near-pure functions
- ✅ have no side effects beyond return values
- ✅ be safe to import from any Phase 7 module
- ✅ not import other Phase 7 layers (routing, ranking, explanation, etc.)

Utilities in this layer MUST NOT:

- ❌ make recommendation decisions
- ❌ interpret scores or rankings
- ❌ enforce eligibility or policy
- ❌ depend on Phase 6 infrastructure
- ❌ close feedback or learning loops

---

## Typical Use Cases

✅ Allowed:
- timestamp generation
- defensive validation
- JSON-safe serialization
- small helpers shared by CI / observability / feedback

🚫 Not allowed:
- fallback logic
- ranking heuristics
- locale resolution (Phase 4.5 owns this)
- feature gating

---

## Design Philosophy

If removing the entire Utils layer changes **what Phase 7 recommends**,
then something is wrong.

Utils exist to support correctness — not to shape behavior.