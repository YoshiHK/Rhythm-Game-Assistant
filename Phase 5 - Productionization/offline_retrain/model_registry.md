## Model Registry (Phase 5)

The Model Registry records **offline-trained model artifacts**
and their evaluation results.

### Responsibilities

- Register trained model versions
- Store training dataset references
- Record evaluation metrics and validation outcomes

### What the Registry Is NOT

- It does NOT deploy models
- It does NOT select active models
- It does NOT affect runtime execution

### Required Metadata

Each registered model MUST include:
- model_version
- training_dataset_id
- training_timestamp
- evaluation_summary
- validation_status

The registry is an **authoritative ledger**, not a control plane.