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
