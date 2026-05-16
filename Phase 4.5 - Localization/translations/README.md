# translations/ — Localization Store (Phase 4.5)

This directory contains **all localization assets** for the Rhythm Game Assistant.

✅ Introduced and governed by **Phase 4.5 – Localization**  
✅ **Core rule:** Localization changes *how things are said*, never *what they mean*

---

# 1. Purpose of this folder

The `translations/` folder provides:

- ✅ language- and locale-specific **narrative templates**
- ✅ tone / variant overlays (**casual / expert / analytical / debug**)
- ✅ **glossaries** for terminology consistency
- ✅ **locale metadata** for routing and fallback
- ✅ **pack metadata** for CI validation and completeness tracking
- ✅ a **pseudo-locale** used exclusively for CI and QA

---

# 2. Critical architectural rules

## ✅ Phase discipline

- ❌ No gameplay logic allowed
- ❌ No scoring / severity logic
- ❌ No personalization decisions
- ✅ Phase 4.5 is strictly **presentation-only**
- ✅ Completely **downstream from Phases 1–4**

---

## ✅ Determinism

- All templates MUST be deterministic
- No randomness
- No conditional execution
- Output must be reproducible

---

## ✅ Locale parity (STRICT)

> 🔒 **All templates MUST exist in all locales**

Enforced by CI via:

- template_registry.json  
- pack_version.json  
- validator checks  

---

# 3. Folder structure

translations/
├─ _meta/                      ← GLOBAL CONTRACT (not per locale)
│  ├─ locales.json
│  ├─ locale_aliases.json
│  ├─ template_registry.json
│  └─ sources.json
│
├─ {locale}/
│  ├─ _meta/                  ← PER-LOCALE META
│  │  ├─ locale_meta.json
│  │  ├─ glossary.json
│  │  ├─ pack_version.json
│  │  └─ debug.json
│  │
│  ├─ chart_level/
│  ├─ element_level/
│  ├─ section_level/
│  ├─ guidance_framing/
│  └─ tone/
│
└─ pseudo/                   ← CI ONLY

---

# 4. Template layers

## ✅ Chart Level
- High-level summary of difficulty and structure

## ✅ Element Level
- Core gameplay mechanics (density, flick, hold, etc.)
- ✅ Most important layer (largest coverage)

## ✅ Section Level
- Structural emphasis (opening, climax, ending)

## ✅ Guidance Framing
- Attention framing and risk explanation
- ✅ No new advice introduced

## ✅ Tone Layer
- Controls presentation style only
- Uses `{base_text}` placeholder

---

# 5. Meta layers

## ✅ GLOBAL (shared)

### template_registry.json
- ✅ Single source of truth
- ✅ Defines ALL template IDs
- ❌ MUST NOT be duplicated per locale

### locales.json
- Defines locale list + fallback graph

### locale_aliases.json
- Maps user input → canonical locale

### sources.json
- Defines allowed translation provenance

---

## ✅ PER-LOCALE (_meta)

### locale_meta.json
- Locale identity + routing metadata

### glossary.json
- Terminology mapping (NOT full translation)

### pack_version.json
- Coverage + validation status
- Used by CI

### debug.json
- ✅ MUST exist per locale
- ✅ MUST be identical across all locales

---

# 6. Glossary rules (CRITICAL)

Glossary is:

✅ terminology reference  
❌ NOT a translation layer  

Rules:

- Keys MUST NOT change
- Values MUST stay semantically aligned
- MUST NOT introduce new concepts

---

# 7. Tone system

Tone templates:

- neutral
- casual
- expert
- analytical

Rules:

- ✅ MUST preserve `{base_text}`
- ❌ MUST NOT change meaning
- ✅ Only modifies phrasing / emphasis

---

# 8. Pseudo locale (CI only)

Purpose:

- UI stress testing
- placeholder validation
- overflow detection
- missing translation detection

Rules:

- ❌ NEVER user-facing
- ✅ MUST contain all templates

---

# 9. CI validation (MANDATORY)

All changes MUST pass:

- ✅ template parity check
- ✅ placeholder integrity check
- ✅ pack completeness check
- ✅ debug consistency check

Validator:

ci/checks/check_pack_integrity.py


---

# 10. Non-goals (important)

This folder MUST NOT contain:

- gameplay logic
- scoring rules
- evaluation heuristics
- AI decision-making
- runtime branching

---

# 11. Design philosophy

> ✅ Localization = Presentation Layer  
> ✅ Templates = Deterministic Data  
> ✅ Meta = System Contract  
> ✅ CI = Enforcement Layer  

---

# ✅ Final rule (memorize this)

> 🔒 **If a change alters meaning, it does NOT belong in Phase 4.5**

---

# ✅ End of README