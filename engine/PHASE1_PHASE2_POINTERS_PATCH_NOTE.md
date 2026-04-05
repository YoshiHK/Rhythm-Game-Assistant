# Phase 1 → Phase 2 Documentation Pointer Patch Note

## Purpose
This patch introduces **non‑breaking documentation pointers** into Phase 1 documents, clearly directing readers to the Phase 2 (v2) documentation set.

It does **not** modify runtime code, schemas, or configs. The change is purely editorial and safe to apply at any time.

---

## Scope of Change
The following Phase 1 documents receive a short **Phase 2 Note** at the top:

1. `SYSTEM_ARCHITECTURE.md`
   - Adds a pointer to `ADVANCED_SYSTEM_ARCHITECTURE_v2.md`
   - Clarifies that Phase 1 remains the authoritative baseline

2. `SPEC_INDEX.md`
   - Adds a pointer to `ADVANCED_SPEC_INDEX_v2.md`
   - Preserves Phase 1 spec/schema authority

3. `PATCHES_README.md`
   - Adds a pointer to `PATCHES_README_v2.md`
   - Clarifies Phase 1 vs Phase 2 patch responsibilities

4. `ULTIMATE_TIPS_PRODUCTION_GUIDE.txt`
   - Adds a prominent banner pointing to `ULTIMATE_TIPS_PRODUCTION_GUIDE_v2.md`
   - Marks Phase 1 guide as baseline reference only

---

## Motivation
With Phase 2 Track A–D fully established (calibration, selection, guidance, narrative), the documentation set has evolved.

These pointers ensure:
- New readers do not miss Phase 2 behavior
- Phase 1 documents remain frozen and auditable
- Phase 2 documents become the operational entry point

---

## Files Added / Referenced (Phase 2)
- `ADVANCED_SYSTEM_ARCHITECTURE_v2.md`
- `ADVANCED_SPEC_INDEX_v2.md`
- `PATCHES_README_v2.md`
- `ULTIMATE_TIPS_PRODUCTION_GUIDE_v2.md`

---

## Application
Apply the accompanying patch file:

```
patch_phase1_add_phase2_pointers.patch
```

using:

```bash
git apply patch_phase1_add_phase2_pointers.patch
```

---

## Rollback
To rollback, simply revert the documentation files or reset the commit.
No runtime artifacts are affected.

---

## Compatibility
✅ Phase 1: unchanged behavior
✅ Phase 2: fully supported
✅ Runtime: unaffected

---

END
