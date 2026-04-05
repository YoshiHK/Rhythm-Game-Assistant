# PHASE_4.5_SPEC.md
## Phase 4.5 — Localization & Language Adaptation

**Status:** Draft (Speed‑Run, Ready for Review)  
**Upstream Dependencies:**
- Phase 1 — Foundation & Workflow ✅
- Phase 2 — Enhancement ✅
- Phase 3 — Unified Ingestion Manager ✅
- Phase 4 — Personalization & Presentation ✅

**Non‑Negotiable Rule:** *Do not modify anything in Completed Phases.*

---

## 0. Positioning

Phase 4.5 defines the **localization layer** of the Rhythm Game Assistant.

It operates strictly **downstream of Phase 4** and is responsible for adapting
*rendered tips content* into multiple languages and regional variants **without
altering meaning, intent, or personalization decisions**.

Phase 4.5 answers:

> “Given the finalized presentation, how should this be expressed for this locale?”

---

## 1. Purpose

Phase 4.5 exists to:
- enable multi‑language support,
- ensure consistent phrasing across locales,
- preserve trust, determinism, and explainability.

Localization affects **how text is expressed**, never **what is being advised**.

---

## 2. Phase Boundary

### Inputs (from Phase 4 only)
- rendered tips text (canonical)
- narrative template IDs and variant IDs
- personalization provenance
- difficulty label
- locale preference (player or system)

### Outputs
- localized tips text
- localization metadata
- localization provenance

Phase 4.5 MUST NOT mutate:
- element selection
- ordering
- severity
- personalization decisions

---

## 3. Invariants

### 3.1 Semantic Immutability
Localization MUST NOT change:
- gameplay advice
- instructional intent
- ordering or emphasis
- safety messaging

### 3.2 Deterministic Fallback
- A default locale (e.g. `en-US`) MUST always be available.
- Missing translations MUST fall back deterministically.

### 3.3 Non‑Interpretive Translation
Phase 4.5 MAY:
- translate text
- substitute locale‑specific phrasing
- adjust grammar and word order

Phase 4.5 MUST NOT:
- summarize
- paraphrase gameplay meaning
- introduce new guidance

---

## 4. Localization Modes

### 4.1 Pass‑Through Mode
- Localization disabled
- Phase‑4 output returned unchanged

### 4.2 Localized Mode
- Locale resolved
- Translation applied
- Provenance recorded

### 4.3 Pseudo‑Localization Mode (QA)
- Artificial locale expansion
- Length and layout stress testing
- Used for CI and QA only

---

## 5. Locale Resolution Rules

Locale is resolved by priority:
1. explicit request parameter
2. player profile language
3. system default locale

Resolution outcome MUST be recorded.

---

## 6. Translation Sources

Allowed translation sources:
- curated static translations
- versioned translation bundles
- approved machine translation (offline)

Prohibited:
- runtime free‑form generation
- context‑less translation

---

## 7. Provenance & Explainability

Each localized output MUST record:
- base_locale
- target_locale
- translation_source
- translation_version
- fallback_used (boolean)

Localization provenance MUST be append‑only.

---

## 8. Safety Guarantees

Phase 4.5 guarantees:
- no upstream impact
- no semantic drift
- deterministic fallback
- isolation from gameplay logic

---

## 9. Contract Closure

Phase 4.5 is:
✅ downstream‑only  
✅ non‑semantic  
✅ reversible  
✅ auditable  

Phase 4.5 is NOT:
❌ a personalization phase  
❌ a gameplay phase  
❌ a learning phase  

---

**End of PHASE_4_5_SPEC.md**