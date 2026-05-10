"""
Phase 7 — Eligibility Layer

This package defines governance and CI-facing eligibility rules.
It MUST NOT be imported by runtime recommendation code.
"""

from .eligibility_policy import EXPLICIT_EXCLUSIONS

__all__ = ["EXPLICIT_EXCLUSIONS"]