# Phase 6 CI — Song Recommendation System

## 🎯 Purpose

This CI suite validates the **runtime safety, determinism, and contract integrity**
of the Phase 6 Song Recommendation system.

Phase 6 is the **ONLY runtime gatekeeper**.  
This CI ensures:

- Deterministic behavior across all inputs
- Multi-game safety (no hardcoded assumptions)
- Contract compliance (request / response / persistence)
- Selector correctness (tier isolation, exclusion, fallback logic)
- Schema integrity (JSON + cross references)

---

## 🧠 CI Philosophy

This CI suite is **NOT evaluating recommendation quality**.

✅ It checks:
- Structure
- Determinism
- Safety guarantees
- Contract shape
- Invariants

❌ It does NOT check:
- Ranking quality
- Personalization correctness
- Game-specific tuning

---

## 🧱 Test Layers

---

### ✅ 1️. Capability Layer

Validates **multi-game configuration correctness**

Tests:
- game capability resolver
- ladder invariants
- fixture coverage

Guarantees:
- tier ordering is valid
- completion ladder is consistent
- all fixtures load correctly

---

### ✅ 2️. Coordinator Layer

Validates **core orchestration logic**

Flow:

normalized request
→ game capability
→ target generation
→ selector

Guarantees:
- deterministic outputs
- no randomness in recommendation
- exclusions respected

---

### 3️. Contract Layer

Validates **input/output contracts**

#### Request Normalizer
- schema enforcement
- multi-game safe structure
- invalid inputs rejected

#### Response Shaper
- JSON serializable output
- stable recommendation set id
- correct response structure

---

### 4️. Persistence Layer

Validates **rotation + save/refresh logic**

Guarantees:
- `refresh` → no persistence
- `save` → deterministic persistence plan
- bookmarked items are never deleted
- deletion order is stable

---

### 5. Selector Layer

Validates **catalog selection logic**

Guarantees:
- deterministic selection
- exclusion respected
- no cross-tier leakage
- fallback (window widening) is deterministic

---

### 6️. Schema Layer

Validates **schema integrity**

Guarantees:
- all JSON schemas parse
- cross-reference consistency
- no broken schema links

---

## 📁 Directory Structure

```
tests/
├── capability/
│   ├── test_game_capability_resolver.py
│   ├── test_game_capability_ladder_invariants.py
│   ├── test_game_capability_fixtures.py
│   └── test_all_games_capability_coverage.py
│
├── coordinator/
│   ├── test_coordinator_determinism.py
│   └── test_song_rec_coordinator_integration.py
│
├── contract/
│   ├── test_request_normalizer_contract.py
│   └── test_response_shaper_contract.py
│
├── persistence/
│   └── test_rotation_policy.py
│
├── selector/
│   ├── test_selector_determinism.py
│   ├── test_selector_exclusions.py
│   ├── test_selector_multi_tier.py
│   └── test_selector_window_widening.py
│
└── schemas/
    ├── test_schema_json_parseability.py
    └── test_schema_cross_reference.py
```

---

## ⚙️ Running Tests

### ✅ Local run

```
export PYTHONPATH="$PYTHONPATH:$(pwd)/Phase 6 - Hardening and Scaling"
pytest "Phase 6 - Hardening and Scaling/song_recommendations/tests" -q -rA
```

---

### ✅ GitHub Actions
Phase 6 CI is executed inside Phase 7 CI workflow:

```
.github/workflows/phase7_ci.yml
```

---

## 🔒 CI Guarantees (Critical)

This CI enforces:

- ✅ Deterministic recommendation system
- ✅ No hidden randomness
- ✅ No semantic leakage into Phase 6
- ✅ Multi-game compatibility
- ✅ Stable contract boundaries

---

## 🚫 Non-Goals
This CI will NOT:

- rank songs “correctly”
- evaluate recommendation usefulness
- tune player experience

Those belong to:

```
Phase 5 (learning / evaluation)
Phase 4 (personalization)
```

---

## 🧩 Design Principles

🔹 1. Data-driven
All tests operate on:

- fixtures
- schemas
- structured inputs

No hardcoded game logic.

---

🔹 2. Determinism-first
Every test enforces:

```
same input → same output
```

---

🔹 3. Isolation-friendly
Each layer can be tested independently:

- selector without coordinator
- contract without runtime
- schema without execution

---

🔹 4. CI-safe (no side effects)

- no DB
- no network
- no randomness
- no external dependency

---

✅ Final State
When all tests pass:

```
✅ Phase 6 routing is stable
✅ Song recommendation system is safely deployable
✅ Integration with Phase 5 + Phase 7 is contract-safe
```


---

## 🔭 Future Evolution (Optional)

Potential next steps:

- Integration tests via Phase 6 router (mode-level verification)
- Replay-based validation using observability logs
- Stronger schema validation (beyond JSON parsing)
- Performance / latency constraints
- CI-level monitoring hooks

---

## 🔥 Key Takeaway

> Phase 6 CI ensures the system is **safe, deterministic, and structurally correct**  
> — not that it is “smart”.

---