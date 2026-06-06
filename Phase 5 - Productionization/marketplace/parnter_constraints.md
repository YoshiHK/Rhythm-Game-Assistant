### Partner Constraints

Defines external integration rules.

---

### Partner Data Rules

- content metadata MUST remain consistent
- creator attribution MUST be preserved
- monetization rules MUST not be bypassed

---

### Event Compliance (NEW)

External integrations MUST:

- produce marketplace_events
- maintain schema compatibility

---

### Safety Integration

Partner violations MUST:

```
→ generate safety_event
```

---

### Invariants

- no hidden logic
- no bypass of marketplace rules
- no unauthorized monetization

---

Partner constraints ensure:
> ecosystem integrity across integrations