from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class Phase7RoutingContext:
    """
    Routing context for Phase 7.

    This is intentionally lightweight and presentation-safe.
    It carries only what routing needs to coordinate:

    - player_id: identity for personalization/discovery (Phase 7 does not infer identity)
    - locale: for explanation/template selection
    - top_k: maximum number of returned items
    - platform: optional (used only as a non-blocking filter if registry metadata exists)
    - invocation_source: diagnostics-only (e.g., 'phase6', 'sdk', 'batch')
    - extra: optional pass-through metadata (non-semantic)
    """

    player_id: str
    locale: str = "zh-HK"
    top_k: int = 5

    platform: Optional[str] = None
    invocation_source: str = "phase6"

    extra: Optional[Dict[str, Any]] = None