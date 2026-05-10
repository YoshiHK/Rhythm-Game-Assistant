# Phase 7 — Boundary Declarations

This directory defines the **explicit architectural boundaries** of
**Phase 7 – Games Recommendations**.

These documents are **normative**, not descriptive.
Violating any rule defined here is considered an architectural error.

---

## Why This Layer Exists

Phase 7 is intentionally:
- downstream-only,
- additive,
- reversible,
- and non-blocking.

Because Phase 7 sits close to UI and discovery surfaces,
its boundaries must be **structurally enforced**, not implicitly assumed.

This layer exists to make misuse difficult and visible.

---

## Scope of Boundary Definitions

This directory defines:

- ✅ What Phase 7 is allowed to consume
- ❌ What Phase 7 is forbidden from importing or mutating
- ✅ What Phase 7 guarantees to emit

It does **not** define:
- ranking logic,
- learning behavior,
- rollout strategy,
- or platform enforcement.

Those belong to other phases by design.

---

## Relationship to Other Documentation

These boundary rules are derived directly from:

- PHASE_7_SPEC.md
- PHASE_7_ARCHITECTURE.md
- Phase 7 README.md

If any conflict exists, **boundary documents take precedence**.

---

## Enforcement Model

- Some rules are enforced by CI (imports, schema shape).
- Some rules are enforced by code review.
- All rules are enforced by design discipline.

Boundaries are intentionally strict.