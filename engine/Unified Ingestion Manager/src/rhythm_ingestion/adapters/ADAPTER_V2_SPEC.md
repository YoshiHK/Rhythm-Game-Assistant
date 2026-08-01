
# ADAPTER_V2_SPEC.md
## Adapter v2 — Multi‑Game Integration Contract (Additive)

**Scope:** Phase 3 (UMI) adapters  
**Status:** Draft (Lock‑ready after review)

This spec defines an **additive** Adapter v2 interface that scales to new games (Bandori, D4DJ, Phigros)
without modifying completed phases.

Although dictionary key order is not semantically significant for pipeline execution, adapters SHOULD emit canonical payloads using a consistent key ordering for human readability, auditability, and long‑term maintenance consistency across games.

---

## 1) Why Adapter v2 exists

The existing Phase‑3 adapter contract focuses on routing + row persistence:
- `accepts_file(path)`
- `load(path)`
- `to_canonical_row(raw)`

UMI already optionally calls `to_canonical_payload(path)` when present.
Adapter v2 formalizes that optional payload contract.

---

## 2) Required methods (unchanged)

Adapters MUST implement:
- `accepts_file(path) -> bool`
- `load(path) -> RawChart`
- `to_canonical_row(raw) -> dict`

These are required for UMI routing and writer insertion.

---

## 3) Optional methods (newly formalized)

Adapters SHOULD implement:

### 3.1 `to_canonical_payload(path) -> dict`
Must emit a dict conforming to **canonical_chart_payload.schema.json**, including:
- `game_id`, `chart_id`, `difficulty`
- `adapter_metadata`
- `chart_meta` (bpm, max_time_beats, optional measure_markers/bpm_changes)
- `note_events` (canonical events)
- optional `sections`, `diagnostics`

### 3.2 `capabilities() -> dict`
Returns a lightweight capabilities descriptor, e.g.:
- supports_sections
- supports_bpm_changes
- supports_measure_markers

This is informational only.

---

## 4) Strict non‑goals

Adapters MUST NOT:
- implement gameplay semantics (elements, severity, selection)
- generate tips
- call registries or writers

Adapters are structural normalizers only.

---

## 5) Backwards compatibility

Adapter v2 is a superset of the existing adapter interface.
UMI can keep routing and persistence unchanged.

---

**End of ADAPTER_V2_SPEC.md**
