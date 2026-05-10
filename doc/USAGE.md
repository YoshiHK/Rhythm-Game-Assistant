# Usage Guide

This document describes **supported entry points and integration patterns**
for the current system architecture.

It does NOT describe internal phase logic.

---

## 1. Batch & CLI Usage (Phase 3)

The Unified Ingestion Manager (UMI) provides a CLI surface for batch ingestion.

Typical usage includes:
- `--source` directory of raw chart files
- `--db` path to Song Database Excel (unless `--dry-run`)
- `--dry-run` run without persistence
- `--game` restrict run to a single enabled `game_id`
- `--json` emit structured run report
- `--tips-mode` `production` or `debug`

UMI:
- resolves adapters and validators,
- invokes Phase 1–2 pipelines,
- emits canonical artifacts and run reports.

---

## 2. Orchestrator Extension Bridge

Runtime and batch execution are mediated via **OrchestratorBridge**.

The bridge:
- wraps an existing orchestrator core,
- exposes a stable `.run(...)` surface,
- preserves legacy behavior when all flags are off,
- enforces control‑plane guarantees.

Rules:
- The bridge MUST NOT import Phase 1 / 2 / 4 logic.
- STOP / DEGRADED are valid outcomes.
- The bridge is non‑semantic by design.

---

## 3. Runtime API Usage (Phase 6)

All runtime traffic enters via **Phase 6 API only**.

Phase 6 responsibilities:
- authentication & authorization,
- request normalization,
- failure isolation,
- routing to Phase 3 / Phase 4 / Phase 7.

Direct invocation of internal phases is not supported.

---

## 4. Tips Generation Flow (Songs)

Client
→ Phase 6 API
→ Phase 3 Orchestrator
→ Phase 1 → Phase 2
→ Phase 4 Personalization
→ Phase 4.5 Localization
→ Response

This flow is deterministic and explainable.

---

## 5. Games Recommendation Flow (Phase 7)

Client
→ Phase 6 API
→ Phase 7 Router
→ Ranking + Explanation
→ Feedback / Observability
→ Response

Properties:
- discovery only,
- no gameplay mutation,
- non‑blocking,
- feedback flows to Phase 5 asynchronously.

---

## 6. Game Registry

`games.json` is the single source of truth for supported games.

Rules:
- Adapters and validators MUST NOT hardcode game lists.
- Per‑game behavior is expressed via configuration.

---

## 7. Localization Assets (Phase 4.5)

Localization assets live under `translations/`.

Localization:
- changes presentation only,
- never changes semantic meaning,
- is treated as wiring, not logic.

---

## 8. What This Guide Does NOT Cover

- Internal Phase 1–2 algorithms
- Personalization model internals
- Learning pipeline details
- UI rendering specifics

For routing topology, consult **`Repo_Routing_Skeleton.txt`**.