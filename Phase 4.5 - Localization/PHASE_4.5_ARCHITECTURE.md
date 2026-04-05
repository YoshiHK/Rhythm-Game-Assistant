# PHASE_4.5_ARCHITECTURE.md
## Phase 4.5 — Localization Architecture

**Status:** Draft (Aligned with PHASE_4_5_SPEC.md)  
**Depends on:**
- Phase 4 Personalization Layer (Locked)

**Invariant:** Phase 4.5 is downstream‑only and non‑semantic.

---

## 1. Architectural Role

Phase 4.5 sits **between Phase 4 and the UI layer**.

Its role is to:
- localize finalized narrative output,
- manage translation assets,
- guarantee consistent fallback behavior.

It does not participate in personalization or analysis.

---

## 2. High‑Level Data Flow

[ Phase 4 Output ]
│ rendered tips text
│ narrative metadata
│ personalization provenance
▼
[ Phase 4.5 Entry ]
│
├─► Locale Resolution
│
├─► Translation Lookup
│
├─► Translation Application
│
├─► Fallback Handling
│
▼
[ Phase 4.5 Output ]
localized tips text + localization provenance

---

## 3. Phase 4.5 Entry Layer

### Responsibilities
- accept Phase‑4 output
- resolve locale
- select localization mode

### Inputs
- tips_text
- template_id / variant_id
- locale hint
- engine_mode

No mutation occurs at entry.

---

## 4. Locale Resolution Layer

- applies priority rules
- validates locale availability
- emits resolution metadata

No translation occurs here.

---

## 5. Translation Store

### Characteristics
- versioned
- locale‑keyed
- template‑aware

Example structure:

translations/
en-US/
ja-JP/
zh-HK/
pseudo/

Translations are **data**, not logic.

---

## 6. Translation Application Layer

Responsibilities:
- substitute localized strings
- preserve placeholders and variables
- enforce formatting safety

No gameplay interpretation is allowed.

---

## 7. Fallback & Degradation Handling

If translation is missing:
- fall back to base locale
- mark fallback_used = true
- continue safely

Failures never block output.

---

## 8. Provenance Assembly

Localization provenance includes:
- locale_resolution
- translation_source
- translation_version
- fallback flags

Provenance is appended to Phase‑4 provenance.

---

## 9. QA & CI Integration

Phase 4.5 supports:
- pseudo‑localization
- string length validation
- placeholder integrity checks

QA tooling is isolated from runtime logic.

---

## 10. Relationship to UI

Phase 4.5 provides:
- ready‑to‑display localized text
- locale metadata
- explanation hooks

The UI performs no translation.

---

## 11. Architectural Summary

Phase 4.5 is:
✅ downstream‑only  
✅ non‑semantic  
✅ deterministic  
✅ safe by default  

It enables multi‑language support **without risking gameplay correctness**.

---

**End of PHASE_4_5_ARCHITECTURE.md**