# Rhythm Game Assistant — System Bundle (Phases 1–7)

**Bundle purpose:** Provide a single, authoritative entry point for understanding and integrating the Rhythm Game Assistant (RGA) system across Phases 1–7.

This bundle contains **authoritative wrapper documents**:
- `SPEC.md` — system-wide contract and phase boundaries
- `ARCHITECTURE.md` — system-wide architecture and data-flow
- `LIMITATIONS.md` — explicit prohibitions and non-goals (safety / immutability)
- `USAGE.md` — how to run / integrate the system at the supported entrypoints
- `MANIFEST.md` — source documents (Wave 1–9) this bundle is derived from

> **Non‑negotiable rule (system-wide):** 
- Completed phases are immutable. 
- Wiring between phases is flexible.
- Charts live in OneDrive.
- UMI ingests charts automatically.
- Tips are immutable outputs.
- Players never trigger analysis.

---

## What this system does (high level)

- Generates deterministic gameplay tips and summaries for charts (Phase 1–2).
- Scales ingestion across multiple rhythm games via a game‑agnostic orchestrator (Phase 3 / UMI).
- Personalizes presentation without changing gameplay semantics (Phase 4).
- Localizes finalized narrative output without changing meaning (Phase 4.5).
- Defines productionization and offline learning loops (Phase 5).
- Defines platform hardening, security, reliability, and partner boundaries (Phase 6).
- Adds game‑level recommendations as a downstream, explainable discovery layer (Phase 7).

---

## Where to start

1. Read `SPEC.md` for the system contract and phase boundaries.
2. Read `ARCHITECTURE.md` for the end-to-end data flow.
3. Read `USAGE.md` to run the ingestion orchestrator and understand supported integration points.
4. Keep `LIMITATIONS.md` nearby while building UI (e.g., Softr) to avoid semantic drift.

---

## Intended consumers

- **Product / UI builders (Softr / client):** consume outputs, do not re-interpret.
- **Engine maintainers:** follow manifested specs/schemas as inputs.
- **Ops / platform:** implement Phase 6 guardrails around orchestration and APIs.

### Storage Characteristics

The Rhythm Game Assistant stores only generated outputs:
- tips text
- summaries
- difficulty profiles
- provenance metadata

Raw chart files are treated as ephemeral analytical inputs and are never stored in the application database.

As a result, storage requirements scale linearly with the number of song–difficulty pairs and remain lightweight (typically a few kilobytes per entry).

