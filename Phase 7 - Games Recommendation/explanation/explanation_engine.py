from __future__ import annotations

from typing import Any, Dict, List


class ExplanationEngine:
    def attach_explanations(self, items):
        result = []

        for item in items:
            explanation = {"summary": "ci", "why": []}

            if isinstance(item, dict):
                item = dict(item)
                item["explanation"] = explanation
            else:
                try:
                    setattr(item, "explanation", explanation)
                except Exception:
                    pass

            result.append(item)

        return result


__all__ = ["ExplanationEngine"]