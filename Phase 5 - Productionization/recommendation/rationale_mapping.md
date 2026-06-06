### Rationale Mapping

Defines how structured reason codes are translated into user-facing explanations.

---

### Purpose

- Convert machine reasoning into human-readable explanations
- Preserve semantic meaning across transformation
- Enable consistent explanation across UI contexts

---

### Inputs

- reason_codes
- primary_reason
- taxonomy metadata

---

### Output

- human-readable rationale text
- localization-ready strings

---

### Mapping Rules (UPDATED)

#### 1. Deterministic Mapping

Each reason_code MUST map to:

- predefined explanation template
- localization-ready string

---

#### 2. No Semantic Drift

Mapping MUST NOT:

- ❌ change meaning of reason_codes
- ❌ introduce new reasoning
- ❌ remove critical explanation elements

---

#### 3. Structure Preservation (NEW)

Mapping MUST preserve:

- primary_reason
- reason_codes
- ordering of importance

---

#### 4. UI Independence (NEW)

Mapping must:

- support multiple UI formats
- separate:
  - content (meaning)
  - format (presentation)

---

### Example

```
reason_code: SELECTOR_FALLBACK_USED
→ template:
"This recommendation was generated using a fallback strategy."
→ localized:
"此推薦是基於備用策略生成"
```

---

### Relationship to Evaluation (NEW)

Reason mapping MUST:

- align with evaluate_reason_alignment
- allow reverse-check:
  text → reason_code consistency

---

### Invariants

- Mapping is reversible at semantic level
- No hidden logic or thresholds
- All explanation is traceable to taxonomy

---

Rationale mapping exists to:
> translate meaning without changing it
