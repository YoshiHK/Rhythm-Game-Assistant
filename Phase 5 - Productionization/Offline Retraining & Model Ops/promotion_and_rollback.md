# Model Promotion & Rollback

Promotion steps:
1. Validate candidate model
2. Stage in shadow or canary mode
3. Monitor metrics and curator feedback
4. Promote to production if safe

Rollback:
- Immediate revert to previous model
- Log incident and block re-promotion

All promotions and rollbacks must be logged.
