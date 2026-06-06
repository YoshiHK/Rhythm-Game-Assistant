### Monetization Rules

Defines economic interactions in marketplace.

---

### Transaction Types

- purchase
- reward
- refund

---

### Mapping to Events (NEW)

Each transaction MUST emit:

```
marketplace_event:
event_type = "transaction"
```

---

### Economic Constraints

- all transactions MUST be auditable
- must support reversal
- must be transparent to users

---

### Anti-Abuse Integration (NEW)

Suspicious transactions MUST:

```
→ trigger safety_event
```

Examples:

- abnormal purchase patterns
- reward farming
- coordinated manipulation

---

Monetization ensures:
> fair and transparent economic system