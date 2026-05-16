# taxonomy/ — Localization Taxonomy Layer (Phase 4.5)

## 1. Purpose

This directory defines **all allowed template families**  
used in Phase 4.5 Localization.

Each taxonomy corresponds to a **layer in the narrative system**.

---

## 2. Taxonomy Layers

taxonomy/
├─ CHART_TEMPLATE_TAXONOMY.md
├─ SECTION_TEMPLATE_TAXONOMY.md
├─ ELEMENT_TEMPLATE_TAXONOMY.md
├─ GUIDANCE_TEMPLATE_TAXONOMY.md
└─ TONE_TEMPLATE_TAXONOMY.md

---

## 3. Role of Taxonomy

Taxonomy defines:

✅ allowed template categories  
✅ grouping of templates  
✅ semantic boundaries  

Taxonomy does NOT define:

❌ detection logic (Phase 1)  
❌ scoring or severity (Phase 2)  
❌ personalization rules (Phase 4)  

---

## 4. Relationship to Other Components

template_registry.json → "what exists"
taxonomy               → "how they are grouped"
templates              → "how they are expressed"

---

## 5. Core Invariants

### 🔒 1. Full Alignment

Every template_id MUST:

- ✅ exist in template_registry.json
- ✅ exist in exactly ONE taxonomy

---

### 🔒 2. No Overlap

A template_id:

- ❌ MUST NOT appear in multiple taxonomies

---

### 🔒 3. No Drift

Taxonomy MUST NOT:

- introduce new template IDs
- omit registry IDs

---

## 6. CI Enforcement

The following checks ensure correctness:

- taxonomy_validator.py
- check_pack_integrity.py

---

## 7. Design Philosophy

Each layer serves a distinct role:

| Layer     | Meaning |
|-----------|--------|
| Element   | WHAT |
| Section   | WHEN |
| Chart     | OVERALL |
| Guidance  | WHERE TO FOCUS |
| Tone      | HOW TO SAY |

---

## ✅ Final Rule

> 🔒 If a template_id is not defined here, it MUST NOT exist.

---

## Summary

The taxonomy layer is the **structural backbone** of localization, ensuring
consistency, non-overlap, and long-term stability.