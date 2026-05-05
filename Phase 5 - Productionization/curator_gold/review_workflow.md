## Curator Review Workflow (Phase 5)

This workflow governs how gold labels are produced for training and evaluation.

### Workflow Steps

1. Receive grouped feedback events (by provenance_id).
2. Review generated tips, selected elements, and surrounding context.
3. Apply one or more gold labels.
4. Record confidence and optional notes.
5. Submit labels to an append‑only, versioned store.
6. Escalate ambiguous or disputed cases for secondary review.

### Invariants

- No automatic approval or rejection is permitted.
- Labels do not affect runtime behavior.
- All labels are immutable once written.
- Revisions are represented as new labels, not edits.

This process exists to build **trustworthy training data**, not to police outputs.
