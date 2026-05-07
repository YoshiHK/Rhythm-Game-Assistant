# Phase 4 — Personalization

Phase 4 is the **personalization and presentation layer** of the Rhythm Game Assistant.

It answers one question:

> Given the analytical truth, **how should this be presented to this player?**

Phase 4 is strictly **downstream-only** and **non-destructive**.
It personalizes *presentation*, not *meaning*.

---

## What Phase 4 Does

Phase 4:
- adapts tip presentation to player context
- optionally reorders or reweights elements
- selects narrative templates and phrasing variants
- produces explainable, auditable outputs
- guarantees deterministic fallback at all times

Phase 4 does **not**:
- detect gameplay patterns
- change severity, scores, or guidance
- generate free-form text
- learn online or affect live behavior

---

## Inputs and Outputs

### Inputs (from Phase 3 only)
- canonical payload
- canonical row(s)
- elements skeleton
- upstream provenance
- optional player context and flags

### Outputs
- rendered tips text
- unchanged elements skeleton
- personalization provenance
- presentation metadata (for UI and CI)

---

## Runtime Flow (High-Level)

1. Request received
2. Deterministic core run
3. Personalization decision (rule-based)
4. Optional model inference (advisory)
5. Safe adjustment application (non-destructive)
6. Narrative Module v3 rendering
7. Response assembly
8. Event logging
9. Feedback capture
10. Curator triage (offline)
11. Offline retraining and promotion

---

## Determinism and Safety

Phase 4 guarantees:
- a deterministic, non-personalized output is always available
- personalization can be skipped or reverted safely
- no upstream artifacts are mutated
- all adjustments are traceable

If any invariant fails, Phase 4 **falls back to deterministic mode**.

---

## Explainability

Every Phase 4 output includes provenance that explains:
- why personalization was (or was not) applied
- what adjustments were suggested
- what adjustments were actually applied
- which template and variant were used

No personalization is allowed without explainability.

---

## Events, Feedback, and Curators

Phase 4 emits:
- structured, append-only events
- user feedback records (offline only)

Curators:
- review flagged or sampled outputs
- provide gold labels
- trigger offline retraining

Curator actions **never affect live behavior**.

---

## Relationship to Other Phases

- Phase 1–3: analytical truth (locked)
- Phase 4: presentation personalization (this phase)
- Phase 4.5: localization and i18n
- Phase 5+: productionization, learning, recommendations

---

## Status

Phase 4 is:
✅ downstream-only  
✅ non-destructive  
✅ explainable by construction  
✅ CI-enforced  

See:
- `PHASE_4_SPEC.md` for normative rules
- `PHASE_4_ARCHITECTURE.md` for system structure
- `ci/` for enforcement logic