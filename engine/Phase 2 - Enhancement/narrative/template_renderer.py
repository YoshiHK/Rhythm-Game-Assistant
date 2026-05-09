"""
template_renderer.py (Phase 2)

Renders narrative text from spec-aligned templates
and structured guidance fields.
"""

from __future__ import annotations
from typing import Dict, Any


def render_from_template(
    *,
    template: str,
    guidance: Dict[str, Any],
) -> str:
    """
    Render a template using guidance fields.

    Template format:
    - Python-style {field_name} placeholders
    """
    if not isinstance(template, str):
        return ""

    if not isinstance(guidance, dict):
        guidance = {}

    try:
        return template.format(**guidance)
    except Exception:
        # Fail-safe: return template without substitution
        return template


__all__ = ["render_from_template"]