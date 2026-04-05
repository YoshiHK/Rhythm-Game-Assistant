# CI — Continuous Invariants

This folder enforces **system invariants**, not model correctness.

CI exists to ensure **completed phases remain immutable**, while allowing
safe wiring, observability, and operational enforcement as the system scales.

---

## What CI protects

- **Phase boundaries**
  - No upstream semantic access
  - No cross‑phase leakage

- **Deterministic contracts**
  - Personalization output structure (Phase 4)
  - Localization and presentation invariants (Phase 4.5)

- **Localization safety (Phase 4.5)**
  - Per‑string token parity
  - Placeholder integrity
  - Word and token budgets
  - Waiver governance (global + per‑locale)
  - Waiver decay (`review_by`)

- **Log‑level contracts**
  - Stable, machine‑consumed CI output
  - Versioned summary lines

- **Operational readiness (Phase 6 wiring)**
  - Observability hooks
  - Alertable CI artifacts

---

## What CI does NOT do

- Run chart ingestion
- Execute Phase 1–3 pipelines
- Train or evaluate models
- Judge recommendation quality or gameplay semantics

CI is **non‑semantic by design**.

---

## CI SUMMARY contract (log‑level invariant)

Some CI checks (notably localization / token parity) emit a **single summary line**
at the end of execution.

This line is treated as a **machine‑consumed contract**, not a human‑only log.

CI SUMMARY: status=... base=... waived_total=... waived_by_locale=... per_locale_budget=... decay=... suggested_review_by=... reason=...

### Contract version

- **CI SUMMARY — v1**

This version is explicitly marked in code and protected by CI self‑tests.

---

## Log‑level contracts (versioned)

### Contract: CI SUMMARY — v1

**Applies to**
- Phase 4.5 localization checks

**Guarantees**
- Exactly **one physical line**
- Always emitted (PASS or FAIL)
- Space‑separated `key=value` tokens
- Stable field names and ordering within the version

**Required fields**
- `status` — `PASS | FAIL`
- `base` — resolved base locale
- `waived_total` — `<used>/<global_budget>`
- `waived_by_locale` — dict‑like representation
- `per_locale_budget` — dict‑like representation
- `decay` — decay policy flags
- `suggested_review_by` — ISO date (`YYYY-MM-DD`)
- `reason` — short failure or success reason

**Example**

CI SUMMARY: status=PASS base=en-US waived_total=1/5 waived_by_locale={'ja-JP': 1} per_locale_budget={'ja-JP': 2} decay=require_review_by:True,warn_before_days:7,fail_on_expired:True suggested_review_by=2026-05-05 reason=ok

### Stability rules

Any change to this format **must**:
1. Introduce a new contract version (e.g. `CI SUMMARY — v2`)
2. Update downstream consumers
3. Update CI self‑tests

Breaking this contract is treated as a **CI failure**.

---

## Contract enforcement via CI tests

The following test locks the CI SUMMARY contract:


CI/Phase_4_5/tests/test_token_parity_summary_ci.py

It enforces:
- Required fields and value shapes
- Exactly one summary line
- No embedded or escaped newlines
- No duplicated fragments

These tests are intentionally strict.

---

## Observability hooks (Phase 6 wiring)

CI provides **Phase‑6‑style observability** without modifying Phase 4.5 semantics.

### CI artifacts and alert gating

Some CI checks emit machine‑consumed summaries that are scraped into structured
artifacts under:

CI/artifacts/
├─ ci_summary_events.jsonl
└─ ci_summary_aggregate.json

These artifacts are derived from CI logs and are used for:

- Observability and trend inspection
- CI gating via alert rules
- Budget and invariant enforcement

An alert rule is provided:
scripts/observability/alert_ci_summary.py

This rule fails CI when:
- `latest.status == FAIL`
- Waiver budget is nearly exhausted (configurable thresholds)

This gate operates **only on log‑level contracts** (CI SUMMARY v1) and does not
introduce new gameplay or localization semantics.

---

## Design principle

> CI protects **contracts**, not behavior.

If CI fails here, it means:
- A completed‑phase invariant was violated, **or**
- A downstream consumer would break silently

Both are treated as failures by design.
