## Curator Queue (Phase 5)

The Curator Queue defines how aggregated feedback is prepared
for human review.

### Purpose

- Group related feedback events by provenance_id.
- Present curators with coherent review units.
- Reduce noise without introducing judgment.

### Queue Units

Each queue item contains:
- One provenance_id
- Associated tips and outputs
- All related feedback events within a time window

### Non‑Goals

- The queue does NOT prioritize correctness.
- The queue does NOT approve or reject outputs.
- The queue does NOT enforce policy.

### Invariants

- Queue ordering does not imply severity.
- Absence of feedback does not imply correctness.
- Curators are free to skip, defer, or escalate items.

The Curator Queue exists to **support human judgment**, not replace it.