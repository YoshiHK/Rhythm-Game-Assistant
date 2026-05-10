from __future__ import annotations

from dataclasses import dataclass

from .feature_flags import FeatureFlags


from __future__ import annotations
from dataclasses import_flags import FeatureFlagsfrom dataclasses import dataclass


@dataclass(frozen=True)
class Phase7Config:
    """
    Phase 7 configuration.

    Note:
    - Phase 7 does NOT support runtime ranker or explainer versioning.
    - Evolution occurs through implementation updates, not config switches.
    """
    feature_flags: FeatureFlags = FeatureFlags()


