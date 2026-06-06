### Model Registry (Phase 5)

The Model Registry records **offline-trained model artifacts**
and their evaluation results.

---

### Responsibilities

- Register model versions (immutable)
- Link models to training datasets
- Store evaluation and validation results
- Ensure full traceability

---

### Required Metadata (UPDATED)

Each model MUST include:

#### Identity
- model_version
- training_timestamp

#### Dataset
- training_dataset_id
- label_schema_version
- feature_schema_version
- taxonomy_version

#### Evaluation
- evaluation_summary:
  - selection metrics
  - reason alignment metrics
- evaluation_timestamp

#### Validation
- validation_status (pass / fail)
- validation_report_reference

---

### Optional Metadata (Recommended)

- experiment_id / variant
- baseline_comparison_id
- diagnostics_trace_reference

---

### What the Registry Is NOT

- It does NOT deploy models
- It does NOT select active models
- It does NOT affect runtime execution

---

### Invariants

- Registry entries are immutable
- All models are reproducible from dataset_id
- All evaluations are auditable

---

The registry is:
> an authoritative ledger, not a control plane.