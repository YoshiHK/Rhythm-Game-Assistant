# Phase 5 — Song Recommendation Orchestrator Helper (Utils)

## Purpose

This helper runs the **offline learning dataflow** for Song Recommendations:

feedback → aggregation → features → training → evaluation → artifacts

It exists for:
- reproducible offline runs
- CI/QA checks
- generating deployment-safe artifacts

Phase 5 routing is explicitly **NOT a runtime decision engine**. [1](https://onedrive.live.com/?id=1e428acc-4a68-416e-9d6d-c8692b153f2c&cid=d5d62a1ef303ba22&web=1)

---

## Non‑Negotiable Boundaries

This helper MUST:
- run offline only (Phase 5)
- be deterministic and auditable
- never modify completed phases
- output only deployment artifacts (no runtime coupling) [2](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!sb2f7c783c4344d509f43af7f127b6c89)

This helper MUST NOT:
- be imported by Phase 6 runtime
- consume tips/taxonomy/severity/narrative content
- create any runtime learning loop
- load artifacts dynamically in runtime (deployment only) [2](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!sb2f7c783c4344d509f43af7f127b6c89)

---

## Inputs

- A list of feedback event dicts emitted by Phase 6 Song Recommendation feedback layer.
- Optional: events loaded from JSON / JSONL files (offline convenience).

---

## Outputs

Artifacts written to an artifact directory:
- song_selector_params.json
- song_selector_training_report.json
- song_selector_evaluation_report.json
- optional baseline snapshot (for future deltas)

Artifacts are intended for **deployment only**. [2](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!sb2f7c783c4344d509f43af7f127b6c89)

---

## Typical Usage (Offline)

1) Load feedback events (JSONL/JSON array)
2) Run pipeline
3) Inspect evaluation guards
4) Deploy static selector params if approved

This helper supports baseline comparisons and optional baseline snapshot updates.

---

## Design Intent

This helper makes Phase 5 Song Recommendation learning:
✅ repeatable  
✅ reviewable  
✅ reversible  

without making Phase 6 runtime unsafe.
