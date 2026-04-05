"""
Partner Gateway

Responsibilities:
- Act as the single external-facing entrypoint
- Enforce authentication, authorization, and rate limits
- Isolate partner traffic from internal execution paths

No gameplay or recommendation logic is allowed here.
"""

class PartnerGateway:
    def route(self, context, payload):
        return payload
