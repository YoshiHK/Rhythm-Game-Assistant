# Phase 4.5 — Localization

**Status:** Design‑Locked ✅  
**Type:** Presentation Layer (Non-Semantic)  
**Runtime Entry:** Phase 6 only  

---

# 1. What Phase 4.5 Is

Phase 4.5 is the **localization and presentation layer** of the system.

It:

- ✅ transforms narrative output into different locales
- ✅ applies tone and formatting
- ✅ preserves semantic meaning strictly
- ✅ ensures cross-locale consistency

---

# 2. What Phase 4.5 Is NOT

Phase 4.5 MUST NOT:

- ❌ modify gameplay meaning
- ❌ introduce new advice
- ❌ alter scoring / severity
- ❌ perform inference or analysis
- ❌ execute runtime routing decisions

---

# 3. System Position

```
Phase 1–3 → Analysis (locked)
Phase 4   → Personalization (locked)
   ↓
Phase 4.5 → Localization (this phase)
   ↓
Phase 6   → Runtime routing
```

Phase 4.5 is:

- ✅ downstream-only
- ✅ deterministic
- ✅ non-semantic

---

# 4. Core Components

---

## 4.1 Translation Store

translations/
├─ _meta/          (global contract)
└─ {locale}/       (self-contained packs)

Each locale includes:

_meta/
chart_level/
element_level/
section_level/
guidance_framing/
tone/

---

## 4.2 Template System

Narrative v3 templates are **layer-based**:

| Layer | Meaning |
|------|--------|
| Element | WHAT |
| Section | WHEN |
| Chart | OVERALL |
| Guidance | WHERE TO FOCUS |
| Tone | HOW TO SAY |

---

## 4.3 Taxonomy Layer

Taxonomy defines:

- ✅ template families
- ✅ structural grouping

It enforces:

- no overlap
- no drift
- full alignment with registry

---

## 4.4 Locale Normalizer

locale_normalizer/
├─ normalize_locale.py
└─ fallback_rules.py

Responsible for:

- locale resolution
- alias mapping
- fallback chain generation

---

## 4.5 CI Governance

ci/
├─ run_all_localization_checks.py
└─ checks/

CI enforces:

- template parity
- placeholder integrity
- taxonomy alignment
- debug consistency
- token & word constraints

---

# 5. Key Concepts

### ✅ Determinism

Same input → same output

---

### ✅ Template Parity

All locales MUST contain all templates

---

### ✅ Debug Consistency

> debug.json MUST be identical across ALL locales

---

### ✅ Taxonomy Alignment

- every template belongs to one taxonomy
- no missing / extra categories

---

# 6. Failure Model

- ❌ Failures are NOT hidden
- ✅ CI catches issues
- ✅ Runtime surfaces degradation explicitly

---

# 7. Relationship to Other Phases

- Phase 4.5 **depends on Phase 4 output**
- Phase 4.5 **feeds Phase 6**
- Phase 4.5 **does not modify upstream logic**

---

# ✅ Final Rule

> 🔒 If a change alters meaning, it does NOT belong here.

---

# ✅ Summary

Phase 4.5 is a **fully deterministic presentation system**  
with strict contracts, enforced by CI, ensuring safe multi-language output.
