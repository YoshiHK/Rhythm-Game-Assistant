### Recommendation API Contract

Defines the structure and guarantees of recommendation responses.

---

### Request → Response Flow

```
request → model → recommendation_response → UI → telemetry
```


---

### Response Requirements

Each response MUST include:

#### Identity
- response_id
- request_id
- provenance_id

#### Model Trace
- model_version
- feature_version

#### Recommendations
Each recommended item MUST include:

- item_id
- rank
- score (optional)
- reason:
  - primary_reason
  - reason_codes

---

### Explanation Rules (NEW)

- Explanation must be derived from reason_codes
- Human-readable rationale must come from rationale_mapping

---

### Determinism

Given same:

- request
- model_version
- feature_version

Response MUST be identical

---

### Telemetry Integration (NEW)

Each response MUST support logging:

- exposure events
- interaction events
- outcome signals

---

### Evaluation Compatibility (NEW)

Response structure MUST support:

- selection evaluation
- reason alignment evaluation

---

### Versioning (NEW)

Response MUST include version metadata:

- schema_version
- mapping_version

---

### Error Handling

Errors MUST:

- include error_code
- specify stage (model / mapping / response)

---

### Non-Goals

API MUST NOT:

- expose internal model logic
- include sensitive data
- perform runtime learning

---

### Invariants

- Response is immutable once generated
- All reasoning is auditable
- All outputs are traceable

---

The API contract exists to:
> provide stable, explainable, and measurable outputs