## Phase 5 – Observability & Experimentation Layer

This layer defines how the system **measures effectiveness**
and **runs controlled experiments** during Phase 5 (Productionization).

---

## Purpose

- Measure effectiveness of tips and recommendations
- Enable controlled experimentation without semantic drift
- Provide signals for offline learning and Phase 7 expansion

---

## What This Layer Does

- Collect non-semantic telemetry
- Define canonical evaluation metrics
- Run presentation-only experiments
- Support analysis and human review

---

## What This Layer Does NOT Do

- It does NOT change runtime behavior
- It does NOT modify semantic outputs
- It does NOT trigger enforcement actions
- It does NOT replace curator judgment

---

## Relationship to Other Phases

- **Upstream**  
  Consumes runtime outputs from Phases 1–4.5,
  executed under Phase 6 governance.

- **Downstream**  
  Feeds Phase 5 Curator Gold & Labeling and offline retraining.

Observability informs learning; it never controls execution.

---

## Invariants

- All telemetry is explainable and auditable
- All experiments are reversible
- All semantics remain fixed
- Phase 6 boundaries are never bypassed

---

Phase 5 Observability exists to **learn safely from reality**,
not to steer it in real time.
