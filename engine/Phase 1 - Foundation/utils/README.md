# Phase 1 Utils Layer – README

## Purpose

This directory contains **shared utility helpers**
used across multiple Phase 1 Foundation layers.

Utilities in this layer exist to:
- reduce duplication
- simplify wiring
- provide common helper functions

They must **never** implement business logic,
decision rules, or pipeline orchestration.

---

## Contents

### `utils.py`
General-purpose helper functions.

Characteristics:
- stateless
- deterministic
- side‑effect free

Typical responsibilities:
- simple data transformations
- small convenience helpers
- common formatting or lookup logic

---

### `shared_helpers.md`
Documentation for shared helper concepts used in Phase 1.

This file exists to:
- explain helper intent
- document assumptions
- avoid misinterpretation by later phases

---

## Guarantees

- Utilities do not affect pipeline decisions
- Utilities do not alter semantic meaning
- Utilities are safe to call from any Phase 1 layer

---

## Relationship to Later Phases

- **Phase 2+** may re‑use concepts but must not rely on Phase 1 utils
- **Phase 3** may provide its own utility layer
- **Phase 4+** must not import Phase 1 utils directly

Phase 1 utils exist solely to support the Foundation runtime.

---

## Change Policy

✅ Allowed:
- Documentation updates
- Minor refactoring with no behavior change
- Packaging metadata (e.g. `__init__.py`)

❌ Not Allowed:
- Adding decision logic
- Adding scoring logic
- Adding orchestration logic
- Introducing new dependencies

Any meaningful evolution must occur via:
- Phase 1.1 (parallel foundation), or
- Phase 2+ enhancement layers

---

## Summary

This layer provides **infrastructure support only**.

It exists to make Phase 1 readable and maintainable,
not to drive system behavior.