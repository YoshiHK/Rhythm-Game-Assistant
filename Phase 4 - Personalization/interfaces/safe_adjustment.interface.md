## PHASE_4_SAFE_ADJUSTMENT_INTERFACE.md
### Phase 4 — Safe Adjustment Interface

**Status:** Draft (Lock‑ready)

### 1. Authority
This interface is the **only place** where personalization
adjustments may be applied.

### 2. Inputs
- elements_skeleton (read‑only)
- base_narrative (Phase 2)
- adjustment_directives (from Decision Interface)

### 3. Allowed Adjustments
- element reordering
- scalar reweighting
- template selection
- variant selection

### 4. Prohibited Adjustments
MUST NOT:
- change analytical meaning
- modify severity, scores, guidance
- inject new gameplay claims

### 5. Application Rules
- applied after Phase‑2 selection
- purely additive
- reversible

### 6. Failure Handling
If validation fails:
- skip all adjustments
- return deterministic output

### 7. Output
- elements_view
- applied_adjustments
- adjustment_provenance

This interface is mandatory and CI‑enforced.
