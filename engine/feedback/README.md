## Engine — Feedback System

### Purpose

The Feedback System defines how runtime feedback signals are:

- interpreted
- structured
- traced
- connected to offline learning (Phase 5)

This layer exists to transform **raw runtime signals into structured reasoning signals**
without introducing ground truth or learning logic.

---

### Core Concept

```
feedback_event (raw reality)
→ interpreter (machine hypothesis)
→ feedback_reason
→ bridge (Phase 5 alignment)
```

This layer answers:

✅ “What likely happened?”  
NOT:

❌ “Is it correct?”  
❌ “How should the model learn?”  

---

## 🔷 System Role (CRITICAL)

| Layer | Responsibility |
|------|----------------|
| engine/feedback | interpret runtime signals |
| Phase 5 | learn from signals |
| curator | define truth |

---

### Pipeline Position

```
Phase 6 runtime
↓
feedback_event (raw)
↓
engine/feedback
- taxonomy
- interpreter
- diagnostics
↓
interpretation_bridge
↓
Phase 5 aggregation
```

---

## 🔷 Submodules

---

### 1. taxonomy/

Defines the **shared reasoning language**.

- reason_codes (canonical)
- category / layer / cause_type
- semantic structure

This is the **language used across**:

- interpreter (machine)
- curator (human)
- dataset (training)

---

### 2. interpreter/

Converts runtime signals into structured reasoning.

Input:

```
feedback_event
system_context
payload
```

Output:

```
feedback_reason:

primary_reason
reason_codes
confidence
```

Constraints:

- deterministic
- no learning
- no I/O
- no side effects

---

### 3. bridge/

Connects runtime interpretation to Phase 5.

Responsibilities:

- attach derived reasoning to events
- preserve raw feedback
- avoid semantic mutation

Key principle:

```
raw_event ≠ derived_reason
```

Derived fields MUST remain separate.

---

### 4. diagnostics/

Provides debugging and tracing tools.

Includes:

- reason_debugger
  - explain reasoning decisions
  - compare model vs curator

- trace_utils
  - end-to-end pipeline trace
  - lineage reconstruction

This layer is:

✅ diagnostic only  
❌ not part of decision logic  

---

## 🔷 Data Contracts

---

### Input

Raw feedback events:

```
feedback_events.schema.json
```

Characteristics:

- append-only
- weak / noisy signals
- no interpretation

---

### Output

Interpreted signals:

```
feedback_reason:
primary_reason
reason_codes
confidence
```

PLUS:

```
enriched event:
raw_event
derived_reason
```

---

## 🔷 Design Principles

---

### 1. No Semantic Authority

This layer:

- does NOT define correctness
- does NOT assign labels
- does NOT override human judgment

---

### 2. Deterministic

Same input:

```
feedback_event → identical reasoning output
```

---

### 3. Separation of Concerns

| Concept | Owner |
|--------|------|
| reality | feedback_event |
| hypothesis | interpreter |
| truth | curator |
| learning | Phase 5 |

---

### 4. Non-Invasive

- never mutate raw feedback
- never inject semantics into upstream layers
- only attach derived signals

---

## 🔷 Relationship to Phase 5

---

The bridge enables:

```
feedback_event
→ derived_reason (engine)
→ aggregation (Phase 5)
→ curator_label
→ training_dataset
```

Important:

- engine output = hypothesis
- Phase 5 determines learning

---

## 🔷 What This Layer Does NOT Do

---

- ❌ Does NOT train models
- ❌ Does NOT produce datasets
- ❌ Does NOT evaluate performance
- ❌ Does NOT control runtime behavior
- ❌ Does NOT define truth

---

## 🔷 Design Intent

This layer exists to:

✅ understand runtime behavior  
✅ structure noisy signals  
✅ enable debugging  
✅ bridge runtime → learning  

WITHOUT:

❌ polluting learning data  
❌ introducing semantic bias  
❌ breaking system determinism  

---

## 🔥 Key Insight

```
feedback_event = reality
feedback_reason = hypothesis
curator_label = truth
```

---

## ✅ Summary

The Feedback System is:

- deterministic ✅  
- non-semantic ✅  
- runtime-adjacent ✅  
- learning-supporting ✅  

---

**Engine/feedback understands reality — it never defines it.**
