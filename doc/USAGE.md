# Usage Guide (Entry Points & Integration)

This guide describes supported integration entrypoints **without changing completed-phase behavior**.

## 1) Run the Phase 3 UMI orchestrator (batch ingestion)

The UMI orchestrator provides a CLI surface with the following options:
- `--source` directory of raw chart files
- `--db` path to the Song Database Excel (required unless `--dry-run`)
- `--dry-run` run without persistence
- `--game` restrict run to a single enabled `game_id`
- `--json` write run report to a JSON path
- `--tips-mode` `production` or `debug`

UMI produces canonical rows/payloads, invokes Phase 1–2 pipelines, and emits batch summaries and run reports.

## 2) Use the orchestrator extension bridge (non-breaking)

The bridge provides a stable `.run()` surface to wrap either:
- a core object with `.run(...)`, or
- a module-like object exposing `.ingest(...)`.

If all FeatureFlags are disabled, the wrapper behaves as a thin pass-through.
The bridge must not import or call Phase 1/2/4 logic directly.

## 3) Game registry (games.json)

`games.json` is the single source of truth for supported rhythm games.
Adapters/validators MUST NOT hardcode game lists.

## 4) Tip generation inputs/outputs (Phase 1–2)

Preferred payload shape (per chart):
```json
{
  "detected_tags": ["..."],
  "sections": ["SectionMetrics", "..."],
  "diagnostics": {"...": "..."}
}
```
Fallback payload shape:
```json
{ "detected_tags": ["..."] }
```
Outputs include:
- `tips_text` (2 paragraphs)
- per-chart summary block
- batch summary block

## 5) Localization store (Phase 4.5)

Localization assets live under `translations/` with required folder parity.
Localization changes presentation, never meaning.

