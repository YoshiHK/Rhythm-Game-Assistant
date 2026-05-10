# Phase 4.5 CI — Localization Governance

**Status:** Design‑Locked ✅  
**Scope:** Phase 4.5 (Localization) only  
**Execution Context:** CI‑only (non‑runtime)

---

## 1. Purpose

This directory defines the **CI governance layer** for Phase 4.5 (Localization).

Its purpose is to:
- enforce structural and policy contracts for localization,
- prevent runtime breakage caused by translation drift,
- provide deterministic, auditable failure signals.

This CI layer is **not** part of the runtime execution path.

---

## 2. What This CI Layer IS

Phase 4.5 CI:

- ✅ validates localization structure and contracts,
- ✅ enforces placeholder and token integrity,
- ✅ enforces narrative word budgets,
- ✅ supports explicit, auditable waivers with decay,
- ✅ emits a stable CI SUMMARY line for observability.

---

## 3. What This CI Layer is NOT

Phase 4.5 CI **does NOT**:

- ❌ evaluate translation quality or style,
- ❌ judge linguistic correctness,
- ❌ execute runtime localization logic,
- ❌ gate Phase 6 runtime execution,
- ❌ invoke Phase 7 logic,
- ❌ modify localization or narrative content.

---

## 4. CI Structure

ci/
├─ run_all_localization_checks.py   # CI runner (checks‑only)
│
├─ check_localization.py            # Localization directory integrity
├─ check_template_parity.py         # Narrative v3 template parity + schema
├─ check_placeholder_integrity.py   # Placeholder preservation across locales
│
├─ check_token_parity_per_string.py # Per‑string token parity + waivers + summary
├─ check_token_counts.py            # Aggregate token count consistency
├─ check_word_budget.py             # Narrative v3 word/unit budget enforcement
│
├─ token_parity_waivers.json        # CI governance data (waivers, budgets, decay)
│
└─ README.md                        # This document


- Executes Phase 4.5 checks **only**
- Runs checks in deterministic order
- Stops on first failure
- Produces a single PASS/FAIL exit code

This runner:
- ✅ is safe to run locally or in CI,
- ❌ must not be used as a runtime gate,
- ❌ must not invoke Phase 7 logic.

---

## 7. Token Parity Waivers

`token_parity_waivers.json` defines **explicit exceptions** to token parity rules.

Properties:
- Waivers are **auditable**
- Budgets exist at global and per‑locale levels
- Waivers **decay** via `review_by` dates
- Expired or invalid waivers fail CI

This file is **governance data**, not versioned configuration.

---

## 8. CI SUMMARY Output (Observability)

Some checks (notably token parity) emit a **single‑line CI SUMMARY**:
CI SUMMARY: 
token_parity_per_string status=PASS 
mismatches=0 
waivers_used=0 
invalid_waivers=0

Guarantees:
- Exactly one physical line
- Stable, machine‑consumable format
- No embedded or escaped newlines

CI SUMMARY:
- ✅ may be scraped for observability,
- ❌ must not be used to gate runtime behavior.

---

## 9. Relationship to Other Phases

- Phase 4.5 CI constrains **localization only**
- Phase 4 (Personalization) CI is separate
- Phase 7 CI is separate
- Phase 6 may observe CI results, but does not depend on them

---

## 10. Design Principles (Non‑Negotiable)

- ✅ Deterministic
- ✅ CI‑only
- ✅ No runtime mutation
- ✅ No versioned contracts
- ✅ Fail loud, fail early
- ✅ Clear ownership and boundaries

---

## 11. Summary

Phase 4.5 CI exists to ensure that **localization remains safe, consistent, and operable at scale** without ever becoming part of runtime logic.

If this CI fails, the fix is always:
- adjust localization artifacts, or
- update explicit waivers with review dates.

It is never:
- a runtime hotfix,
- a semantic override,
- or a Phase 6 decision.