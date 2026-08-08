# RGA Maintenance Workflow

Schema: rga.maintenance.workflow.v1.0

## Purpose

Defines the governance and execution workflow between:

- RGA Verifier Bot #1 (Auditing and Recommending Fixes)
- RGA Executor Bot #2 (Maintenance Executor)
- Human Governor / Maintainer

## Core Principle

Completed Phases are immutable.

The workflow may extend, verify, audit, plan, and wire systems together.

The workflow must not modify:

- Phase 1–2 chart understanding and tips generation
- Phase 3 canonical ingestion contract
- Phase 4 personalization logic
- Phase 4.5 localization logic
- Phase 5–7 recommendation logic

## Authority Model

### Bot #1

Roles:

- Checker
- Validator
- Verifier
- Auditor
- Advisor
- Maintainer Support

Restrictions:

- Cannot approve execution
- Cannot execute changes
- Cannot merge changes
- Cannot delete assets

### Bot #2

Roles:

- Execution Planner
- Maintenance Executor

Restrictions:

- Cannot self-approve
- Cannot override governance
- Cannot bypass Bot #1 audits

### Human

Roles:

- Governor
- Maintainer

Responsibilities:

- Review execution plans
- Approve or reject execution
- Authorize exceptional maintenance actions

## Double-Sideway Verification Workflow

1. Bot #1 Pre-Audit
2. Bot #2 Execution Plan Generation
3. Bot #1 Plan Audit
4. Human Approval
5. Bot #2 Execution
6. Bot #1 Post-Audit

## Pre-Audit

Inputs:

- runtime_verifier_report.json
- governance lineage
- artifact lineage

Outputs:

- root failures
- derived failures
- governance state
- audit report

## Execution Planning

Bot #2 shall:

- prioritize root failures
- generate repair DAGs
- generate execution plans
- generate rollback plans

Required execution plan sections:

- target_root_failures
- proposed_changes
- verification_steps
- rollback

## Plan Audit

Bot #1 evaluates:

- root failure alignment
- derived failure sequencing
- protected phase violations
- rollback availability
- governance compliance

Possible results:

- approved_for_human_review
- needs_revision
- rejected_by_policy

## Execution

Execution requires explicit human approval.

Bot #2 may perform:

- tooling updates
- workflow updates
- verifier updates
- evidence generation
- bootstrap script generation

Bot #2 may not perform:

- canonical_row modification
- personalization modification
- localization modification
- recommendation logic modification
- source asset deletion

## Post-Audit

Bot #1 compares:

- pre-audit state
- execution plan
- current repository state

Verification targets:

- root failure progress
- derived failure progress
- governance regressions
- deletion readiness
- protected phase integrity

## Current Priority

Primary root contract:

artifact_database_policy

Artifact backbone:

file_scan_inventory.db
    -> chart_assets.db
    -> chart_patterns.db

Derived contracts:

- artifact_relationships
- artifact_backbone_contract
- asset_coverage
- hash_integrity
- type_A_usability
- runtime_artifact_readiness

## Governance Rules

- Validation != Verification
- Root Failure != Derived Failure
- Dependency Failure != Governance Failure
- Runtime Limited != Governance Blocked
- Discovery != Verification
- Presence != Readiness

## Version

v1.0
