### Phase 5 — Safety, Legal, and Anti‑Cheat

This layer defines how the system:

- detects risk
- records structured safety events
- escalates issues for enforcement

---

### Pipeline Role (UPDATED)

```
telemetry / feedback / marketplace
→ safety_events
→ escalation
→ Phase 6 enforcement
```

---

### Purpose

- Protect system integrity
- Preserve fairness in learning
- Ensure legal and compliance alignment

---

### What This Layer Does

- Detect risk signals (anti-cheat / misuse)
- Structure signals into safety_events
- Classify severity
- Record decisions (non-enforcing)
- Escalate to Phase 6

---

### What This Layer Does NOT Do

- ❌ Does NOT block runtime execution
- ❌ Does NOT apply penalties
- ❌ Does NOT modify recommendations
- ❌ Does NOT define legal outcomes

---

### Core Model (NEW)

```
signal → classification → decision → safety_event → escalation
```

---

### Data Contract (NEW)

Primary schema:
- safety_events.schema.json

Generated via:
- build_safety_event()

Core fields:
- severity
- signal
- decision

### Relationship to Other Layers

| Layer | Role |
|------|------|
| telemetry | system behavior |
| feedback | user reaction |
| marketplace | economic signals |
| safety | risk detection |

---

### Invariants

- Signals are probabilistic
- No automatic punishment
- All events are auditable
- All decisions are reversible
- Phase 6 is the only enforcement authority 

---

### Design Intent

Safety defines:

✅ what is risky  
✅ what needs escalation  

NOT:

❌ what punishment is  
❌ what truth is  

---

Safety exists to:
> detect and structure risk, not enforce it