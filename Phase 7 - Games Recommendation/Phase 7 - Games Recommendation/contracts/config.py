from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from contracts.feature_flags import FeatureFlags


@dataclass(frozen=True)
class Phase7Config:
    """
    Phase 7 Configuration (CI-safe, non-semantic)

    Design constraints:
    - Must NOT affect ranking semantics
    - Must NOT introduce runtime coupling
    - Only used for optional tuning / feature flags
    """

    # max number of recommendations returned
    max_results: int = 10

    # enable explanation layer
    enable_explanations: bool = True

    # feature flags (optional, CI-safe)
    feature_flags: Optional[FeatureFlags] = None
