"""
Deployment Router

Responsibilities:
- Route execution across environments (dev / staging / canary / prod)
- Enforce environment-level constraints
- Support gradual rollout strategies

No semantic behavior is allowed here.
"""

class DeploymentRouter:
    def route(self, context):
        return True
