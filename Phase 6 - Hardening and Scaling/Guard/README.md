# Phase 6 - Guards

Guards are **non-semantic enforcement components** in Phase 6.

They exist to:
- protect system reliability,
- enforce operational invariants,
- and prevent unsafe execution.

Guards MAY:
- block execution,
- allow execution,
- record observations for audit or observability.

Guards MUST NOT:
- schedule work,
- trigger scans,
- interpret gameplay, tips, or recommendations,
- modify payloads or outputs.

## Guard Execution Model

- Guards are evaluated by the Phase 6 router.
- Guards consume immutable routing context and system signals.
- Guards return a boolean allow/deny decision.

## Available Guards

- **must_scan_guard**
  Enforces the must-scan invariant before ingestion.

- **reliability_guard**
  Protects against retries, duplication, and unstable execution.

- **security_guard**
  Enforces authentication, authorization, and boundary safety.

- **abuse_guard**
  Mitigates rate abuse and anomalous usage patterns.

- **compliance_guard**
  Ensures auditability, logging, and retention compliance.

Guards observe and block; they never decide semantics.
