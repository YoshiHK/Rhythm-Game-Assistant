### Feature Flags (Phase 5)

Feature flags control presentation variants for experimentation.

---

### Principles

- Flags gate presentation only
- Flags must be reversible
- Default state must be safe
- Flags must not encode business logic

---

### Telemetry Integration (NEW)

All flags MUST:

- log exposure via telemetry_events
- record:
  - flag_name
  - variant
  - timestamp
  - provenance_id

---

### Examples

- enable_alt_narrative_variant
- enable_practice_hints

---

### Usage Constraints

Flags MUST NOT:

- ❌ alter semantic output
- ❌ change severity or selection
- ❌ bypass Phase 6 enforcement

---

### Relationship to Experiments

Every experiment MUST:

- map to one or more feature flags
- be traceable via telemetry

---

Feature flags exist to:
> safely control presentation, not behavior