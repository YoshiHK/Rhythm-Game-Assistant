"""
Eligibility policy for Phase 7 (CI and governance only).

This file defines games that are explicitly excluded from
Phase 7 recommendations, along with human-readable reasons.

IMPORTANT:
- This module MUST NOT be imported by runtime logic.
- It is intended for CI checks, audits, and release governance only.
"""

# Games explicitly excluded from Phase 7 recommendations.
#
# Format:
#   "game_id": "reason for exclusion"
#
# Reasons should be concise, factual, and auditable.
#
# Examples:
# - "Difficulty profiles not yet available"
# - "Catalog metadata incomplete"
# - "Pending partner approval"
# - "Localization coverage insufficient"

EXPLICIT_EXCLUSIONS = {
    # "example_game_id": "Reason for exclusion",
}