### Feedback Collector (Phase 5)

The Feedback Collector captures **raw, uninterpreted feedback signals**
from runtime execution.

---

### Responsibilities

- Collect player and system feedback events
- Enforce feedback_events.schema.json contract
- Preserve full provenance linkage
- Record runtime context (player, session, recommendation, environment)
- Store feedback in append-only form

---

### What Feedback IS

- Observable behavior:
  - completion
  - dismissal
  - retry patterns

- System observations:
  - fallback usage
  - degraded mode
  - execution failures

---

### What Feedback IS NOT

- ❌ A correctness judgment
- ❌ A quality score
- ❌ A training label
- ❌ A semantic interpretation
- ❌ A runtime control signal

---

### Data Contract (NEW)

Each event MUST conform to:
- feedback_events.schema.json

Specifically MUST include:
- event_id
- provenance_id
- event_type
- source_type
- timestamp
- payload

---

### Context Requirements (NEW)

Collector MUST preserve:
- player_id / session_id
- recommendation context (song_id, rank, set_id)
- system context (fallback, errors)
- experiment metadata (if present)

---

### Design Invariants

- Collection MUST NOT affect runtime execution
- Feedback is immutable once written
- Feedback is append-only
- Feedback remains weak and noisy by design

---

Feedback Collector exists to:
> preserve signal, not decide meaning