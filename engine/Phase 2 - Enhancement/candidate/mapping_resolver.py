"""
mapping_resolver.py (Phase 2)

Resolves the tips training mapping artifact used for
tag -> element candidate inference.

This module is declarative:
- it selects WHICH mapping to use
- it does NOT implement mapping semantics
"""

from __future__ import annotations
from typing import Dict, Any, Optional

import json
import os


def resolve_training_mapping(
    *,
    mapping_path: Optional[str] = None,
    default_path: str = "tips_training_mapping.json",
) -> Dict[str, Any]:
    """
    Resolve and load a tips training mapping file.

    Priority:
    1) explicit mapping_path (if provided and exists)
    2) default_path

    Returns:
    - mapping dict if loaded successfully
    - {} on any failure

    No exceptions are raised.
    """
    path = None
    if mapping_path and isinstance(mapping_path, str) and os.path.exists(mapping_path):
        path = mapping_path
    elif os.path.exists(default_path):
        path = default_path

    if not path:
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    return {}


__all__ = ["resolve_training_mapping"]