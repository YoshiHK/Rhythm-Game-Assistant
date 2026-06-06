## Phase 5 — Safety, Legal, and Anti-Cheat

This layer defines how the system:

- detects risk
- records structured safety events
- escalates issues for enforcement

---

## 🔷 Pipeline Role

```
telemetry / feedback / marketplace
→ safety_events
→ escalation
→ Phase 6 enforcement
```

---

## 🔷 Purpose

- Protect system integrity
- Preserve fairness in learning
- Ensure legal and compliance alignment
- Support evidence-based enforcement

---

## 🔷 What This Layer Does

- Detect risk signals (anti-cheat / misuse)
- Structure signals into safety_events
- Classify severity
- Record decisions (non-enforcing)
- Escalate to Phase 6

---

## 🔷 What This Layer Does NOT Do

- ❌ Does NOT block runtime execution
- ❌ Does NOT apply penalties
- ❌ Does NOT modify recommendations
- ❌ Does NOT define legal outcomes

---

## 🔷 Core Model (NEW)

```
signal → classification → decision → safety_event → escalation
```

---

## 🔷 Data Contract (NEW)

Primary schema:
- `safety_events.schema.json`

Generated via:
- `build_safety_event()`

Key objects:
- `severity` (low/medium/high/critical)
- `signal` (raw detection signals)
- `decision` (action + automation flag)
- `review` (manual review status)

---

## 🔷 Severity Classification

| Level | Risk Score | Action |
|-------|------------|--------|
| low | < 0.4 | monitor |
| medium | 0.4–0.7 | flag |
| high | 0.7–0.9 | restrict |
| critical | ≥ 0.9 | temporary_block |

---

## 🔷 Event Types

| Event | Trigger |
|-------|----------|
| abuse_detected | pattern matching |
| anti_cheat_flag | anomaly detection |
| policy_violation | rule breach |
| content_flagged | harmful content |
| account_action | enforcement |
| safety_review_required | manual escalation |

---

## 🔷 Relationship to Other Layers

| Layer | Role |
|-------|------|
| Telemetry | system behavior |
| Feedback | user reaction |
| Marketplace | economic signals |
| Safety | risk detection |
| Phase 6 | enforcement |

---

## 🔷 Invariants

- Signals are probabilistic (not definitive)
- No automatic punishment
- All events are auditable
- All decisions are reversible
- Phase 6 is the only enforcement authority

---

## 🔷 Design Intent

Safety defines:

✅ what is risky
✅ what needs escalation
✅ evidence for enforcement

NOT:

❌ what punishment is
❌ what truth is
❌ runtime control

---

**Safety: Detecting and structuring risk, not enforcing it.**
