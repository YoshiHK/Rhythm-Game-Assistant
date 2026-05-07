"""
Phase 4 — Registry Layer (declarative, allow-list only).

This package defines:
- Narrative template allow-lists
- Variant allow-lists
- Difficulty × locale → template mappings

Hard rules:
- Declarative only (no personalization logic)
- No model inference
- No narrative generation
- Localization content lives in Phase 4.5
"""

from .template_registry_loader import (
    LoadedTemplateRegistries,
    load_phase4_template_registry,
)

__all__ = [
    "LoadedTemplateRegistries",
    "load_phase4_template_registry",
]