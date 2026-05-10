# Phase 4.5 Architecture — Localization

**Status:** Design‑Locked ✅  
**Phase Type:** Presentation / Wiring  
**Runtime Ownership:** Phase 6 (invocation only)

---

## 1. Purpose

Phase 4.5 provides **localization and internationalization wiring**
for personalized gameplay tips.

It exists to:
- adapt presentation to locale,
- preserve semantic meaning,
- prevent runtime breakage caused by translation drift.

Phase 4.5 does **not** introduce new gameplay logic.

---

## 2. Architectural Position

Phase 4 (Personalization Output)
↓
Phase 4.5 (Localization Wiring)
↓
Localized Presentation Payload

Phase 4.5:
- is invoked **only via Phase 6**,
- never invokes Phase 4 or earlier phases directly,
- never mutates semantic decisions.

---

## 3. Responsibilities

Phase 4.5 owns:

- Locale resolution and fallback
- Narrative v3 template localization
- Variant selection (casual / expert / debug)
- Placeholder preservation
- Presentation‑level constraints (word budgets)
- Localization provenance metadata

---

## 4. Non‑Responsibilities (Hard Boundaries)

Phase 4.5 MUST NOT:

- modify detected elements or scores
- alter severity or guidance meaning
- reorder or filter tips
- perform free‑form translation
- bypass Phase 6 routing
- gate runtime execution

---

## 5. Translation Store Architecture

Localization assets live under a **deterministic folder layout**:

- `translations/_meta/` — locale registry and sources
- `translations/<locale>/templates/` — Narrative v3 templates
- `translations/<locale>/variants/` — word budget definitions
- `translations/<locale>/glossary/` — reference‑only glossary
- `translations/<locale>/locale_meta.json` — locale metadata

All locales must maintain **template parity**.

---

## 6. Locale Normalization

Locale normalization is handled by:

- `locale_normalizer.normalize_locale`
- explicit alias mappings
- deterministic fallback rules

Normalization is wiring‑only and non‑semantic.

---

## 7. CI Governance Layer

Phase 4.5 is protected by a **dedicated CI governance layer**:

- Structural integrity checks
- Template parity enforcement
- Placeholder/token safety
- Narrative word budgets
- Explicit waivers with decay

CI is **non‑runtime** and **non‑blocking**.

---

## 8. Failure Semantics

Phase 4.5 failures result in:

- CI failures (during development), or
- STOP / DEGRADED outcomes via Phase 6 (runtime)

There is no silent fallback.

---

## 9. Summary

Phase 4.5 is a **pure presentation layer**:
- semantics are preserved,
- localization is deterministic,
- failures are explicit,
- governance is enforced by CI.

This phase is **safe, sealed, and extensible**.