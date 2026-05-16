# Phase 4.5 CI — Localization Governance

**Status:** Design‑Locked ✅  
**Scope:** Phase 4.5 (Localization) only  
**Execution Context:** CI‑only (non‑runtime)

---

# 1. Purpose

This directory defines the **CI governance layer** for Phase 4.5 (Localization).

Its purpose is to:

- ✅ enforce structural and policy contracts for localization
- ✅ prevent runtime breakage caused by translation drift
- ✅ provide deterministic, auditable failure signals

This CI layer is **strictly non-runtime** and MUST NOT influence execution.

---

# 2. What This CI Layer IS

Phase 4.5 CI:

- ✅ validates localization structure and contracts  
- ✅ enforces template parity across locales  
- ✅ enforces placeholder integrity  
- ✅ ensures taxonomy ↔ registry alignment  
- ✅ ensures debug configuration consistency  
- ✅ enforces word/token budget constraints  
- ✅ emits deterministic CI SUMMARY signals  

---

# 3. What This CI Layer is NOT

Phase 4.5 CI **does NOT**:

- ❌ evaluate translation quality or fluency  
- ❌ judge linguistic correctness  
- ❌ execute runtime localization logic  
- ❌ gate Phase 6 runtime execution  
- ❌ introduce or modify semantics  
- ❌ auto-fix localization errors  

---

# 4. CI Architecture

ci/
├─ run_all_localization_checks.py          # CI runner (deterministic, checks-only)
│
├─ checks/
│  ├─ taxonomy_validator.py                # Taxonomy docs ↔ registry alignment
│  ├─ check_pack_integrity.py              # Locale pack completeness + schema sanity
│  ├─ check_localization.py                # translations/ structural integrity
│  ├─ check_template_parity.py             # template file-set parity + schema sanity
│  ├─ check_placeholder_integrity.py       # placeholder preservation across locales
│  ├─ check_debug_consistency.py           # debug.json identical across locales
│  ├─ check_token_counts.py                # aggregate token count consistency
│  ├─ check_token_parity_per_string.py     # per-string token parity + waivers + CI SUMMARY
│  └─ check_word_budget.py                 # per-variant word/unit budget enforcement
│
├─ data/
│  └─ token_parity_waivers.json            # waivers, budgets, decay (CI-only)
│
├─ observability/
│  └─ OBSERVABILITY_SNIPPET.md
│
├─ tests/
│  ├─ test_pseudo_validation_rules.py
│  └─ test_token_parity_summary.py
│
└─ test_token_parity_summary.py         # locks CI SUMMARY format (meta-CI)

Runner behavior:
- Executes Phase 4.5 checks **only**
- Runs checks in deterministic order
- Stops on first failure
- Produces a single PASS/FAIL exit code
- CI failures block merges, not runtime execution

---

# 5. Deterministic Execution Order (CRITICAL)

Checks MUST run in the following order:

### 🔹 Stage 1 — Contract Layer
- taxonomy_validator.py
- check_pack_integrity.py

✅ Validate global correctness before file-level checks

---

### 🔹 Stage 2 — Structure Layer
- check_localization.py
- check_template_parity.py

✅ Ensure file completeness and schema validity

---

### 🔹 Stage 3 — Integrity Layer
- check_placeholder_integrity.py
- check_debug_consistency.py

✅ Prevent runtime-breaking drift

---

### 🔹 Stage 4 — Quantitative Constraints
- check_token_counts.py
- check_token_parity_per_string.py
- check_word_budget.py

✅ Enforce presentation consistency and budgets

---

# 6. Key Invariants

### 🔒 Template Parity

All templates MUST exist in all locales.

---

### 🔒 Placeholder Integrity

- Placeholder sets MUST match across all locales
- No additions / removals allowed

---

### 🔒 Taxonomy Alignment

- Every template_id MUST exist in one taxonomy
- No orphan or duplicate mappings allowed

---

### 🔒 Debug Consistency

> ✅ debug.json MUST be identical across ALL locales

This prevents:
- routing divergence
- inconsistent tracing
- non-deterministic debug output

---

# 7. Token Parity Waivers

`data/token_parity_waivers.json` defines **explicit exceptions**.

Properties:

- ✅ auditable
- ✅ time-bounded (review_by)
- ✅ budget-constrained
- ❌ expired waivers FAIL CI

---

# 8. CI SUMMARY Output

CI SUMMARY: = ...
Guarantees:

- ✅ single line only
- ✅ stable format
- ✅ machine-consumable

---

# 9. Failure Model

- ❌ CI stops at first failure
- ✅ Errors MUST be fixed in localization layer
- ❌ Runtime MUST NOT compensate

---

# 10. Relationship to Other Phases

- Phase 4.5 CI governs **localization only**
- Phase 4 CI governs personalization
- Phase 7 CI governs recommendation
- Phase 6 observes, but does NOT depend on CI

---

# 11. Design Principles

- ✅ Deterministic
- ✅ CI-only enforcement
- ✅ Fail fast
- ✅ No runtime coupling
- ✅ Separation of concerns

---

# ✅ Final Rule

> 🔒 If CI fails, the system is NOT safe to ship.

---

# ✅ Summary

Phase 4.5 CI ensures:

- stable localization structure
- cross-locale consistency
- zero semantic drift
- fully deterministic behavior

It is the **final safety gate** before localization reaches runtime.