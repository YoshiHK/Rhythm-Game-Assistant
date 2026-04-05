# Adapter SDK Interface Spec (Short Version)

This document describes the **minimal interface** that any game-specific adapter must implement
in order to feed charts into the gameplay-tips engine using the canonical
`canonical_chart_payload.schema.json` payload.

The engine consumes **only** the canonical payload; each adapter is responsible for
parsing its source game's chart format and normalizing it into this form.

---

## 1. Core Responsibilities of an Adapter

For each chart in a source game (e.g. Proseka, Arcaea, ユメステ, BanG Dream / Our Notes, D4DJ),
the adapter MUST:

1. **Parse** the game-native chart asset.
2. **Normalize** all gameplay-relevant objects into `note_events[]` with
   canonical fields (`time_beats`, `lane`, `kind`, `extra{...}`).
3. **Populate** `chart_meta` with at least `bpm` and `max_time_beats` and optional
   `measure_markers` / `bpm_changes` when available.
4. **Emit** a single JSON object that conforms to `canonical_chart_payload.schema.json`.

The downstream detection pipeline uses this canonical payload to compute
pattern-signal tags and generate tips.

---

## 2. Recommended Adapter Interface (Pseudo-API)

Each adapter SHOULD expose a small, pure, deterministic API.

### 2.1 `load_chart(source_ref) -> RawChart`

- **Input**: `source_ref` (path, ID, or handle to the game-native chart asset).
- **Output**: `RawChart` – an adapter-defined structure that directly mirrors the
  source game's format (no normalization yet).

This function knows how to read the game's internal chart representation
(e.g. JSON, binary, SVG, custom text format).

### 2.2 `normalize_events(raw_chart) -> (chart_meta, note_events)`

- **Input**: `RawChart` from `load_chart()`.
- **Output**:
  - `chart_meta`: minimal chart metadata required by the schema
    (BPM, max_time_beats, optional time-signature & BPM changes).
  - `note_events[]`: list of canonical note events, where each element has:

```jsonc
{
  "time_beats": number,
  "lane": number,
  "kind": "tap" | "critical_tap" | "flick" | "flick_arrow" |
           "hold_body_or_start" | "hold_path" | "critical_hold_path",
  "extra": {
    "width_lanes"?: number,
    "rect_height"?: number,
    "direction"?: string,
    "shape"?: string,
    "raw_type"?: string
  }
}
```

This step is where all game-specific note types are mapped onto the canonical set.

### 2.3 (Optional) `build_sections(chart_meta, note_events) -> sections[]`

- **Input**: `chart_meta`, `note_events[]`.
- **Output**: `sections[]` (SectionMetrics records).

If omitted, the shared detection layer will compute sections itself.
Adapters may implement this for games where precise sectioning is well-understood.

### 2.4 `to_canonical_payload(source_ref) -> CanonicalChartPayload`

This is the main entrypoint used by the batch pipeline.

**Input**: `source_ref` as above.

**Process (typical implementation):**

1. `raw_chart = load_chart(source_ref)`
2. `(chart_meta, note_events) = normalize_events(raw_chart)`
3. Optionally, `sections = build_sections(chart_meta, note_events)`
4. Assemble the canonical payload:

```jsonc
{
  "game_id": "...",
  "chart_id": "...",
  "difficulty": "...",
  "adapter_metadata": {
    "adapter_id": "adapter_<game>_v1",
    "adapter_version": "1.0.0",
    "source_format": "...",
    "source_path": "...",
    "notes": "..."
  },
  "chart_meta": chart_meta,
  "note_events": note_events,
  "sections": sections?,
  "diagnostics": { ... }?
}
```

**Output**: `CanonicalChartPayload` – a JSON object that MUST validate
against `canonical_chart_payload.schema.json`.

---

## 3. Determinism and Versioning Requirements

- Adapters MUST be **pure and deterministic**:
  - given the same source chart asset and adapter version, they MUST produce
    the same canonical payload.
- Any change in mapping logic or parsing must trigger a **version bump** in
  `adapter_version`.
- The batch pipeline can then track which adapter version produced which
  canonical payloads for audit and regression testing.

---

## 4. Error Handling & Diagnostics

- If parsing fails or unsupported features are encountered, the adapter SHOULD:
  - populate `diagnostics` with structured warnings/errors;
  - optionally mark flags that the pipeline can use to skip tips generation.
- Adapters MUST NOT fabricate data; when a field cannot be inferred, omit it or
  clearly document the approximation in `diagnostics.notes`.

---

This interface, together with `canonical_chart_payload.schema.json`, defines the
minimal contract required for multi-game support in the gameplay-tips engine.
