# CI Architecture Overview

**Status:** Design‑Locked ✅  
**Scope:** Repository‑level CI structure  
**Audience:** Maintainers, reviewers, future contributors

---

## 1. Purpose

This directory defines the **repository‑level CI architecture**.

It exists to clarify:
- where CI logic lives,
- what belongs to a Phase,
- what must remain Phase‑agnostic,
- and why this repository intentionally avoids a monolithic `ci/` folder.

This file is **architectural documentation**, not a how‑to guide.

---

## 2. Core Principle

> **All Phase‑specific CI lives inside its Phase.  
> The repo‑level `ci/` directory contains only Phase‑agnostic CI infrastructure.**

This rule is non‑negotiable.

---

## 3. Phase‑Specific CI (Where It Lives)

Each Phase owns its own CI governance layer:

| Phase | CI Location | Responsibility |
|---|---|---|
| Phase 4 | `Phase_4_Personalization/ci/` | Personalization invariants (determinism, safety, explainability) |
| Phase 4.5 | `Phase_4.5_Localization/ci/` | Localization structure, parity, token budgets |
| Phase 7 | `Phase_7_Games_Recommendations/ci/phase7/` | Recommendation policies, ranking, contracts |

These CI layers:
- understand Phase semantics,
- directly constrain Phase runtime,
- are authoritative for that Phase only.

They **must not** be moved to repo‑level `ci/`.

---

## 4. Repo‑Level CI (What Belongs Here)

The repo‑level `ci/` directory contains **only Phase‑agnostic CI infrastructure**.

Current structure:

ci/
└─ observability/
   ├─ scrape_ci_summaries.py
   ├─ alert_ci_summary.py
   ├─ README.md
   └─ artifacts/        # generated only (never committed)

This layer:
- does NOT import Phase runtime,
- does NOT evaluate gameplay, localization, or recommendation logic,
- operates strictly on **CI signals**, not product semantics.

---

## 5. CI Observability Layer

The `ci/observability/` layer is responsible for:

- consuming **CI SUMMARY v1** log‑level signals,
- aggregating CI health across runs and Phases,
- producing machine‑consumable artifacts,
- enforcing alerting thresholds on CI governance signals.

It is a **signal consumer**, not a CI gate for any single Phase.

---

## 6. CI SUMMARY Contract

All Phase CI layers may emit log lines following the contract:

CI SUMMARY: key=value key=value ...

Properties:
- single‑line only,
- space‑delimited `key=value` tokens,
- no embedded newlines,
- values must not contain spaces.

Phase CI layers **emit** CI SUMMARY signals.  
Repo‑level CI **consumes** them.

---

## 7. What Must NOT Appear Here

The following are explicitly forbidden at repo‑level `ci/`:

- ❌ Phase‑specific checks or tests
- ❌ Runtime logic
- ❌ Feature heuristics
- ❌ Product semantics
- ❌ Localization or recommendation rules

If CI logic understands a Phase’s semantics, it belongs **inside that Phase**.

---

## 8. Why This Structure Is Intentional

This repository intentionally avoids a monolithic CI folder.

Benefits:
- clear ownership boundaries,
- reduced accidental coupling,
- safer Phase evolution,
- predictable CI behavior,
- easier long‑term maintenance.

This structure reflects a **platform‑level CI architecture**, not a feature‑level one.

---

## 9. Design‑Locked Statement

As of this revision:

> **The repository‑level CI architecture is Design‑Locked ✅**

Future CI additions at repo‑level must be:
- Phase‑agnostic,
- non‑runtime,
- signal‑oriented,
- explicitly documented.

If you are unsure whether CI logic belongs here,
it almost certainly belongs inside a Phase instead.