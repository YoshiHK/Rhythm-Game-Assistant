### Experiment Design Guidelines (Phase 5)

Experiments evaluate presentation and delivery only.

---

### Allowed Experiments

- Narrative phrasing variants
- Tip ordering/grouping
- UI / layout changes

---

### Prohibited Experiments

- ❌ Semantic content changes
- ❌ Severity modification
- ❌ Element inclusion/exclusion
- ❌ Model parameter changes

---

### Design Requirements (UPDATED)

All experiments MUST:

- be gated by feature flags
- record:
  - assignment
  - exposure
  - outcomes
- preserve provenance_id linkage
- log experiment_id and variant

---

### Telemetry Requirements (NEW)

Each experiment MUST produce:

- experiment_exposure event
- outcome metrics (linked to same provenance_id)

---

### Analysis Rules

Experiment results:

- feed into evaluation layer
- may influence dataset construction
- require human review before model update

---

### Invariants

- Experiments DO NOT change semantics
- Experiments DO NOT bypass Phase 6
- All experiments are reversible

---

Experiments exist to:
> test delivery, never to change meaning