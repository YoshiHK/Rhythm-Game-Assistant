# CI Observability & Alerting

**Status:** Design‑Locked ✅  
**Scope:** CI‑only, Phase‑agnostic  
**Execution Context:** Non‑runtime

---

## 1. Purpose

This directory defines the **CI observability and alerting layer**.

It consumes **CI SUMMARY** signals emitted by individual Phase CI layers
(Phase 4, Phase 4.5, Phase 7, etc.), and transforms them into:

- structured artifacts,
- dashboards inputs,
- alerting decisions.

This layer is **explicitly NOT part of any single Phase CI**.

---

## 2. What This Layer IS

CI Observability:

- ✅ consumes log‑level CI SUMMARY signals,
- ✅ aggregates CI health across runs and phases,
- ✅ enforces alerting thresholds on governance signals,
- ✅ produces machine‑consumable artifacts.

---

## 3. What This Layer is NOT

CI Observability does **NOT**:

- ❌ participate in runtime execution,
- ❌ evaluate gameplay, model, or localization semantics,
- ❌ mutate or gate Phase logic directly,
- ❌ replace Phase‑level CI checks or tests,
- ❌ infer business or product quality.

This layer operates strictly on **log‑level contracts**.

---

## 4. CI SUMMARY Contract

This layer relies on the **CI SUMMARY v1** contract:

CI SUMMARY: key=value key=value ...

Properties:
- single‑line only,
- space‑delimited `key=value` tokens,
- no embedded newlines,
- values must not contain spaces.

Each Phase CI is responsible for emitting valid CI SUMMARY lines.
This layer only **consumes** them.

---

## 5. Components

ci/observability/
├─ README.md
├─ init.py
├─ scrape_ci_summaries.py
├─ alert_ci_summary.py
└─ artifacts/        # generated only (never committed)

### `scrape_ci_summaries.py`
- Scans CI logs for `CI SUMMARY:` lines
- Emits:
  - `ci_summary_events.jsonl`
  - `ci_summary_aggregate.json`
- Pure observability wiring (no semantics)

### `alert_ci_summary.py`
- Consumes `ci_summary_aggregate.json`
- Fails CI when:
  - latest CI status == FAIL
  - waiver budgets approach exhaustion
- Non‑semantic alert rule

---

## 6. Relationship to Phase CI Layers

| Layer | Responsibility |
|---|---|
| Phase 4 CI | Personalization invariants |
| Phase 4.5 CI | Localization invariants |
| Phase 7 CI | Recommendation invariants |
| **CI Observability** | Cross‑Phase signal aggregation |

This layer **never replaces** Phase CI.
It only aggregates and alerts.

---

## 7. Generated Artifacts

Artifacts under `ci/observability/artifacts/` are:

- ✅ generated during CI runs,
- ✅ machine‑consumable,
- ❌ never committed to source control.

---

## 8. Design‑Locked Statement

As of this revision:

> **CI Observability & Alerting is Design‑Locked ✅**

Future changes must:
- preserve the CI SUMMARY v1 contract,
- remain Phase‑agnostic,
- remain non‑runtime and non‑semantic.

If you are unsure whether logic belongs here,
it probably belongs in a Phase CI instead.