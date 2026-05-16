# locale_normalizer/ — Locale Resolution Layer (Phase 4.5)

## 1. Purpose

This module provides **deterministic locale normalization and fallback resolution**  
for Phase 4.5 Localization.

It is responsible for:

- ✅ converting user-provided locale → canonical locale
- ✅ applying alias mappings
- ✅ generating fallback chains
- ✅ validating fallback graph correctness

---

## 2. Scope (STRICT)

This layer is:

✅ routing-only  
✅ deterministic  
✅ non-semantic  

This layer MUST NOT:

- ❌ perform translation
- ❌ modify narrative text
- ❌ introduce gameplay meaning
- ❌ interact with templates directly

---

## 3. Module Structure

locale_normalizer/
├─ init.py
├─ normalize_locale.py     # entry point
└─ fallback_rules.py       # fallback chain logic

---

## 4. Core Function

### normalize_locale()

Input:

- requested_locale (user input)
- locales_config (from translations/_meta/locales.json)
- alias_config (from translations/_meta/locale_aliases.json)

Output:

```
{
  "canonical_locale": "zh-Hant-TW",
  "fallback_chain": ["zh-Hant-TW", "en-US"],
  "is_supported": true,
  "used_alias": true
}
```

---

## 5. Fallback Rules
Fallback chain MUST:

✅ be deterministic
✅ have no cycles
✅ terminate (typically at base_locale)

Example:
zh-Hant-HK → zh-Hant-TW → en-US

---

## 6. Invariants

normalize_locale MUST always return a valid supported locale
fallback_chain MUST be valid under all conditions
behavior MUST NOT depend on external state

---

## 7. Relationship to Phase 4.5
Input → normalize_locale → lookup → apply templates

This module sits between Phase 4 output and translation lookup.

---

## ✅ Final Rule

🔒 If locale resolution changes behavior, it is a bug.

---

## Summary
The locale_normalizer ensures that all localization decisions are deterministic,
valid, and safe before template rendering.