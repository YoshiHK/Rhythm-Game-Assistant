## Recommendation Rationale Mapping (Phase 5)

Rationale Mapping defines how internal recommendation signals
are translated into **human-readable explanations**.

### Responsibilities

- Convert model outputs into clear rationales
- Preserve alignment with generated tips and elements
- Avoid exposing internal scores or weights

### Constraints

- Mapping MUST NOT introduce new reasoning
- Mapping MUST NOT reinterpret model intent
- Mapping MUST remain consistent across versions

### Examples

- “This song helps you practice alternating rhythms”
- “Recommended because it targets your recent timing issues”

Rationales explain **why something was suggested**,
not **how the model works**.
