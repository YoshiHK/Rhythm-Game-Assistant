from __future__ import annotations

"""
delete_policy_validator.py

Validation for safety delete policy config.

Purpose
-------
Validate structure and types of delete_policy.json.

Scope
-----
- local validation only
- no DB access
- no system-level checks

This is a VALIDATOR (not verifier).
"""

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional


# --------------------------------------------------
# Models
# --------------------------------------------------

@dataclass
class PolicyIssue:
    severity: str  # error / warning
    field: str
    message: str


@dataclass
class PolicyValidationResult:
    valid: bool
    issues: List[PolicyIssue] = field(default_factory=list)


# --------------------------------------------------
# Core validation
# --------------------------------------------------

def validate_delete_policy(policy: Dict[str, Any]) -> Dict[str, Any]:
    issues: List[PolicyIssue] = []

    # ---------------------------
    # helpers
    # ---------------------------
    def err(field: str, msg: str):
        issues.append(PolicyIssue("error", field, msg))

    def warn(field: str, msg: str):
        issues.append(PolicyIssue("warning", field, msg))

    # ---------------------------
    # version
    # ---------------------------
    version = policy.get("version")
    if version is None:
        err("version", "missing version")
    elif not isinstance(version, int):
        err("version", "must be integer")

    # ---------------------------
    # verification
    # ---------------------------
    verification = policy.get("verification", {})
    if not isinstance(verification, dict):
        err("verification", "must be object")
    else:
        if "require_pass" in verification and not isinstance(
            verification["require_pass"], bool
        ):
            err("verification.require_pass", "must be boolean")

    # ---------------------------
    # scope
    # ---------------------------
    scope = policy.get("scope", {})
    if not isinstance(scope, dict):
        err("scope", "must be object")
    else:
        for key in ["only_type_A", "include_type_B"]:
            if key in scope and not isinstance(scope[key], bool):
                err(f"scope.{key}", "must be boolean")

    # ---------------------------
    # deduplication
    # ---------------------------
    dedup = policy.get("deduplication", {})
    if not isinstance(dedup, dict):
        err("deduplication", "must be object")
    else:
        if "enabled" in dedup and not isinstance(dedup["enabled"], bool):
            err("deduplication.enabled", "must be boolean")

        if "keep_at_least_one_copy" in dedup and not isinstance(
            dedup["keep_at_least_one_copy"], bool
        ):
            err("deduplication.keep_at_least_one_copy", "must be boolean")

        if "max_copies_to_keep" in dedup:
            if not isinstance(dedup["max_copies_to_keep"], int):
                err("deduplication.max_copies_to_keep", "must be integer")
            elif dedup["max_copies_to_keep"] < 1:
                err("deduplication.max_copies_to_keep", "must be >= 1")

        group_by = dedup.get("group_by")
        if group_by and group_by not in {"content_sha256", "path"}:
            warn("deduplication.group_by", f"unknown value: {group_by}")

    # ---------------------------
    # action
    # ---------------------------
    action = policy.get("action", {})
    if not isinstance(action, dict):
        err("action", "must be object")
    else:
        mode = action.get("mode")
        if mode and mode not in {"quarantine"}:
            err("action.mode", "only 'quarantine' supported")

        if "allow_delete_last_copy" in action and not isinstance(
            action["allow_delete_last_copy"], bool
        ):
            err("action.allow_delete_last_copy", "must be boolean")

        if "quarantine_dir" in action and not isinstance(
            action["quarantine_dir"], str
        ):
            err("action.quarantine_dir", "must be string")

    # ---------------------------
    # safety
    # ---------------------------
    safety = policy.get("safety", {})
    if not isinstance(safety, dict):
        err("safety", "must be object")
    else:
        for key in ["dry_run_default", "require_explicit_execute"]:
            if key in safety and not isinstance(safety[key], bool):
                err(f"safety.{key}", "must be boolean")

    # ---------------------------
    # logging
    # ---------------------------
    logging = policy.get("logging", {})
    if not isinstance(logging, dict):
        err("logging", "must be object")
    else:
        if "highlight_limit" in logging and not isinstance(
            logging["highlight_limit"], int
        ):
            err("logging.highlight_limit", "must be integer")

    # ---------------------------
    # result
    # ---------------------------
    result = PolicyValidationResult(
        valid=not any(i.severity == "error" for i in issues),
        issues=issues,
    )

    return {
        "valid": result.valid,
        "issues": [asdict(i) for i in issues],
    }


__all__ = [
    "validate_delete_policy",
]