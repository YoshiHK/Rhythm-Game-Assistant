## Feature Flags (Phase 5)

Feature flags are used to **control presentation variants**
for experimentation and gradual rollout.

### Principles

- Flags gate presentation only
- Flags must be reversible
- Default state must be safe
- Flags do not encode business logic

### Examples

- enable_alt_narrative_variant
- enable_practice_hints

### Non‑Goals

Feature flags MUST NOT:
- alter semantic output
- affect severity or element selection
- bypass Phase 6 enforcement
