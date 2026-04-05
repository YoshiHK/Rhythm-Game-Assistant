
from __future__ import annotations

from typing import Any, Dict, List


class ExplanationEngineV1:
    """Stub explanation engine for Phase 7.

    Explanation logic is deferred; this class defines the contract only.
    """

    VERSION = 'v1'

    def explain(self, *, recommendations: List[Dict[str, Any]], ctx: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []
