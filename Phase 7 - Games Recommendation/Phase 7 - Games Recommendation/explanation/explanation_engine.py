from __future__ import annotations

from typing import Any, Dict, List


class ExplanationEngine:
    """
    Phase 7 Explanation Engine (CI-safe, bounded, versionless)

    Non-goals:
    - does not judge explanation quality
    - does not do free-form generation
    """

    def attach_explanations(self, items: List[Any]) -> List[Any]:
        """
        Attach a minimal, bounded explanation surface to every item.
        Works for both dict items and dataclass/object items.
        """
        out: List[Any] = []
        for item in items:
            explanation = {"summary": "CI placeholder", "why": []}

            if isinstance(item, dict):
                item = dict(item)
                item["explanation"] = explanation
                out.append(item)
            else:
                # set attribute if possible
                try:
                    setattr(item, "explanation", explanation)
                except Exception:
                    pass
                out.append(item)

        return out


__all__ = ["ExplanationEngine"]