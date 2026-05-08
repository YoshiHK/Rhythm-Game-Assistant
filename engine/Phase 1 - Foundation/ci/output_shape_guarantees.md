# Phase 1 CI – Output Shape Guarantees

## Purpose

This document defines the **output shape guarantees**
for Phase 1 (Foundation).

It ensures that downstream phases can safely consume
Phase 1 outputs without relying on implementation details.

---

## Guaranteed Outputs (Per Chart)

Phase 1 guarantees the presence of:

- `tips_text`
  - paragraph_1 (string)
  - paragraph_2 (string)

- `chart_summary`
  - conforms to canonical per‑chart summary schema

---

## Guaranteed Outputs (Per Batch)

For batch execution, Phase 1 guarantees:

- batch summary block
- aggregation consistent with batch summary schema

---

## Stability Guarantees

Phase 1 guarantees that:

- Field names are stable
- Field types are stable
- Required fields are always present when tips are produced
- Optional fields are additive only

---

## What Is NOT Guaranteed

Phase 1 does NOT guarantee:

- Exact wording stability across spec versions
- Backward compatibility with undocumented fields
- Presence of Phase 2+ enrichment fields

Downstream phases must not depend on:
- internal intermediate structures
- non‑documented keys
- incidental ordering of fields

---

## Relationship to Schemas

- Schemas define **validation contracts**
- This document defines **runtime guarantees**

Schemas may be stricter than runtime,
but runtime must not violate schemas.

---

## Change Policy

✅ Allowed:
- Additive fields in later phases
- New output contracts in Phase 2+

❌ Not Allowed:
- Removing existing fields
- Changing field meanings
- Re‑typing existing fields

---

## Summary

Output shape stability is the **contract boundary**
between Phase 1 and all later phases.

Breaking this contract breaks the system.
