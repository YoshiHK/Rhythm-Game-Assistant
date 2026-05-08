# Phase 1 CI – Determinism Guarantees

## Purpose

This document defines the **determinism guarantees**
required for Phase 1 (Foundation) of the Tip Generation System.

It serves as a **conceptual CI contract**, ensuring that Phase 1
remains reproducible and stable over time.

---

## Determinism Definition

Phase 1 is considered *deterministic* if:

- The same input chart payload
- Using the same authoritative specs and schemas
- Produces the same:
  - detected tags
  - inferred elements
  - selected elements
  - guidance fields
  - narrative text
  - summary blocks

across repeated runs.

---

## Scope

Determinism applies to:

- Visual detection and SectionMetrics
- Tag → element inference
- Severity, score, and coverage computation
- Element selection
- Guidance filling
- Narrative rendering
- Summary generation

---

## Explicit Exclusions

Phase 1 determinism does NOT depend on:

- system time
- randomness
- external network calls
- user profile or personalization
- machine learning models

---

## CI Expectations (Conceptual)

Any CI or QA process validating Phase 1 must ensure:

- No random seeds are introduced
- No non-deterministic ordering is relied upon
- Sorting rules are explicit and stable
- Floating-point calculations are clamped or bounded

---

## Change Policy

✅ Allowed:
- Documentation updates
- Additional determinism checks in later phases

❌ Not Allowed:
- Introducing randomness into Phase 1
- Adding time-dependent behavior
- Conditional logic based on environment state

---

## Summary

Determinism is the **core invariant** of Phase 1.

If determinism is broken, Phase 1 is no longer a valid foundation.