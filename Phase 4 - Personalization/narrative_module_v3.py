
#!/usr/bin/env python3
"""
narrative_module_v3.py
Phase 4: Personalization-aware Narrative Rendering Layer.

Design principles:
- MUST NOT modify Phase 1–3 semantics or outputs.
- Reuses narrative_module_v2 for deterministic text generation.
- Applies personalization only via template/variant selection and ordering.
- Attaches provenance metadata for explainability.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional

from narrative_module_v2 import generate_tips_text_v2


def generate_tips_text_v3(
    difficulty: str,
    selected_elements: List[Dict[str, Any]],
    *,
    engine_mode: str = "deterministic",
    narrative_template_id: Optional[str] = None,
    variant_id: Optional[str] = None,
    locale: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate tips text with Phase‑4 personalization support.

    Parameters
    ----------
    difficulty : str
        Difficulty label (Expert, Master, Append, etc.).
    selected_elements : list
        Phase‑2 elements skeleton (unchanged).
    engine_mode : str
        deterministic | personalized | debug
    narrative_template_id : Optional[str]
        Selected narrative template identifier (Phase 4 decision output).
    variant_id : Optional[str]
        Selected phrasing variant identifier.
    locale : Optional[str]
        Locale hint for future i18n rendering.

    Returns
    -------
    dict
        {
          "tips_text": str,
          "narrative_metadata": {
              "engine_mode": str,
              "template_id": Optional[str],
              "variant_id": Optional[str],
              "locale": Optional[str]
          }
        }
    """

    # Phase‑4 rule: deterministic baseline always exists
    tips_text = generate_tips_text_v2(
        difficulty=difficulty,
        selected_elements=selected_elements,
    )

    # Phase‑4: personalization does NOT rewrite text here
    # Template / variant selection is recorded, not applied semantically

    narrative_metadata = {
        "engine_mode": engine_mode,
        "template_id": narrative_template_id,
        "variant_id": variant_id,
        "locale": locale,
    }

    return {
        "tips_text": tips_text,
        "narrative_metadata": narrative_metadata,
    }


__all__ = ["generate_tips_text_v3"]
