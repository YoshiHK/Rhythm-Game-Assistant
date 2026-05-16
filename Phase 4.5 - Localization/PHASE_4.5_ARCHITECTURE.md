## Phase 4.5 Architecture — Localization

**Status:** Design‑Locked ✅  
**Phase Type:** Presentation Layer (Deterministic)  
**Runtime Ownership:** Phase 6 (invocation only)

---

# 1. Purpose

Phase 4.5 provides **deterministic localization and presentation transformation**
for personalized gameplay tips.

Its responsibilities are to:

- ✅ adapt presentation to locale
- ✅ enforce template-based rendering
- ✅ preserve semantic meaning strictly
- ✅ ensure cross-locale consistency

Phase 4.5 NEVER modifies gameplay semantics.

---

# 2. Architectural Position

Phase 1–3 → Analysis (locked)
Phase 4   → Personalization (locked)
↓
Phase 4.5 → Localization
↓
Phase 6   → Runtime routing

Phase 4.5:
- ✅ is downstream-only
- ✅ is non-semantic
- ✅ is deterministic
- ❌ cannot call upstream phases

---

# 3. Core Layers (Current Architecture)

Phase 4.5 is composed of:

---

## 3.1 Translation Store

translations/
├─ _meta/                (global contract)
├─ {locale}/             (self-contained locale pack)

Each locale contains:

_meta/
chart_level/
element_level/
section_level/
guidance_framing/
tone/

---

## 3.2 Template System (Narrative v3)

Template structure is stratified:

| Layer | Role |
|------|------|
| Element | WHAT |
| Section | WHEN |
| Chart | OVERALL |
| Guidance | WHERE TO FOCUS |
| Tone | HOW TO SAY |

All templates:
- MUST be deterministic
- MUST preserve placeholders
- MUST be identical in structure across locales

---

## 3.3 Taxonomy Layer

Taxonomy defines:

- ✅ allowed template families
- ✅ grouping rules

It does NOT define:
- ❌ logic
- ❌ detection

Enforced via:
- taxonomy_validator.py

---

## 3.4 Locale Normalizer

locale_normalizer/
├─ normalize_locale.py
└─ fallback_rules.py

Responsibilities:

- ✅ resolve canonical locale
- ✅ apply aliases
- ✅ build fallback chain

This layer is:
- deterministic
- non-semantic
- routing-only

---

## 3.5 CI Governance Layer

ci/
├─ run_all_localization_checks.py
└─ checks/

CI enforces:

- ✅ taxonomy alignment
- ✅ template parity
- ✅ placeholder integrity
- ✅ debug consistency
- ✅ token/word constraints

---

# 4. Responsibilities

Phase 4.5 owns:

- locale resolution
- template selection (mapping only)
- placeholder-safe rendering
- tone application
- localization metadata

---

# 5. Hard Boundaries

Phase 4.5 MUST NOT:

- ❌ modify gameplay meaning
- ❌ introduce new elements
- ❌ change severity or score
- ❌ perform free-form translation
- ❌ apply AI transformation

---

# 6. Determinism Guarantees

Phase 4.5 guarantees:

- same input → same output
- locale-independent semantics
- no hidden fallback behavior

---

# 7. Failure Model

Failures are:

- ✅ caught in CI (preferred)
- ✅ explicit at runtime
- ❌ NEVER silent

---

# 8. Key Invariants

- template_registry is global source of truth
- all locales must have full template parity
- debug.json must be identical across locales
- fallback chains must terminate

---

# ✅ Final Statement

Phase 4.5 is a **sealed, deterministic presentation layer**  
that guarantees:

- semantic safety
- cross-language consistency
- CI-enforced correctness