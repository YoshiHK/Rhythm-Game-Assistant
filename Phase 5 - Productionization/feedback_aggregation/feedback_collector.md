## Feedback Collector (Phase 5)

The Feedback Collector captures **raw feedback signals** produced during runtime
execution.

### Responsibilities

- Collect player and system feedback events.
- Preserve full provenance linkage.
- Store feedback in append-only form.
- Avoid interpretation or scoring.

### What Feedback Is

- Observable reactions (completion, dismissal, retries)
- System-level observations (timeouts, fallback usage)

### What Feedback Is NOT

- A correctness judgment
- A quality score
- A training label
- A runtime control signal

### Design Invariants

- Feedback collection MUST NOT affect runtime execution.
- Feedback is immutable once written.
- Feedback semantics are intentionally weak and noisy.

Feedback Collector exists to **preserve signal**, not to decide meaning.