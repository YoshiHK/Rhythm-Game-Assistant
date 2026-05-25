# CI Observability Layer — Design Overview

## Purpose

This layer provides **phase-agnostic CI observability** for the repository.

It operates strictly on the **CI SUMMARY log contract** and does not:
- evaluate business logic
- invoke runtime code
- enforce Phase semantics

---

## Role in System Architecture

CI Observability sits **outside all Phases**:

```
Phase 4 / 4.5 / 6 / 7 CI
          ↓
CI SUMMARY (log-level signals)
          ↓
Observability Layer (this module)
          ↓
Alerting / Dashboard / External Gate
```

---

## CI SUMMARY Contract (v1)

Each Phase CI job should emit:

CI SUMMARY: phase=<phase_id> status=<ok|FAIL> ...

### Required fields

- `phase` — logical phase identifier  
  e.g. `phase4`, `phase6`, `phase7`, `integration`

- `status` — CI result  
  - `ok`
  - `FAIL`

### Optional fields

- `reason=...`
- `waived_total=used/budget`

---

## Aggregation Model

The scraper produces:

```
{
  "total": 4,
  "by_phase": {
    "phase4": {"status": "ok"},
    "phase6": {"status": "ok"},
    "phase7": {"status": "ok"},
    "integration": {"status": "ok"}
  },
  "by_status": {
    "ok": 4
  },
  "latest": {...}
}
```

### Alerting Model
Alert rules operate on:

✅ Phase-aware health
Fail when:

```
any phase.status == FAIL
```

✅ Budget thresholds (optional)
Fail when:

```
used / budget >= threshold
```

---

###Design Principles
1. Phase-agnostic

- The layer does NOT understand Phase logic
- It only processes CI signals

2. Non-semantic

- No gameplay, ranking, or personalization logic
- Pure infrastructure signal processing

3. CI-only

- Never used in runtime paths
- Never imported by API or engine layers

4. Deterministic

- Same input logs → same output aggregate

---

### What This Layer Guarantees

✅ Unified CI health view
✅ Phase-level visibility
✅ External alerting readiness
✅ Scalable architecture (new phases require no change)

---

### What This Layer Does NOT Do

❌ Does not validate Phase correctness
❌ Does not run tests
❌ Does not replace CI pipelines
❌ Does not interpret business meaning

---

### Future Extensions

Possible improvements:

- CI health dashboard JSON export
- GitHub Check annotations
- Slack / webhook alerts
- Historical CI trend analysis

---

### Summary

This layer elevates CI from:

```
pass / fail logs
```

to:

```
structured system observability
```
