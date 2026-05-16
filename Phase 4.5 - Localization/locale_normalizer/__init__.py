from __future__ import annotations

from .normalize_locale import normalize_locale
from .fallback_rules import (
    build_fallback_chain,
    validate_fallback_graph,
)

__all__ = [
    "normalize_locale",
    "build_fallback_chain",
    "validate_fallback_graph",
]