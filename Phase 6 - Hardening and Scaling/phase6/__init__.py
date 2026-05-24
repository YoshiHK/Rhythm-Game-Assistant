"""
Compatibility shim for integration tests.

Expose Phase 6 router under `phase6` namespace.
"""

from song_recommendations.phase6_router import Phase6Router  # re-export