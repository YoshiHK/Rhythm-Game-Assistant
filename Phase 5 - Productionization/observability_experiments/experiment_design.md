## Experiment Design Guidelines (Phase 5)

Experiments in Phase 5 exist to evaluate **presentation and delivery**,
not to alter semantic meaning.

### Allowed Experiments

- Narrative phrasing variants
- Ordering and grouping of tips
- Recommendation surface layout

### Prohibited Experiments

- Semantic content changes
- Severity modification
- Element inclusion or exclusion
- Model parameter changes

### Design Requirements

All experiments MUST:
- be gated by feature flags
- support immediate rollback
- record assignment, exposure, and outcome
- preserve Phase 4 provenance identity

### Interpretation Rules

Experiment results:
- inform offline learning and design decisions
- do not directly alter runtime behavior
- must be reviewed before promotion