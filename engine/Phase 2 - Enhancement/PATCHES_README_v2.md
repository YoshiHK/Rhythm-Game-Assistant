# PATCHES_README_v2.md
Patch Artifacts – Project SEKAI Tips Generation (Phase 2)

This document supersedes `PATCHES_README.md` by adding Phase 2 patch conventions and an expanded patch manifest.

**Important:** Patch files are version-control migration aids only.
- Do **not** import patch files in Python.
- Apply with `git apply` (or your VCS tooling) in a clean working tree.

---

## 1) Patch Inventory (detected)
- (no patch files found in this checkout)

---

  

## Phase 1 → Phase 2 Documentation Pointer Patch

  

### Patch

-  `patch_phase1_add_phase2_pointers.patch`

  

### Purpose

This patch introduces **non‑breaking documentation pointers** into Phase 1 documents, directing readers to the Phase 2 (v2) documentation set.

  

It does **not** modify runtime code, schemas, configs, or pipeline behavior.

The change is purely editorial and safe to apply at any time.

  

### Scope of Change

The patch adds a short **Phase 2 Note** at the top of each Phase 1 document:

  

-  `SYSTEM_ARCHITECTURE.md`

→ points to `ADVANCED_SYSTEM_ARCHITECTURE_v2.md`

  

-  `SPEC_INDEX.md`

→ points to `ADVANCED_SPEC_INDEX_v2.md`

  

-  `PATCHES_README.md`

→ points to `PATCHES_README_v2.md`

  

-  `ULTIMATE_TIPS_PRODUCTION_GUIDE.txt`

→ banner pointing to `ULTIMATE_TIPS_PRODUCTION_GUIDE_v2.md`

  

Each Phase 1 document remains authoritative for the **baseline** system; Phase 2 documents are the operational reference for Track A–D.

 ---

### Motivation

With Phase 2 Tracks A–D fully established (calibration, selection, guidance, narrative), documentation needed a clear and explicit handoff:

  

- Phase 1 docs stay frozen and auditable

- Phase 2 docs become the active operational truth

- Readers cannot accidentally miss Phase 2 behavior

  

### Application

Apply using Git:

  

```bash

git apply patch_phase1_add_phase2_pointers.patch

``

## 2) Patch Naming Convention
- `patch_<scope>_<intent>.patch`
- Scope examples: `trackA`, `trackB`, `trackC`, `trackD`, `wire`, `runner`

---

## 3) Recommended Application Order (Phase 2)
1) **Track A wiring fixes** (ensure calibrated wrapper is called correctly)
2) **Track B selector wiring** (switch selection to `selector_v2`)
3) **Track C/D wiring** (swap guidance/narrative modules to v2)
4) **Runner/spec index updates** (documentation-only if runner already stable)

If you only need feature work and not wiring, skip patches and keep your local integration consistent.

---

## 4) Patch Documentation Template
For each patch, keep a short header block:
- Target file(s)
- Purpose
- Preconditions
- Postconditions
- Rollback steps

---

## 5) Legacy Note
Phase 1 patch readme (`PATCHES_README.md`) describes the baseline runner-default patch. Phase 2 expands patches primarily for calibration + selection + narrative wiring.

END
