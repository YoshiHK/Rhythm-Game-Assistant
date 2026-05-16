# Phase 4.5 Invariants — Localization Guarantees

**Status:** Locked ✅  
**Scope:** Phase 4.5 only  
**Enforcement:** CI + Architecture

---

# 1. Purpose

This document defines **non-negotiable invariants**  
for Phase 4.5 Localization.

These invariants:

- ✅ MUST always hold
- ✅ are enforced by CI
- ❌ MUST NOT be bypassed

---

# 2. Core Invariants

---

## 🔒 2.1 Semantic Preservation

Localization MUST NOT alter meaning.

- no new advice
- no loss of meaning
- no reinterpretation

---

## 🔒 2.2 Template Parity

Every locale MUST:

- contain all template_ids
- match structure exactly
- preserve all variants

---

## 🔒 2.3 Placeholder Integrity

Placeholders MUST:

- exist in all locales
- match exactly (no additions/removals)
- maintain ordering

---

## 🔒 2.4 Taxonomy Alignment

- every template_id MUST exist in taxonomy
- template_id MUST exist in exactly ONE taxonomy
- taxonomy MUST match template_registry

---

## 🔒 2.5 Locale Determinism

Locale resolution MUST:

- be deterministic
- use alias mapping consistently
- produce valid fallback chains

---

## 🔒 2.6 Debug Consistency

> debug.json MUST be identical across ALL locales

---

## 🔒 2.7 CI Enforcement

All localization MUST pass:

- taxonomy_validator
- pack_integrity
- template_parity
- placeholder_integrity
- debug_consistency
- token / word constraints

---

## 🔒 2.8 No Hidden Dependencies

- no _shared runtime data
- no implicit fallbacks
- no cross-locale dependency

---

# 3. Forbidden Behavior

Phase 4.5 MUST NOT:

- ❌ introduce runtime logic
- ❌ modify template selection
- ❌ perform AI generation
- ❌ mutate upstream outputs

---

# 4. Failure Rules

If ANY invariant is violated:

- ❌ CI MUST fail
- ❌ code MUST NOT ship
- ✅ fix MUST occur in localization layer

---

# 5. Relationship to Architecture

Architecture → defines structure
Spec         → defines behavior
Invariants   → enforce correctness
CI           → enforces invariants

---

# ✅ Final Statement

> 🔒 These invariants define the **safety boundary** of Phase 4.5.

Breaking them results in:

- invalid system behavior
- semantic corruption
- non-deterministic output

---

# ✅ Summary

Phase 4.5 invariants guarantee:

- semantic safety
- deterministic behavior
- cross-locale consistency
- long-term stability