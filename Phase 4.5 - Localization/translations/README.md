
# translations/ — Localization Store (Phase 4.5)

This directory contains **all localization assets** for the Rhythm Game Assistant.
It is introduced and governed by **Phase 4.5 – Localization**.

> **Core rule:** Localization changes *how things are said*, never *what they mean*.

---

## 1. Purpose of this folder

The `translations/` folder provides:

- language- and locale-specific **narrative templates**
- presentation-only **variants** (casual / expert / debug)
- **glossaries** for consistent terminology
- **locale metadata** for normalization and fallback
- a **pseudo-locale** used exclusively for CI and QA

This folder is **downstream-only**:
- It consumes outputs from Phases 1–4
- It MUST NOT influence gameplay analysis, scoring, or personalization decisions

---

## 2. High-level structure

```
translations/
├─ _meta/
│  ├─ locales.json          # Canonical locales and fallback graph
│  ├─ locale_aliases.json   # Input alias → canonical locale mapping
│  └─ sources.json          # Allowed translation sources
│
├─ en-US/                   # Base locale (authoritative fallback)
├─ en-GB/                   # English (UK)
├─ ja-JP/                   # Japanese
├─ ko-KR/                   # Korean
├─ zh-Hans/                 # Simplified Chinese
├─ zh-Hant-HK/              # Traditional Chinese (Hong Kong)
├─ zh-Hant-TW/              # Traditional Chinese (Taiwan)
├─ pseudo/                  # Pseudo-locale (CI only)
└─ README.md                # This file
```

---

## 3. Per-locale folder layout

Each locale directory follows the **same required structure**:

```
<locale>/
├─ templates/
│  ├─ narrative_v3/
│  │  ├─ difficulty/
│  │  ├─ elements/
│  │  └─ summaries/
│  └─ shared/               # Optional shared fragments (presentation-only)
│
├─ variants/
│  ├─ casual.json
│  ├─ expert.json
│  └─ debug.json
│
├─ glossary.json
└─ locale_meta.json
```

**All locales must maintain template parity.**

---

## 4. Narrative templates (`templates/narrative_v3/`)

- Templates are rendered by **Narrative Module v3**
- Each file must declare:
  - `template_id`
  - `version: "v3"`
  - `strings.default`
- Templates MUST NOT:
  - contain gameplay logic
  - introduce new advice
  - reinterpret analysis results

They are **pure render-time assets**.

---

## 5. Variants (`variants/`)

Variants control **tone and word budgets only**:

- `casual` → friendly, shorter phrasing
- `expert` → technical, more precise phrasing
- `debug`  → verbose, QA / audit use

Variants:
- do not change meaning
- do not change element selection
- are safe to share across locales

---

## 6. Glossary (`glossary.json`)

Glossaries provide **terminology consistency** for each locale.

They:
- are presentation-only
- are not authoritative for gameplay semantics
- help translators and curators stay consistent

Glossaries MUST NOT be used by Phases 1–3.

---

## 7. Locale metadata (`locale_meta.json`)

Each locale declares:

- canonical locale code (e.g. `ja-JP`, `zh-Hans`)
- language name
- fallback locale (always resolves to `en-US` eventually)
- source (`curated`, `approved_machine`, or `generated`)

This file is used by **locale normalization and provenance only**.

---

## 8. Pseudo locale (`pseudo/`)

The `pseudo/` locale is **CI-only** and never user-facing.

It is used to:
- stress-test UI layouts
- catch truncation and overflow bugs
- detect hard-coded English strings
- validate placeholder integrity

Pseudo-localized strings are intentionally unreadable.

---

## 9. What must NOT go in `translations/`

To preserve phase boundaries, this folder MUST NOT contain:

- gameplay rules or heuristics
- element definitions
- severity or scoring logic
- personalization decisions
- conditional logic

If a file is required by Phases 1–3, it does not belong here.

---

## 10. Phase discipline

- Phases 1–4 are **locked**
- Phase 4.5 adds localization **without modifying upstream behavior**
- This folder is safe to evolve independently

When in doubt:
> **Localization changes presentation, never meaning.**

---

**End of README**
