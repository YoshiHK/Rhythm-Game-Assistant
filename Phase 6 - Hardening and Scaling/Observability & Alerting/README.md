# Phase 6 Observability

Observability in Phase 6 is **strictly non-semantic**.

It exists to:
- measure system health,
- detect anomalies,
- and surface operational risk.

It does NOT:
- alter execution,
- block routing,
- or reinterpret analysis results.

---

## Observability Flow

1. **Observers**
   - Read system artifacts (e.g. scan_state)
   - Produce HealthMetrics

2. **SLO Router**
   - Evaluates HealthMetrics against declared objectives
   - Produces SLOResult

3. **Alert Router**
   - Routes alerts based on SLOResult
   - Does not deliver notifications directly

---

## Components

- **scan_observer.py**
  Observes scan-state freshness and coverage.

- **health_metrics.py**
  Canonical schema for health signals.

- **slo_router.py**
  Evaluates SLO compliance.

- **alert_router.py**
  Determines alert escalation.

---

Observability observes and escalates.
It never decides semantics.