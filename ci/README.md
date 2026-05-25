# CI Architecture Overview — Rhythm Game Assistant

## Purpose

This document defines the **CI architecture of the repository**.

It ensures:
- ✅ Phase isolation
- ✅ Deterministic testing
- ✅ Clean runtime boundaries
- ✅ Scalable observability

---

## High-Level CI Structure

The CI system is split into **three distinct layers**:

```
Phase CI (isolated)
↓
Integration CI (orchestrator)
↓
External CI Observability (signal aggregation + alerting)
```

---

## 1. Phase-Level CI (Primary Gatekeepers)

Each Phase has its **own independent CI workflow**.

### Design principles
- ✅ Runs only its own Phase code
- ✅ No cross-phase imports
- ✅ Minimal dependencies
- ✅ Deterministic environment

---

### Active Phase CI Workflows

| Phase | Responsibility | CI Scope |
|------|----------------|---------|
| Phase 4 | Personalization | Determinism, semantic safety |
| Phase 4.5 | Localization | String integrity, token constraints |
| Phase 6 | Song Recommendation | Runtime selector & ranking |
| Phase 7 | Game Recommendation | Policy, ranking governance |

---

### Key Rule

> ❗ Each Phase CI must behave as if it is the only phase in the system.

---

## 2. Integration CI (Pipeline Validator)

Integration CI is the **only place where phases are combined**.

### Responsibilities

- ✅ Validate cross-phase compatibility
- ✅ Validate API + orchestrator wiring
- ✅ Validate import graph across phases
- ✅ Run integration tests only

---

### Environment

PYTHONPATH = Phase 4 + Phase 6 + Phase 7

---

### Constraints

Integration CI MUST NOT:
- ❌ run Phase-specific CI logic
- ❌ duplicate Phase tests
- ❌ mutate Phase environments

---

### Conceptual Role

Phase correctness  → Phase CI
System correctness → Integration CI

---

## 3. External CI Observability Layer

Located under:

ci/observability/

### Role

This layer provides:

- ✅ CI signal aggregation
- ✅ Phase-aware health tracking
- ✅ Alerting and dashboards

---

### Data Source: CI SUMMARY

Each CI workflow emits log-level signals:

CI SUMMARY: phase=<phase_id> status=<ok|FAIL>

---

### Aggregation Output

```
{
  "total": 4,
  "by_phase": {
    "phase4": { "status": "ok" },
    "phase6": { "status": "ok" },
    "phase7": { "status": "ok" },
    "integration": { "status": "ok" }
  },
  "by_status": {
    "ok": 4
  },
  "latest": {...}
}
```

---

### Alerting Rules

Fail CI when:

- Any phase fails:

```
any phase.status == FAIL
```

- Budget thresholds exceeded (optional)

---

### Design Principles

- ✅ Phase-agnostic
- ✅ Non-semantic (no gameplay logic)
- ✅ CI-only (never runtime)
- ✅ Deterministic

---

### Phase 5 Consideration (Important)

Phase 5 (Productionization / Learning):

- ✅ Has CI tests
- ❌ Does NOT have a standalone CI workflow

#### Why?

Because Phase 5 is:

- Offline (non-runtime)
- Data / model oriented
- Independent of API execution

---

Phase 5 CI covers:

- ✅ Training determinism
- ✅ Aggregation correctness
- ✅ Feature safety
- ✅ Evaluation metrics
- ✅ Regression guards

---

Enforcement rule

|❗ Phase 5 MUST NOT depend on Phase 6 runtime

---

### CI Isolation Model

#### Phase CI (strict isolation)

```
Phase 4 CI → Phase 4 only
Phase 6 CI → Phase 6 only
Phase 7 CI → Phase 7 only
```

---

#### Integration CI (controlled mixing)

```
Phase 4 + Phase 6 + Phase 7
```

---

#### Observability Layer

```
Consumes CI output
Does NOT run logic
```

---

### What This Architecture Prevents

✅ Cross-phase import leakage
✅ Non-deterministic test execution
✅ Hidden dependency chains
✅ CI environment pollution

---

### What This Architecture Enables

✅ Scalable phase system
✅ Fast debugging (localized failures)
✅ Reliable CI signals
✅ Structured observability
✅ Future Phase expansion (no refactor needed)

---

### Future Extensions

Possible improvements:

- ✅ CI dependency graph (Phase 6 → Phase 7 → integration)
- ✅ Dashboard UI for CI health
- ✅ Slack / webhook alerts
- ✅ Historical CI trend analysis
- ✅ Strict CI policies (e.g. forbid legacy imports)

---

### Summary

This CI system transforms the repository from:

```
ad-hoc testing
```

into:

```
a structured, phase-isolated, observability-driven system
```

---

Final Principle

| CI is not just testing — it is system governance




