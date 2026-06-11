# Phase 4.5 Specification — Localization

**Status:** Design‑Locked ✅  
**Scope:** Localization Contracts & Invariants

---

# 1. Contract Overview

Phase 4.5 applies localization to Phase 4 output **without changing meaning**.

It is governed by:

- ✅ structural contracts
- ✅ deterministic behavior
- ✅ strict invariants

---

# 2. Input Contract

Phase 4.5 accepts:

- tips_text (from Phase 4)
- template_id
- variant_id (optional)
- locale hint
- engine_mode (optional)

Inputs are:

- ✅ immutable
- ✅ deterministic
- ❌ never reinterpreted

---

# 3. Output Contract

Outputs MUST:

- ✅ preserve semantic meaning
- ✅ preserve element identity
- ✅ preserve placeholder structure
- ✅ apply locale transformation only
- ✅ include localization metadata

Outputs MUST NOT:

- ❌ modify logic
- ❌ add/remove elements
- ❌ change priority or ordering

---

# 4. Template Contract (Narrative v3)

All templates MUST:

- define `template_id`
- declare `"version": "v3"`
- include `strings.default.text`
- preserve placeholder sets across locales

---

# 5. Taxonomy Contract

- every template_id MUST exist in taxonomy
- template_id MUST belong to exactly one layer
- taxonomy MUST match template_registry

---

# 6. Locale Contract

- all locales MUST be present in locales.json
- alias mapping MUST resolve deterministically
- fallback graph MUST:
  - have no cycles
  - terminate

---

# 7. Placeholder Contract

- placeholders MUST NOT change across locales
- placeholders MUST NOT be added or removed
- placeholder ordering MUST be preserved

---

# 8. Tone Contract

Tone layer:

- ✅ post-processing only
- ✅ uses `{base_text}`
- ❌ must not alter meaning

---

# 9. Debug Contract

- debug.json MUST exist per locale
- debug.json MUST be identical across all locales

---

# 10. CI Contract

All localization assets MUST pass:

- taxonomy_validator
- pack_integrity
- template_parity
- placeholder_integrity
- debug_consistency
- token/word constraints

---

# 11. Determinism Requirements

Phase 4.5 MUST be:

- deterministic
- reproducible
- locale-consistent

---

# 12. Non-goals

Phase 4.5 MUST NOT:

- perform translation inference
- introduce AI generation
- modify Phase 4 outputs
- influence gameplay semantics

---

# ✅ Final Rule

> 🔒 If a change alters meaning, it is invalid in Phase 4.5.

---

# ✅ Summary

Phase 4.5 is a **strictly controlled transformation layer**:

- deterministic
- non-semantic
- CI-governed
- fully auditable