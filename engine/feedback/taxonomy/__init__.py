"""
engine.feedback.taxonomy

Reason taxonomy definitions for feedback interpretation.

Purpose:
- Define the canonical set of reason_codes
- Provide semantic structure (category / layer / cause_type / etc.)
- Serve as shared language for interpreter, curator, and dataset layers

Notes:
- This is a runtime mirror; authoritative usage occurs in Phase 5
- Must remain stable once used in training pipelines
"""

from .reason_taxonomy_v1 import *


__all__ = [
    "reason_taxonomy_v1"
]