# Phase 2 Registry – README

## Purpose

This directory contains **declarative, read-only registries**
used by Phase 2 (Enhancement) of the Tip Generation System.

Registries define **what is allowed or referenced** by Phase 2 logic.
They do not define procedural behavior.

---

## Registry Files

### `tips_training_mapping.schema.json`
Schema that defines the **allowed shape** of tips training mappings.
Used by CI to validate mapping artifacts before runtime use.

### `tips_training_mapping.seed.json`
A minimal seed/example mapping used for development,
testing, and CI sanity checks.  
This file is **not authoritative production data**.

### `internal_analysis_schema.json`
Declarative snapshot of analysis-related fields and ranges
referenced by Phase 2 logic.  
Acts as a compatibility bridge with Phase 1 semantics.

### `tips_generation_spec.json`
Declarative specification guiding narrative generation constraints,
such as element limits and word budgets.

---

## Guarantees

- Registries are **read-only at runtime**
- No personalization or player context is stored here
- Changes must be **additive or explicitly versioned**

---

## Change Policy

✅ Allowed:
- Additive fields
- New registry files with explicit versioning

❌ Not Allowed:
- Procedural logic
- Runtime mutation
- Silent breaking changes

---

## Summary

The registry layer provides **stable declarative inputs**
that keep Phase 2 deterministic, auditable, and safe for downstream phases.
