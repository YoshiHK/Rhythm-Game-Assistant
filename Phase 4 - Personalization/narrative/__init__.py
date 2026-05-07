"""
Phase 4 — Narrative Layer (presentation-only).

This package provides the Narrative v3 bridge:
- Reuses Phase 2 narrative_module_v2 for deterministic text generation
- Applies Phase 4 personalization via ordering / template / variant hints only

Hard rules:
- MUST NOT modify Phase 1–3 semantics
- MUST NOT perform localization (handled in Phase 4.5)
- MUST be safe to bypass (deterministic fallback always available)
"""

from .narrative_v3_bridge import generate_tips_text_v3

__all__ = [
    "generate_tips_text_v3",
]