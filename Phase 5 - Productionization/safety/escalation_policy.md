### Escalation Policy (Phase 5 → Phase 6)

Defines how safety events are escalated.

---

### Escalation Model

```
safety_event → severity check → escalation package → Phase 6
```

---

### Escalation Triggers

- sustained anti-cheat signals 
- repeated violations
- legal risk indicators 

---

### Escalation Inputs (NEW)

Each escalation MUST include:

- safety_events
- provenance_id
- supporting signals
- historical context

---

### Severity-Based Flow (NEW)

| Severity | Action |
|--------|--------|
| low | log only |
| medium | monitor |
| high | escalate |
| critical | immediate escalation |

---

### Invariants

- No direct enforcement 
- All escalations logged 
- Human review required for severe cases 

---

Escalation separates:
> detection from enforcement