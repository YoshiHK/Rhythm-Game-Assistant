# Recommendation API Contract

Endpoint (conceptual):
POST /api/v1/song-recommendations

Responsibilities of Phase 5:
- Validate request
- Attach provenance-linked rationale
- Return recommendation candidates

Responsibilities of Softr:
- Rank and order songs
- Apply UI logic and filters
- Render explanations
- Capture interaction feedback

Phase 5 MUST NOT:
- Reorder recommendations
- Filter based on UI heuristics
- Override Softr logic
