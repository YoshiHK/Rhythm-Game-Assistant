# Phase 4.5 Specification — Localization

**Status:** Design‑Locked ✅  
**Scope:** Localization Contracts & Invariants

---

## 1. Contract Overview

Phase 4.5 applies localization to personalized outputs
without changing semantic meaning.

It is governed by **structural contracts**, not heuristics.

---

## 2. Input Contract

Phase 4.5 accepts:

- Personalized payload from Phase 4
- Locale identifier (string)
- Variant identifier (optional)
- Feature flags (optional)

Inputs are treated as **read‑only**.

---

## 3. Output Contract

Outputs MUST:

- preserve element identity
- preserve ordering semantics
- preserve placeholder bindings
- comply with word budget limits
- include localization metadata

Outputs MUST NOT:
- introduce new elements
- remove required placeholders
- alter semantic meaning

---

## 4. Template Contract (Narrative v3)

All Narrative v3 templates MUST:

- declare `version = "v3"`
- include `strings.default.text`
- preserve placeholder sets across locales
- respect per‑variant word budgets

Template sets MUST be identical across locales.

---

## 5. Placeholder Integrity

For every template:

- declared placeholders and inline placeholders
  MUST match the base locale
- duplication or loss is forbidden

This prevents runtime binding errors.

---

## 6. Word Budget Rules

Each locale defines word/unit budgets per variant.

- Space‑delimited languages → word count
- CJK / no‑space languages → unit count
- Exceeding budget is a CI failure

Budgets are **presentation constraints**, not semantics.

---

## 7. Waivers & Decay

Some token parity violations may be explicitly waived.

Waivers:
- MUST be declared in `token_parity_waivers.json`
- MUST include a reason
- MUST include `review_by` when decay is enabled
- are bounded by global and per‑locale budgets

Expired waivers fail CI.

---

## 8. Observability

Some checks emit a **single‑line CI SUMMARY**.

Properties:
- deterministic
- machine‑consumable
- non‑gating
- non‑runtime

---

## 9. Non‑Goals

Phase 4.5 does NOT specify:
- translation quality metrics
- linguistic style guides
- runtime fallback behavior
- UI rendering rules

---

## 10. Summary

Phase 4.5 is governed by:
- explicit contracts,
- deterministic CI enforcement,
- strict separation from runtime semantics.

Violations are surfaced early and loudly.
