# step6_narrative_module.py
# Practical narrative generator for Project SEKAI Tips (Step 6)
# This module assumes that Step 5.3 guidance has already been attached
# to each selected element via the guidance engine.

from __future__ import annotations
from typing import List, Dict, Any


def generate_tips_text(difficulty: str, selected_elements: List[Dict[str, Any]]) -> str:
    """
    Generate the final 2‑paragraph tips text based on:
    - selected_elements (each contains guidance fields)
    - difficulty (expert / master / append)
    Following the tips generation spec structure.
    """

    if not selected_elements:
        return "No actionable elements detected for this chart."

    # ---- Paragraph 1: element summary ----
    element_names = [el.get("element_name", "") for el in selected_elements]
    element_list_phrase = ", ".join(element_names)

    # simple focus description: pick the dominant cause from the first element
    first_el = selected_elements[0]
    focus_desc = "these patterns requiring stable control"  # fallback
    diff_causes = first_el.get("guidance", {}).get("difficulty_causes", "")
    if "because of" in diff_causes:
        # extract clause after 'because of'
        try:
            focus_desc = diff_causes.split("because of", 1)[1].strip().rstrip('.')
        except Exception:
            pass

    para1 = f"This chart features {element_list_phrase}, which {focus_desc}."

    # ---- Paragraph 2: difficulty + breakdown + guidance ----
    sentences = []
    for el in selected_elements:
        g = el.get("guidance", {})
        diff_cause = g.get("difficulty_causes", "").rstrip('.')
        breakdown = g.get("chart_breakdown", "").rstrip('.')
        primary = g.get("primary_focus", "").rstrip('.')
        secondary = g.get("secondary_focus", "").rstrip('.')
        strategy = g.get("strategy", "").rstrip('.')
        target = g.get("target_section", "").rstrip('.')

        s1 = f"The difficulty comes from {diff_cause}."
        s2 = f"This manifests as {breakdown}."
        s3 = f"It helps to focus on {primary}, prioritise {secondary}, and plan {strategy} earlier for {target}."
        sentences.extend([s1, s2, s3])

    para2 = " " .join(sentences)

    return para1 + "
" + para2

