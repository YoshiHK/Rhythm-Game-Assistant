# CI — Continuous Invariants

This folder enforces **system invariants**, not model correctness.

CI exists to ensure **completed phases remain immutable**, and that downstream
systems can rely on stable contracts as the codebase evolves.

---

## What CI protects

- **Phase boundaries**
  - No upstream semantic access
  - No cross‑phase leakage

- **Deterministic contracts**
  - Personalization output structure
  - Localization invariants
  - Token and placeholder safety

- **Localization safety (Phase 4.5)**
  - Per‑string token parity
  - Waiver budgets (global + per‑locale)
  - Waiver decay (`review_by`)
  - Stable CI summary output

- **API surface stability**
  - Softr integration
  - Client‑side parsers
  - CI log consumers

---

## What CI does NOT do

- Run chart ingestion
- Execute Phase 1–3 pipelines
- Train or evaluate models
- Judge recommendation quality

CI is **non‑semantic by design**.

---

## CI SUMMARY contract (log‑level invariant)

Some CI checks (notably localization/token parity) emit a **single summary line**
at the end of execution:

CI SUMMARY: status=... base=... waived_total=... per_locale_budget=... suggested_review_by=... reason=...

### Why this matters

- Downstream CI parsers rely on a **single‑line, key=value format**
- Dashboards and alerts depend on **stable field names**
- Accidental formatting changes must fail CI immediately

---

## Log‑level contracts (versioned)

Some CI outputs are treated as **machine‑consumed contracts**, not human‑only logs.
These contracts are versioned and protected by CI self‑tests.

Breaking a log‑level contract is considered a **CI failure**, even if program behavior
is otherwise correct.

### Contract: CI SUMMARY — v1

**Applies to**
- Localization / token parity checks (Phase 4.5)

**Emitted as**
- Exactly **one physical log line**
- Prefix: `CI SUMMARY:`
- Space‑separated `key=value` pairs

**Current required fields**
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

### Stability guarantees

- The summary is always emitted (PASS or FAIL)
- The summary is always **one line**
- Field names are stable within a contract version
- Ordering is stable within a version

Any change to this format **must**:
1. Introduce a new contract version (e.g. `CI SUMMARY — v2`)
2. Update downstream consumers
3. Update CI self‑tests accordingly

---

## Contract enforcement via CI tests

The following tests lock the CI SUMMARY contract:


CI/tests/test_token_parity_summary_ci.py

These tests enforce:
- Presence of required fields
- Exactly one summary line
- No embedded or escaped newlines
- Basic value shape validation (e.g. date formats)

They are intentionally strict to prevent silent downstream breakage.
---

## Summary contract self‑tests

The following self‑tests **lock the CI SUMMARY format**:


CI/tests/test_token_parity_summary_ci.py

These tests assert:

1. Exactly **one** `CI SUMMARY:` line is emitted
2. Required `key=value` fields are present
3. The summary is a **single physical line**
   - No embedded newlines
   - No duplicated fragments

These tests are **intentionally strict** and should only change if
downstream consumers are updated in lockstep.

---

## Design principle

> CI protects **contracts**, not behavior.

If a change breaks CI here, it means:
- A completed phase invariant was violated, **or**
- A downstream consumer would break silently

Both are treated as failures by design.
