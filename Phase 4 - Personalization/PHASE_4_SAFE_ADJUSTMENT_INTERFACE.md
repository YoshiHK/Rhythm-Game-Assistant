
# PHASE_4_SAFE_ADJUSTMENT_INTERFACE.md
## Phase 4 — Safe Adjustment Interface

**Status:** Draft (Lock‑ready)

**Depends on:**
- PHASE_4_SPEC.md
- PHASE_4_ARCHITECTURE.md
- PHASE_4_PERSONALIZATION_DECISION_INTERFACE.md

**Core Rule:** Do not modify anything in Completed Phases.

---

## 1. Purpose

The Safe Adjustment Interface defines **how personalization adjustments are applied** in Phase 4 *without mutating analytical truth*.

It ensures that personalization:
- is **non‑destructive**,
- is **fully reversible**,
- and is **auditable**.

No Phase‑4 component may apply adjustments outside this interface.

---

## 2. Position in Phase‑4 Flow

```
Personalization Decision Interface
        ↓
[ Safe Adjustment Interface ]
        ↓
Narrative Module v3
```

This interface consumes **adjustment directives** and applies them safely to presentation‑layer data only.

---

## 3. Input Contract

### 3.1 Required Inputs (Read‑Only)

```json
{
  "elements_skeleton": [ ... ],
  "base_narrative": "...",
  "adjustment_directives": { ... }
}
```

- `elements_skeleton` is produced by Phase 2 and MUST NOT be modified.
- `base_narrative` is the deterministic Phase‑2 text.

---

## 4. Allowed Adjustments

The Safe Adjustment Interface MAY apply the following **presentation‑only** adjustments:

### 4.1 Element Ordering
- Reorder elements for display or emphasis.
- Original element content remains unchanged.

### 4.2 Scalar Reweighting
- Apply scalar weights for ranking or emphasis.
- Weights do not alter stored scores or severity.

### 4.3 Narrative Template Selection
- Select among pre‑defined narrative templates.
- No free‑form generation or semantic rewrite.

### 4.4 Variant Selection
- Choose a phrasing variant within the selected template.

---

## 5. Prohibited Adjustments (Hard Constraints)

The interface MUST NOT:

- create new elements
- delete elements
- modify severity labels
- modify scores or coverage
- alter guidance fields
- inject new gameplay claims

Any attempt to do so invalidates Phase‑4 compliance.

---

## 6. Application Rules

- Adjustments are applied **after Phase‑2 selection**.
- Adjustments are **purely additive**.
- Original ordering and text MUST remain recoverable.

If adjustment validation fails:
- all adjustments are skipped
- deterministic output is returned

---

## 7. Output Contract

```json
{
  "elements_view": [ ... ],
  "applied_adjustments": { ... },
  "adjustment_provenance": { ... }
}
```

- `elements_view` is a reordered / weighted view only.
- `applied_adjustments` records what was applied.
- `adjustment_provenance` links to Phase‑4 provenance.

---

## 8. Safety & Reversibility

The Safe Adjustment Interface guarantees:

- deterministic fallback
- full reversibility
- zero upstream impact

It is safe to disable entirely at runtime.

---

## 9. Contract Summary

This interface is:
✅ non‑destructive
✅ reversible
✅ auditable
✅ model‑agnostic
✅ mandatory for all Phase‑4 personalization

---

**End of PHASE_4_SAFE_ADJUSTMENT_INTERFACE.md**
