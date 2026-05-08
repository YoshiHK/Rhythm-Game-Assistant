# Phase 1 Interfaces – README

## Purpose

This directory documents the **implicit data contracts** used by Phase 1
(Foundation) of the Tip Generation System.

These interfaces describe the *effective shapes and semantics* of data as they
exist today in Phase 1, without enforcing schemas or modifying runtime behavior.

> **Important**
> - Phase 1 is considered **Completed and Locked**
> - Files in this directory are **documentation only**
> - No enforcement, validation, or runtime dependency is introduced here

---

## What “Interfaces” Mean in Phase 1

Unlike later phases (Phase 2+), Phase 1 interfaces are:

- **Implicit** – inferred from existing pipeline behavior
- **Documented** – written down to prevent accidental drift
- **Non‑enforced** – not validated at runtime

Their role is to act as a **contract of understanding**, not a contract of control.

---

## Interface Files

The following interfaces are documented:

### 1. `chart_input.interface.md`
Defines the canonical ingestion unit for Phase 1.

- Represents a single chart entering the pipeline
- Treated as immutable input
- Minimal assumptions about payload structure

---

### 2. `detected_tags.interface.md`
Defines the pattern‑signal tags produced during chart analysis.

- Tags are the primary signal for downstream inference
- Order‑independent, taxonomy‑dependent
- Not normalized or validated at Phase 1

---

### 3. `element_candidate.interface.md`
Defines element candidates inferred from detected tags.

- Pre‑scoring, pre‑selection
- No severity, no ranking guarantees
- Represents *potential* gameplay elements only

---

### 4. `analysed_element.interface.md`
Defines the analysed gameplay element used for tips generation.

- Includes severity, score, and coverage
- Used by guidance and narrative modules
- No personalization applied at this phase

---

### 5. `tips_output.interface.md`
Defines the final tips text output.

- Presentation‑layer artifact
- Safe for direct rendering
- Localization and personalization are out of scope

---

## Guarantees

The following guarantees apply to all Phase 1 interfaces:

- Phase 1 **will not be retrofitted** to conform to these files
- Phase 1 **output shapes are considered stable**
- Phase 2+ MUST adapt to Phase 1 outputs, not the reverse

---

## Relationship to Later Phases

- **Phase 2** treats these interfaces as *inputs* and applies explicit schemas
- **Phase 3** may validate or adapt these interfaces via adapters
- **Phase 4+** must not assume stronger guarantees than documented here

These interfaces form the **only supported understanding boundary**
between Phase 1 and the rest of the system.

---

## Change Policy

- ✅ Clarifications and wording improvements are allowed
- ❌ Adding new required fields is not allowed
- ❌ Changing semantics is not allowed
- ❌ Introducing enforcement is not allowed

Any evolution of Phase 1 behavior must occur via:
- Phase 1.1 (parallel foundation), or
- Phase 2+ enhancement layers

---

## Summary

This directory exists to:

- Make Phase 1 *understandable*
- Make Phase 1 *safe to depend on*
- Make future refactors *non‑destructive*

It is intentionally conservative.