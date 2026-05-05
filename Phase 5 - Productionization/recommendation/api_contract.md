## Recommendation API Contract (Phase 5)

This document defines the stable API boundary
for recommendation delivery.

### Guarantees

- Request and response schemas are versioned
- Backward compatibility is preserved
- Responses are deterministic for identical inputs (within a version)

### Non‑Guarantees

- The API does NOT guarantee optimality
- The API does NOT expose model internals
- The API does NOT provide tuning controls

### Compatibility Rules

- New fields must be additive
- Existing fields must not change semantics
- Deprecated fields must be supported through transition periods

The API contract protects **clients**, not models.
