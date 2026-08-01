# VALIDATOR_V2_SPEC.md
## Validator v2 — Capability & Structural Validation Contract (Additive)

**Scope:** Phase 3 — Unified Ingestion Manager (UMI)  
**Status:** Draft (Additive, Non‑Breaking)

This document defines the **Validator v2 specification** used by the Unified Ingestion
Manager to determine whether a chart payload is **structurally valid and approachable
for tips generation**.

> IMPORTANT
> - “v2” refers to the **specification only**, not filenames or class names.
> - Game‑specific validators **MUST NOT** be renamed or versioned.
> - This spec introduces **no breaking changes** to completed phases.

---

## 1. Purpose

Validators answer one and only one question:

> **Can this chart meaningfully proceed through the tips‑generation pipeline?**

Validators exist as a **gate** before deeper analysis. They do not participate in
selection, personalization, or narrative generation.

---

## 2. Required Interface (Unchanged)

All validators MUST implement:

```python
validate(canonical_payload: dict) -> dict
```

### 2.1 ValidationResult shape

```json
{
  "supported": true,
  "errors": [],
  "warnings": [],
  "degraded_mode": false
}
```

#### Field semantics
- **supported**  
  - `true`: pipeline may proceed  
  - `false`: pipeline must stop
- **errors**  
  - Hard blockers; non‑empty only when `supported == false`
- **warnings**  
  - Non‑fatal issues surfaced to QA or UI
- **degraded_mode**  
  - Indicates partial or reduced support (not a failure)

Existing validators that already return an equivalent structure are compliant.

---

## 3. Optional v2 Methods (Additive)

Validator v2 formalizes optional methods that may already exist informally.

### 3.1 `capabilities() -> dict` (OPTIONAL)

Returns an **informational capability descriptor**.

Example:
```json
{
  "supports_sections": false,
  "supports_variable_bpm": true,
  "note_model": "lane_based"
}
```

Rules:
- Informational only (no gating logic)
- Must not modify payloads
- Intended for QA, diagnostics, and UI explanation

---

### 3.2 `explain_failure(result: dict) -> str` (OPTIONAL)

Produces a **human‑readable explanation** of a validation failure or degraded result.

Example:
```
"This chart lacks sufficient structural consistency to generate actionable tips."
```

Rules:
- Deterministic
- No player data
- No gameplay advice or tips

---

## 4. Validator Responsibilities (Strict)

Validators MAY:
- Check presence of required payload fields
- Verify structural integrity (e.g., note_events non‑empty)
- Detect unsupported or ambiguous patterns
- Flag degraded‑mode conditions

Validators MUST NOT:
- Infer gameplay difficulty or skill requirements
- Map tags to elements
- Generate or modify tips
- Mutate canonical payloads
- Execute Phase 4 personalization logic

---

## 5. Degraded Mode Semantics

`degraded_mode = true` means:
- The chart **may proceed**, but
- Tip quality, coverage, or specificity may be reduced

Examples:
- Virtual‑lane mapping for spatial charts
- Missing section metrics
- Non‑standard note grammars

Degraded mode is **not** a validation failure.

---

## 6. Backward Compatibility Guarantee

- Existing validators require **no changes**
- `validate()` remains the only required method
- Optional methods are ignored if absent

This spec introduces **no breaking changes**.

---

## 7. Phase Relationships

| Phase | Interaction |
|------|-------------|
| Phase 1 | Validator gates approachability (Step 3) |
| Phase 2 | Validator output informs QA and summaries |
| Phase 3 | Validator belongs here |
| Phase 4 | Validator is NOT involved |

---

## 8. Explicit Non‑Goals

This specification does **not** define:
- Pattern taxonomies
- Element inference rules
- Severity or scoring logic
- Narrative or personalization behavior

Those belong to later pipeline stages.

---

**End of VALIDATOR_V2_SPEC.md**
