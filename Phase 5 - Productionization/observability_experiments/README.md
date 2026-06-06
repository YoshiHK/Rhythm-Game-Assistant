### Phase 5 – Observability & Experimentation

This layer defines how the system:

- measures effectiveness
- runs controlled experiments
- produces analysis signals for learning

---

### Pipeline Role

```
runtime → telemetry_events → metrics → experiments → evaluation → dataset → retraining
```


---

### Purpose

- Measure effectiveness of recommendations and tips
- Enable controlled, reversible experiments
- Provide reliable signals for offline learning

---

### What This Layer Does

- Collect structured telemetry events
- Compute canonical metrics
- Record experiment exposure and outcomes
- Support evaluation and model validation

---

### What This Layer Does NOT Do

- ❌ Does NOT modify semantic outputs
- ❌ Does NOT affect runtime decision logic
- ❌ Does NOT trigger model updates
- ❌ Does NOT replace curator judgment

---

### Data Contract

Primary schema:
- telemetry_events.schema.json

Generated via:
- build_telemetry_event()
---

### Relationship to Other Layers

Upstream:
- Runtime execution (Phase 6 governed)

Downstream:
- Evaluation layer (metrics consumption)
- Dataset builder (feature signals)
- Model validation

---

### Invariants

- All telemetry is non-semantic
- All experiments are reversible
- All results are deterministic
- Observability NEVER controls execution

---

Observability exists to:
> measure reality safely, not to steer it