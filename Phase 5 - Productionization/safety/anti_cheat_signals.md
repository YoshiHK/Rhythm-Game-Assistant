### Anti‑Cheat Signals (Phase 5)

Defines signals indicating potential abuse or cheating.

---

### Signal Types

Examples:

- repeated identical submissions
- impossible performance patterns
- abnormal retry behavior
- coordinated manipulation

---

### Signal Model (UPDATED)

Signals are:

- probabilistic
- weak individually
- meaningful only when aggregated

---

### Signal → Safety Event Mapping (NEW)

Each signal MUST be mapped into:

```
safety_event:
event_type = "anti_cheat_flag"
signal = {...}
severity = derived
```

---

### Severity Guidelines (NEW)

| Level | Meaning |
|------|--------|
| low | anomaly |
| medium | suspicious |
| high | strong abuse signal |
| critical | systemic abuse |

---

### Non‑Goals

- ❌ Signals do NOT prove guilt 
- ❌ Signals do NOT trigger bans 
- ❌ Signals do NOT affect runtime  

---

Anti-cheat signals:
> flag risk, not conclude intent