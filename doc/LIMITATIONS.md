# Limitations & Non‑Goals (Phases 1–7)

This system is intentionally constrained to preserve trust, determinism, and auditability.

## Hard prohibitions (summary)

### UMI (Phase 3)
- MUST NOT contain gameplay analysis logic.
- MUST NOT re-implement or alter Phase 1–2 algorithms.
- MUST NOT decide severity, selection, or narrative meaning.
- MUST NOT embed game-specific heuristics.
- MUST NOT perform personalization.

### Personalization (Phase 4)
- MUST NOT modify detected elements, severity labels, scores, training items, or section coverage.
- MUST NOT create/delete/rewrite elements.
- MUST NOT generate free-form text (narrative is template-bound).

### Localization (Phase 4.5)
- MUST NOT change gameplay advice meaning, intent, ordering/emphasis, or safety messaging.
- MUST NOT summarize or paraphrase gameplay meaning.
- Prohibits runtime free-form translation and context-less translation.

### Learning (Phase 5)
- Offline learning only: no live/online learning.
- MUST NOT alter Phase 4 outputs at runtime.
- MUST NOT modify element selection, severity, score, or guidance.

### Platform hardening (Phase 6)
- MUST NOT reinterpret gameplay advice.
- MUST NOT alter personalization or localization outputs.
- MUST NOT introduce new learning logic.
- MUST NOT override Phase 5 contracts.

### Game recommendations (Phase 7)
- MUST NOT alter song/chart recommendations.
- MUST NOT change tips meaning, severity, or narrative logic.
- MUST NOT redefine difficulty labels or taxonomies.
- MUST NOT inject logic into Phases 1–6.
- MUST NOT bypass Phase 6 enforcement or observability.

## Non-goals
- Phase 7 does not redesign the UI; it adds a parallel discovery channel.
- Phase 6 does not add product intelligence.
- Phase 5 does not own UI.

