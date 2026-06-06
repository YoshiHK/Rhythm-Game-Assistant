### Practice Mapping

Defines how recommendations map into gameplay/practice flows.

---

### Purpose

- Connect recommendation outputs to gameplay elements
- Align system decisions with actionable practice steps

---

### Mapping Inputs

- recommendation_response
- contextual metadata (rank, difficulty)

---

### Mapping Outputs

- practice segments
- target actions (retry, replay, focus area)

---

### Mapping Rules

Mappings MUST:

- preserve original recommendation intent
- maintain alignment with reason_codes
- be deterministic

Mappings MUST NOT:

- ❌ introduce new semantic interpretations
- ❌ alter recommendation ranking
- ❌ inject subjective scoring

---

### Traceability (NEW)

Each mapping MUST link:

- item_id → gameplay context
- provenance_id → session usage

---

### Integration with Telemetry (NEW)

Mappings must support:

- replay tracking
- retry actions
- completion signals

---

Practice Mapping exists to:
> translate recommendations into playable actions
