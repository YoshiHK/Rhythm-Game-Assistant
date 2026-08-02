"""
runtime_verifier.py

MCP Verifier Bot v1.0
RGA Systems Auditor

New in v1.0:
- Governance Verification
- Architecture Contract Verification
- Artifact Backbone Verification
- Flow Contract Verification
- MCP Contract Verification
- Completed Phase Boundary Verification
- Layer Governance Verification

Carried forward from v0.7:
- Artifact Database Verification
- Artifact Relationship Verification
- Dependency Reality Verification
- Asset Scope Policy Verification
- Flow Verification
- Layer Separation Audit
- Type B Intelligence Verification

Carried forward from v0.6:
- Asset Coverage Verification
- Hash Verification
- Type A Usability Verification
- Runtime DB Read Verification
- Repository Reality vs Import Reality vs Runtime Reality separation
- Asset Pipeline Verification
- chart_assets.db discovery and read-only inspection
- Type A / Type B asset evidence
- Deletion readiness gate
- MCP tool visibility / registration evidence

Purpose:
- Read-only architecture, runtime, artifact and governance verification
  for Rhythm Game Assistant (RGA).

Verifier responsibilities:
- repository reality verification
- runtime reality verification
- architecture governance verification
- artifact backbone verification
- flow contract verification
- deletion readiness governance

Boundary:
- Verification-only.
- Read-only.
- Must not modify Completed Phases 1–7.
- Must not write to databases.
- Must not mutate runtime behavior.
- Must not replace authoritative runtime output.

Governance model:
- GitHub Advanced Security:
    security validation

- RGA Verifier:
    architecture and runtime governance

Recommended placement:
- tools/runtime_verifier.py
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import platform
import sqlite3
import sys
import traceback
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import quote


# -----------------------------------------------------------------------------
# Result models
# -----------------------------------------------------------------------------

@dataclass
class CheckResult:
    domain: str
    check: str

    status: str
    severity: str

    summary: str
    evidence: Dict[str, Any]

    suggested_fix: Optional[str] = None

    governance_domain: Optional[str] = None
    contract_type: Optional[str] = None

@dataclass
class RuntimeCandidate:
    root: str

    score: int
    confidence: str

    matched: List[str]
    missing: List[str]

    governance_score: int = 0


@dataclass
class ArtifactDatabaseSnapshot:
    logical_name: str
    path: str
    exists: bool
    readable: bool
    tables: List[str]
    table_columns: Dict[str, List[str]]
    table_row_counts: Dict[str, Any]
    candidate_columns: Dict[str, Dict[str, Optional[str]]]
    error: Optional[str] = None


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

EXPECTED_PACKAGE = "rhythm_ingestion"

INVALID_PACKAGE_ALIASES = [
    "rhythm ingestion",
]

ARTIFACT_WEIGHTS: Dict[str, int] = {
    "main.py": 40,
    "src/rhythm_ingestion/api/recommend.py": 25,
    "src/rhythm_ingestion/api/app.py": 15,
    "src/rhythm_ingestion/runtime_meta.py": 10,
    "mcp_server.py": 10,

    # v0.7 artifact runtime backbone evidence
    "file_scan_inventory.db": 15,
    "chart_assets.db": 15,
    "chart_patterns.db": 15,
}

LOGICAL_ARTIFACT_ALIASES: Dict[str, List[str]] = {
    "src/rhythm_ingestion/api/recommend.py": [
        "src/rhythm ingestion/api/recommend.py",
    ],
    "src/rhythm_ingestion/api/app.py": [
        "src/rhythm ingestion/api/app.py",
    ],
    "src/rhythm_ingestion/runtime_meta.py": [
        "src/rhythm ingestion/runtime_meta.py",
    ],
}


# -----------------------------------------------------------------------------
# Artifact database constants
# -----------------------------------------------------------------------------

FILE_SCAN_INVENTORY_DB_NAME = "file_scan_inventory.db"
CHART_ASSETS_DB_NAME = "chart_assets.db"
CHART_PATTERNS_DB_NAME = "chart_patterns.db"

# Backward-compatible alias used by v0.6 methods.
ASSET_DB_NAME = CHART_ASSETS_DB_NAME

ARTIFACT_DATABASE_NAMES = [
    FILE_SCAN_INVENTORY_DB_NAME,
    CHART_ASSETS_DB_NAME,
    CHART_PATTERNS_DB_NAME,
]

ARTIFACT_DATABASE_LOGICAL_NAMES: Dict[str, str] = {
    FILE_SCAN_INVENTORY_DB_NAME: "file_scan_inventory",
    CHART_ASSETS_DB_NAME: "chart_assets",
    CHART_PATTERNS_DB_NAME: "chart_patterns",
}

ARTIFACT_RELATIONSHIP_CHAIN = [
    FILE_SCAN_INVENTORY_DB_NAME,
    CHART_ASSETS_DB_NAME,
    CHART_PATTERNS_DB_NAME,
]


# -----------------------------------------------------------------------------
# Asset type constants
# -----------------------------------------------------------------------------

TYPE_A_EXTENSIONS = {
    ".aff",
    ".sus",
    ".json",
    ".html",
    ".mht",
}

TYPE_B_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".url",
    ".webloc",
}

MIN_TYPE_A_TEXT_LENGTH = 32
MAX_REPORT_SAMPLE_VALUE_LENGTH = 500


# -----------------------------------------------------------------------------
# Asset scope policy
# -----------------------------------------------------------------------------
#
# v0.6 proved that extension-only detection is too broad because general repository
# JSON files can be mistaken for chart assets. v0.7 keeps repository-wide evidence,
# but introduces explicit scope helpers so verification can distinguish:
#
#   repository files != chart assets
#
# The policy remains read-only and diagnostic only.

ASSET_SCOPE_INCLUDE_ROOT_HINTS = [
    "chart_assets",
    "charts",
    "assets",
    "ingestion_assets",
]

ASSET_SCOPE_EXCLUDE_ROOT_HINTS = [
    ".git",
    ".github",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    "docs",
    "tools",
    "artifacts",

    "Phase 4 - Personalization",
    "Phase 4.5 - Localization",
    "Phase 5 - Productionization",
    "Phase 6 - Hardening and Scaling",
    "Phase 7 - Games Recommendation",
]

ASSET_SCOPE_EXCLUDE_FILENAME_SUFFIXES = [
    ".schema.json",
    ".expect.json",
]

ASSET_SCOPE_EXCLUDE_FILENAME_CONTAINS = [
    "baseline",
    "registry",
    "mcp.json",
]


# -----------------------------------------------------------------------------
# SQLite column candidates
# -----------------------------------------------------------------------------

PATH_COLUMN_CANDIDATES = [
    "path",
    "file_path",
    "source_path",
    "asset_path",
    "original_path",
    "relative_path",
]

HASH_COLUMN_CANDIDATES = [
    "sha256",
    "file_sha256",
    "source_sha256",
    "content_hash",
    "hash",
]

TEXT_COLUMN_CANDIDATES = [
    "text_representation",
    "converted_text",
    "text",
    "content_text",
]

REFERENCE_URL_COLUMN_CANDIDATES = [
    "reference_url",
    "url",
    "source_url",
]

TYPE_COLUMN_CANDIDATES = [
    "asset_type",
    "type",
    "kind",
]

PATTERN_COLUMN_CANDIDATES = [
    "pattern",
    "pattern_id",
    "pattern_name",
    "pattern_type",
    "tag",
    "tags",
]

CHART_ID_COLUMN_CANDIDATES = [
    "chart_id",
    "song_id",
    "asset_id",
    "file_id",
    "source_id",
    "id",
]

TIMESTAMP_COLUMN_CANDIDATES = [
    "created_at",
    "updated_at",
    "scanned_at",
    "ingested_at",
    "timestamp",
]


# -----------------------------------------------------------------------------
# Dependency reality constants
# -----------------------------------------------------------------------------

REQUIRED_RUNTIME_DEPENDENCY_MODULES = [
    "sqlite3",
]

OPTIONAL_RUNTIME_DEPENDENCY_MODULES = [
    "fastapi",
    "uvicorn",
    "pydantic",
]

API_RUNTIME_DEPENDENCY_MODULES = [
    "fastapi",
    "pydantic",
]

# -----------------------------------------------------------------------------
# Governance constants (v1.0)
# -----------------------------------------------------------------------------

GOVERNANCE_DOMAINS = [
    "architecture_contracts",
    "artifact_backbone",
    "flow_contracts",
    "layer_boundaries",
    "mcp_contracts",
]

GOVERNANCE_REQUIRED_GATES = [
    "phase_boundaries_verified",
    "architecture_contracts_verified",
    "artifact_backbone_verified",
    "flow_contracts_verified",
    "layer_boundaries_verified",
    "mcp_contract_verified",
]

GOVERNANCE_VERDICTS = [
    "pass",
    "warning",
    "fail",
    "critical",
]

# -----------------------------------------------------------------------------
# Governance failure lineage policy
# -----------------------------------------------------------------------------
#
# Purpose
# -------
#
# Governance failures are not all equal.
#
# Some failures represent independently actionable root causes.
#
# Other failures are expected downstream consequences of a root
# contract failure and should be rendered as derived failures.
#
# Example:
#
#     artifact_database_policy
#         ↓
#     artifact_relationships
#         ↓
#     artifact_backbone_contract
#         ↓
#     asset_coverage
#         ↓
#     hash_integrity
#         ↓
#     type_A_usability
#         ↓
#     runtime_artifact_readiness
#
# In this case:
#
#     artifact_database_policy
#
# is the root failure.
#
# All downstream failures should be rendered as derived failures.
#
# -----------------------------------------------------------------------------

#
# Contracts that should always be treated as
# independently actionable governance blockers.
#
ROOT_FAILURE_CONTRACT_TYPES: Set[str] = {

    #
    # Artifact backbone root contract.
    #
    "artifact_database_policy",

    #
    # Governance deletion gate.
    #
    # Even if its status depends on upstream failures,
    # deletion_readiness remains an independently visible
    # governance blocker because source file deletion
    # must remain prohibited until all required contracts pass.
    #
    "deletion_readiness",
}


#
# Contracts whose failures are normally consequences
# of another root contract failure.
#
DERIVED_FAILURE_POLICY: Dict[str, str] = {

    #
    # Artifact backbone cascade.
    #
    # Missing or unreadable artifact databases
    # naturally prevent all downstream artifact validation
    # and verification contracts from succeeding.
    #

    "artifact_relationships":
        "artifact_database_policy",

    "artifact_backbone_contract":
        "artifact_database_policy",

    "asset_coverage":
        "artifact_database_policy",

    "hash_integrity":
        "artifact_database_policy",

    "type_A_usability":
        "artifact_database_policy",

    "runtime_artifact_readiness":
        "artifact_database_policy",
}


#
# Governance meta-results.
#
# These are verdicts, not causes.
#
# They should never be counted as root failures.
#
GOVERNANCE_META_CONTRACT_TYPES: Set[str] = {

    "governance_verdict",

    #
    # Potential future additions:
    #
    # "architecture_verdict",
    # "runtime_verdict",
    # "artifact_backbone_verdict",
    #
}

# -----------------------------------------------------------------------------
# Flow / layer separation constants
# -----------------------------------------------------------------------------

FLOW_KEYWORDS = {
    "chart_first": [
        "chart",
        "pattern",
        "tips",
    ],
    "player_first": [
        "player",
        "recommend",
        "tips",
    ],
    "progression": [
        "progression",
        "game",
        "song",
        "tips",
    ],
}

LAYER_KEYWORDS = {
    "models": ["model", "models"],
    "normalizers": ["normalizer", "normalizers", "normalize"],
    "converters": ["converter", "converters", "convert"],
    "classifiers": ["classifier", "classifiers", "classify"],
    "validators": ["validator", "validators", "validate"],
    "persistence": ["persistence", "persist", "writer", "writers"],
    "readers": ["reader", "readers", "read"],
    "bridges": ["bridge", "bridges"],
    "orchestrators": ["orchestrator", "orchestrators"],
}

PROHIBITED_LAYER_IMPORT_HINTS = {
    "models": [
        ".persistence",
        ".writers",
        ".orchestrator",
        ".orchestrators",
    ],
    "normalizers": [
        ".persistence",
        ".writers",
        ".orchestrator",
    ],
    "classifiers": [
        ".persistence",
        ".writers",
        "sqlite3",
    ],
    "converters": [
        ".writers",
        ".persistence",
        "sqlite3",
    ],
    "validators": [
        ".writers",
        ".persistence",
        "sqlite3",
    ],
    "readers": [
        ".writers",
        ".persistence",
    ],
    "bridges": [
        ".writers",
        ".persistence",
    ],
}

# -----------------------------------------------------------------------------
# General helpers
# -----------------------------------------------------------------------------

def artifact_path(root: Path, artifact: str) -> Path:
    return root.joinpath(*artifact.split("/"))


def artifact_exists_with_alias(root: Path, artifact: str) -> Tuple[bool, Optional[str]]:
    canonical = artifact_path(root, artifact)
    if canonical.exists():
        return True, str(canonical)

    for alias in LOGICAL_ARTIFACT_ALIASES.get(artifact, []):
        alias_path = artifact_path(root, alias)
        if alias_path.exists():
            return True, str(alias_path)

    return False, None


def score_candidate(root: Path) -> RuntimeCandidate:
    matched: List[str] = []
    missing: List[str] = []

    score = 0

    for artifact, weight in ARTIFACT_WEIGHTS.items():
        exists, _matched_path = artifact_exists_with_alias(
            root,
            artifact,
        )

        if exists:
            matched.append(artifact)
            score += weight
        else:
            missing.append(artifact)

    if score >= 90:
        confidence = "high"
    elif score >= 60:
        confidence = "medium"
    elif score >= 40:
        confidence = "partial"
    else:
        confidence = "low"

    governance_score = 0

    #
    # Governance readiness hints
    #

    if FILE_SCAN_INVENTORY_DB_NAME in matched:
        governance_score += 25

    if CHART_ASSETS_DB_NAME in matched:
        governance_score += 25

    if CHART_PATTERNS_DB_NAME in matched:
        governance_score += 25

    if "mcp_server.py" in matched:
        governance_score += 25

    return RuntimeCandidate(
        root=str(root.resolve()),
        score=score,
        confidence=confidence,
        matched=matched,
        missing=missing,
        governance_score=governance_score,
    )

def discover_files(search_root: Path) -> Dict[str, List[str]]:
    patterns = {
        "main.py": "main.py",
        "recommend.py": "recommend.py",
        "app.py": "app.py",
        "runtime_meta.py": "runtime_meta.py",
        "mcp_server.py": "mcp_server.py",
        "runtime_verifier.py": "runtime_verifier.py",
    }

    discovered: Dict[str, List[str]] = {key: [] for key in patterns}

    try:
        for path in search_root.rglob("*"):
            if not path.is_file():
                continue

            for label, expected_name in patterns.items():
                if path.name == expected_name:
                    discovered[label].append(str(path.resolve()))
    except Exception:
        pass

    for key in discovered:
        discovered[key] = sorted(discovered[key])

    return discovered


def discover_package_dirs(search_root: Path) -> Dict[str, List[str]]:
    discovered: Dict[str, List[str]] = {
        "expected": [],
        "invalid_aliases": [],
        "other_rhythm_like": [],
    }

    try:
        for path in search_root.rglob("*"):
            if not path.is_dir():
                continue

            name = path.name

            if name == EXPECTED_PACKAGE:
                discovered["expected"].append(str(path.resolve()))
            elif name in INVALID_PACKAGE_ALIASES:
                discovered["invalid_aliases"].append(str(path.resolve()))
            elif "rhythm" in name.lower():
                discovered["other_rhythm_like"].append(str(path.resolve()))
    except Exception:
        pass

    for key in discovered:
        discovered[key] = sorted(discovered[key])

    return discovered

def discover_runtime_candidates(search_root: Path) -> List[RuntimeCandidate]:
    roots: Dict[str, Path] = {}

    try:
        for main_py in search_root.rglob("main.py"):
            root = main_py.parent.resolve()
            roots[str(root)] = root

        for rec_py in search_root.rglob("recommend.py"):
            parts = list(rec_py.parts)

            if "src" in parts:
                idx = parts.index("src")

                if idx > 0:
                    candidate = Path(*parts[:idx]).resolve()
                    roots[str(candidate)] = candidate

    except Exception:
        pass

    candidates = [
        score_candidate(root)
        for root in roots.values()
    ]

    candidates.sort(
        key=lambda candidate: (
            candidate.score,
            candidate.governance_score,
        ),
        reverse=True,
    )

    return candidates

def choose_backend_root(
    repo_root: Path,
    explicit_backend_root: Optional[Path],
) -> Tuple[Path, List[RuntimeCandidate], str]:
    if explicit_backend_root:
        candidate = score_candidate(explicit_backend_root.resolve())
        return explicit_backend_root.resolve(), [candidate], "explicit"

    candidates = discover_runtime_candidates(repo_root)

    if candidates:
        best = candidates[0]

        if best.score >= 60:
            return Path(best.root), candidates, "auto_discovered"

        return Path(best.root), candidates, "partial_discovery"

    return repo_root.resolve(), [], "fallback_to_repo_root"

def classify_import_failure(
    error_text: str,
    package_dirs: Dict[str, List[str]],
) -> str:
    if "No module named 'rhythm_ingestion'" in error_text:

        if (
            package_dirs.get("invalid_aliases")
            and not package_dirs.get("expected")
        ):
            return "package_name_mismatch"

        return "missing_pythonpath_or_package"

    if "No module named" in error_text:
        return "dependency_missing"

    if "cannot import name" in error_text:
        return "runtime_contract_break"

    return "import_failure"

def classify_asset_path(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix in TYPE_A_EXTENSIONS:
        return "type_A"

    if suffix in TYPE_B_EXTENSIONS:
        return "type_B"

    return "unknown"


def is_path_under_hint(
    path: Path,
    hints: List[str],
) -> bool:
    normalized = normalize_path_text(path)
    parts = [part.lower() for part in normalized.split("/")]
    lowered = normalized.lower()

    for hint in hints:
        hint_lower = hint.lower()

        if hint_lower in parts:
            return True

        if hint_lower in lowered:
            return True

    return False


def is_excluded_asset_path(path: Path) -> bool:
    normalized_name = path.name.lower()

    if is_path_under_hint(path, ASSET_SCOPE_EXCLUDE_ROOT_HINTS):
        return True

    for suffix in ASSET_SCOPE_EXCLUDE_FILENAME_SUFFIXES:
        if normalized_name.endswith(suffix.lower()):
            return True

    for token in ASSET_SCOPE_EXCLUDE_FILENAME_CONTAINS:
        if token.lower() in normalized_name:
            return True

    return False


def is_included_asset_path(path: Path) -> bool:
    if is_excluded_asset_path(path):
        return False

    # Keep true chart extensions even if they live outside explicit roots.
    # JSON/HTML/MHT are broader and should prefer scoped roots.
    suffix = path.suffix.lower()

    if suffix in {".aff", ".sus"}:
        return True

    if suffix in {".json", ".html", ".mht"}:
        return is_path_under_hint(path, ASSET_SCOPE_INCLUDE_ROOT_HINTS)

    if suffix in TYPE_B_EXTENSIONS:
        return True

    return False
    
def classify_excluded_asset_reason(path_text: str) -> str:
    normalized = path_text.replace("\\", "/").lower()

    if (
        "phase 4.5 - localization" in normalized
        or "/translations/" in normalized
        or "/locale" in normalized
    ):
        return "localization"

    if (
        "/schemas/" in normalized
        or normalized.endswith(".schema.json")
        or ".schema." in normalized
    ):
        return "schema"

    if (
        "/fixtures/" in normalized
        or "/test_cases/" in normalized
        or "/tests/" in normalized
        or "fixture_" in normalized
    ):
        return "fixture"

    if (
        "/registry/" in normalized
        or "template_registry" in normalized
        or "capability_registry" in normalized
    ):
        return "registry"

    if (
        "/.github/" in normalized
        or "/.vscode/" in normalized
        or "/tools/" in normalized
    ):
        return "tooling"

    if (
        "/artifacts/" in normalized
        or normalized.endswith("runtime_verifier_report.json")
        or normalized.endswith("runtime_verifier_report.md")
    ):
        return "generated_artifact"

    return "other"


def discover_asset_files(search_root: Path) -> Dict[str, Any]:
    excluded_by_reason: Dict[str, List[str]] = {
        "localization": [],
        "schema": [],
        "fixture": [],
        "registry": [],
        "tooling": [],
        "generated_artifact": [],
        "other": [],
    }

    discovered: Dict[str, Any] = {
        "type_A": [],
        "type_B": [],

        #
        # v1.0 evidence-volume refinement:
        #
        # Keep excluded candidates summarized by reason rather than
        # dumping every excluded path into the top-level report.
        #
        "excluded_candidate_count": 0,
        "excluded_candidates_sample": [],
        "excluded_candidates_truncated": False,
        "excluded_by_reason": {},
        "excluded_examples": {},

        "chart_assets_db": [],
        "file_scan_inventory_db": [],
        "chart_patterns_db": [],

        "artifact_databases": [],

        # v1.0 governance evidence
        "artifact_backbone_candidates": [],
    }

    max_excluded_examples = 50
    max_examples_per_reason = 10

    try:
        for path in search_root.rglob("*"):
            if not path.is_file():
                continue

            resolved = str(path.resolve())

            if path.name in ARTIFACT_DATABASE_NAMES:
                discovered["artifact_databases"].append(resolved)
                discovered["artifact_backbone_candidates"].append(resolved)

                if path.name == FILE_SCAN_INVENTORY_DB_NAME:
                    discovered["file_scan_inventory_db"].append(resolved)
                elif path.name == CHART_ASSETS_DB_NAME:
                    discovered["chart_assets_db"].append(resolved)
                elif path.name == CHART_PATTERNS_DB_NAME:
                    discovered["chart_patterns_db"].append(resolved)

                continue

            asset_type = classify_asset_path(path)

            if asset_type in {"type_A", "type_B"}:
                if is_included_asset_path(path):
                    discovered[asset_type].append(resolved)
                else:
                    reason = classify_excluded_asset_reason(resolved)
                    excluded_by_reason.setdefault(reason, []).append(resolved)

    except Exception:
        pass

    for key in [
        "type_A",
        "type_B",
        "chart_assets_db",
        "file_scan_inventory_db",
        "chart_patterns_db",
        "artifact_databases",
        "artifact_backbone_candidates",
    ]:
        discovered[key] = sorted(set(discovered.get(key, [])))

    excluded_flat: List[str] = sorted(
        item
        for values in excluded_by_reason.values()
        for item in values
    )

    discovered["excluded_candidate_count"] = len(excluded_flat)
    discovered["excluded_candidates_sample"] = excluded_flat[:max_excluded_examples]
    discovered["excluded_candidates_truncated"] = (
        len(excluded_flat) > max_excluded_examples
    )

    discovered["excluded_by_reason"] = {
        reason: len(values)
        for reason, values in excluded_by_reason.items()
    }

    discovered["excluded_examples"] = {
        reason: sorted(values)[:max_examples_per_reason]
        for reason, values in excluded_by_reason.items()
        if values
    }

    return discovered

def sha256_file(
    path: Path,
    chunk_size: int = 1024 * 1024,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def normalize_path_text(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip()


def table_quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def first_existing(
    columns: Iterable[str],
    candidates: List[str],
) -> Optional[str]:
    column_set = set(columns)

    for candidate in candidates:
        if candidate in column_set:
            return candidate

    return None


def sqlite_readonly_uri(path: Path) -> str:
    # Read-only SQLite URI. URL-encoding keeps paths with spaces/special characters stable.
    encoded_path = quote(path.resolve().as_posix(), safe="/:")
    return f"file:{encoded_path}?mode=ro"


def truncate_value(
    value: Any,
    limit: int = MAX_REPORT_SAMPLE_VALUE_LENGTH,
) -> Any:
    # Prevent large text_representation values from bloating JSON / Markdown reports.
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + "...<truncated>"

    return value


def truncate_row(
    row: Dict[str, Any],
    limit: int = MAX_REPORT_SAMPLE_VALUE_LENGTH,
) -> Dict[str, Any]:
    return {
        key: truncate_value(value, limit=limit)
        for key, value in row.items()
    }


def import_module_probe(module_name: str) -> Dict[str, Any]:
    try:
        module = importlib.import_module(module_name)

        return {
            "status": "pass",
            "file": getattr(module, "__file__", None),
        }

    except Exception as exc:
        return {
            "status": "fail",
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }


def read_text_safely(
    path: Path,
    limit: int = 200_000,
) -> str:
    try:
        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        if len(text) > limit:
            return text[:limit]

        return text

    except Exception:
        return ""

def governance_candidate_score(
    candidate: RuntimeCandidate,
) -> int:
    score = 0

    matched = set(candidate.matched)

    required = {
        FILE_SCAN_INVENTORY_DB_NAME,
        CHART_ASSETS_DB_NAME,
        CHART_PATTERNS_DB_NAME,
        "mcp_server.py",
    }

    score += len(
        required.intersection(matched)
    ) * 25

    return score
    
def classify_governance_failure_lineage(
    self,
    *,
    governance_failures: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:

    root_failures: List[Dict[str, Any]] = []
    derived_failures: List[Dict[str, Any]] = []

    failed_contract_types: Set[str] = {
        item.get("contract_type")
        for item in governance_failures
        if item.get("contract_type")
    }

    for item in governance_failures:
        contract_type = item.get(
            "contract_type",
        )

        if contract_type in GOVERNANCE_META_CONTRACT_TYPES:
            continue

        dependency_of = DERIVED_FAILURE_POLICY.get(
            contract_type,
        )

        #
        # If a contract is known to be derived, only render it as
        # derived when the upstream root failure is also present.
        #
        # If the upstream root is not currently failing, keep it as
        # a root failure so an independent issue is not hidden.
        #
        if (
            dependency_of
            and dependency_of in failed_contract_types
        ):
            derived_item = dict(item)
            derived_item["failure_class"] = "derived"
            derived_item["dependency_of"] = dependency_of

            derived_failures.append(
                derived_item,
            )
            continue

        root_item = dict(item)
        root_item["failure_class"] = "root"

        if dependency_of:
            root_item["expected_dependency_of"] = dependency_of
            root_item["lineage_note"] = (
                "This contract is usually derived, but its upstream "
                "root contract was not present in the current failure set."
            )

        root_failures.append(
            root_item,
        )

    return root_failures, derived_failures

# -----------------------------------------------------------------------------
# Verifier
# -----------------------------------------------------------------------------

class RuntimeVerifier:
    def __init__(
        self,
        *,
        repo_root: Path,
        backend_root: Optional[Path],
        api_url: str,
        token: Optional[str],
        mcp_config: Optional[Path],
        asset_db: Optional[Path],
        file_scan_inventory_db: Optional[Path],
        chart_assets_db: Optional[Path],
        chart_patterns_db: Optional[Path],
        run_rest: bool,
    ) -> None:
        self.repo_root = repo_root.resolve()

        self.backend_root, self.backend_candidates, self.backend_root_mode = choose_backend_root(
            self.repo_root,
            backend_root,
        )

        self.api_url = api_url
        self.token = token or os.getenv("SOFTR_API_TOKEN")
        self.mcp_config = mcp_config
        self.run_rest = run_rest

        # v0.6 compatibility.
        # asset_db means chart_assets.db unless explicitly overridden below.
        self.asset_db = asset_db

        # v0.7+ explicit artifact DB inputs.
        self.file_scan_inventory_db = file_scan_inventory_db
        self.chart_assets_db = chart_assets_db or asset_db
        self.chart_patterns_db = chart_patterns_db

        self.discovered_files = discover_files(self.repo_root)
        self.discovered_packages = discover_package_dirs(self.repo_root)
        self.discovered_assets = discover_asset_files(self.repo_root)

        self.results: List[CheckResult] = []

        # v0.6 compatibility cache.
        self.asset_db_snapshots: List[Dict[str, Any]] = []

        # v0.7+ artifact database caches.
        self.artifact_db_snapshots: Dict[str, List[Dict[str, Any]]] = {}
        self.artifact_db_records: Dict[str, List[Dict[str, Any]]] = {}

        self.repository_asset_hashes: Dict[str, str] = {}
        self.repository_file_hashes: Dict[str, str] = {}

        # ------------------------------------------------------------------
        # v1.0 governance state
        #
        # Governance must distinguish:
        #
        #   hint
        #       != suspicion
        #       != evidence
        #
        # Layer boundary governance should not automatically
        # escalate keyword matches into architecture blockers.
        #
        # Completed phases remain immutable.
        # Verifier remains read-only.
        # ------------------------------------------------------------------

        self.governance_state: Dict[str, Any] = {
            #
            # Top-level verdicts
            #
            "architecture_verdict": None,
            "runtime_verdict": None,
            "artifact_backbone_verdict": None,
            "flow_contract_verdict": None,
            "layer_boundary_verdict": None,
            "mcp_contract_verdict": None,
            "deletion_verdict": None,
            "governance_verdict": None,
            "root_failures": [],
            "derived_failures": [],

            #
            # Layer boundary audit telemetry
            #
            "layer_boundary_risk": {
                "status": None,
                "evidence_count": 0,
                "suspicion_count": 0,
                "hint_count": 0,
                "governance_blocking": False,
            },

            #
            # Governance accounting
            #
            "blocking_reasons": [],
            "warnings": [],

            #
            # Evidence confidence accounting
            #
            "confidence_summary": {
                "evidence": 0,
                "suspicion": 0,
                "hint": 0,
            },

            #
            # Audit policy metadata
            #
            "policy": {
                "completed_phases": "immutable",
                "verifier_mode": "read_only",
                "false_positive_isolation": True,
                "boundary_confidence_model": {
                    "hint": {
                        "governance_blocking": False,
                        "severity": "info",
                    },
                    "suspicion": {
                        "governance_blocking": False,
                        "severity": "warning",
                    },
                    "evidence": {
                        "governance_blocking": True,
                        "severity": "critical",
                    },
                },
            },
        }

    # ------------------------------------------------------------------
    # Result helpers
    # ------------------------------------------------------------------

    def classify(
        self,
        *,
        domain: str,
        check: str,
        base_status: str,
    ) -> Tuple[str, str]:
        if domain == "environment" and check == "softr_api_token_present":
            if self.token:
                return "pass", "info"

            if self.run_rest:
                return "fail", "fail"

            return "warning", "warning"

        if domain == "mcp" and check == "config_present" and base_status == "skipped":
            return "skipped", "info"

        if domain == "rest_api" and check == "rest_verification_enabled" and base_status == "skipped":
            return "skipped", "info"

        if domain == "repo" and base_status == "warning":
            if self.backend_root_mode in {"auto_discovered", "explicit", "partial_discovery"}:
                return "warning", "warning"

            return "fail", "fail"

        if domain == "flow_verification" and base_status == "skipped":
            return "skipped", "info"

        if domain == "flow_contract_verification" and base_status == "skipped":
            return "skipped", "info"

        if domain == "type_B_intelligence" and base_status == "skipped":
            return "skipped", "info"

        if domain == "artifact_databases" and base_status == "warning":
            return "warning", "warning"

        if domain == "dependency_reality":
            if base_status == "pass":
                return "pass", "info"

            if base_status == "warning":
                return "warning", "warning"

            if base_status == "fail":
                #
                # Dependency failure.
                #
                # Runtime blocker,
                # NOT governance blocker.
                #
                return "fail", "warning"
                
        if domain == "runtime_import":

            if base_status == "fail":
                #
                # Runtime import failure.
                #
                # Runtime blocker,
                # not architecture blocker.
                #
                return "fail", "warning"

        #
        # v1.0 governance severity rules.
        #
        
        if domain == "governance" and base_status == "warning":
            return "warning", "warning"
        
        if domain == "governance" and base_status == "fail":
            return "fail", "critical"

        if domain == "governance" and base_status == "critical":
            return "critical", "critical"

        if domain == "layer_separation":

            if base_status == "pass":
                return "pass", "info"

            if base_status == "info":
                return "info", "info"

            if base_status == "warning":
                return "warning", "warning"

            if base_status == "critical":
                #
                # Evidence-level boundary violation.
                #
                return "critical", "critical"

        if domain == "artifact_relationships" and base_status == "fail":
            return "fail", "fail"

        if domain == "artifact_backbone" and base_status == "fail":
            return "fail", "fail"

        if domain == "flow_contract_verification" and base_status == "fail":
            return "fail", "fail"

        if domain == "mcp_contract" and base_status == "fail":
            return "fail", "fail"

        mapping = {
            "pass": "info",
            "info": "info",
            "warning": "warning",
            "skipped": "info",
            "fail": "fail",
            "critical": "critical",
        }

        return base_status, mapping.get(base_status, "warning")

    def add(
        self,
        *,
        domain: str,
        check: str,
        status: str,
        summary: str,
        evidence: Optional[Dict[str, Any]] = None,
        suggested_fix: Optional[str] = None,
        governance_domain: Optional[str] = None,
        contract_type: Optional[str] = None,
    ) -> None:
        final_status, severity = self.classify(
            domain=domain,
            check=check,
            base_status=status,
        )

        result = CheckResult(
            domain=domain,
            check=check,
            status=final_status,
            severity=severity,
            summary=summary,
            evidence=evidence or {},
            suggested_fix=suggested_fix,
            governance_domain=governance_domain,
            contract_type=contract_type,
        )

        self.results.append(result)

        #
        # v1.0 lightweight governance state collection.
        # This does not make final decisions by itself; it records blockers
        # for later governance verdict generation.
        #
        if severity in {"fail", "critical"}:
            self.governance_state.setdefault("blocking_reasons", []).append(
                {
                    "domain": domain,
                    "check": check,
                    "severity": severity,
                    "summary": summary,
                    "governance_domain": governance_domain,
                    "contract_type": contract_type,
                }
            )

        elif final_status == "warning":
            self.governance_state.setdefault("warnings", []).append(
                {
                    "domain": domain,
                    "check": check,
                    "summary": summary,
                    "governance_domain": governance_domain,
                    "contract_type": contract_type,
                }
            )

    def inject_pythonpath(self) -> None:
        src = self.backend_root / "src"
        src_pkg = src / EXPECTED_PACKAGE

        for path in [src, src_pkg, self.backend_root]:
            path_text = str(path)

            if path_text not in sys.path:
                sys.path.insert(0, path_text)

    def read_json_file(
        self,
        path: Path,
    ) -> Optional[Dict[str, Any]]:
        try:
            data = json.loads(
                path.read_text(
                    encoding="utf-8",
                )
            )

            if isinstance(data, dict):
                return data

            self.add(
                domain="file",
                check="json_shape",
                status="fail",
                summary=f"JSON file is valid but does not contain an object: {path}",
                evidence={
                    "path": str(path),
                    "actual_type": type(data).__name__,
                },
            )

            return None

        except Exception as exc:
            self.add(
                domain="file",
                check="json_parse",
                status="fail",
                summary=f"Could not parse JSON file: {path}",
                evidence={
                    "path": str(path),
                    "error": str(exc),
                },
            )

            return None

    def post_json(
        self,
        payload: Dict[str, Any],
    ) -> Any:
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        request = urllib.request.Request(
            self.api_url,
            data=body,
            headers=headers,
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=15) as response:
            text = response.read().decode("utf-8", errors="replace")

            if not text:
                return {}

            return json.loads(text)
            
    def record_boundary_signal(
        self,
        *,
        confidence: str,
    ) -> None:

        summary = self.governance_state.setdefault(
            "confidence_summary",
            {},
        )

        summary[confidence] = (
            summary.get(confidence, 0)
            + 1
        )
    
    def update_layer_boundary_risk(
        self,
        *,
        evidence_count: int,
        suspicion_count: int,
        hint_count: int,
        status: str,
    ) -> None:

        self.governance_state["layer_boundary_risk"] = {
            "status": status,
            "evidence_count": evidence_count,
            "suspicion_count": suspicion_count,
            "hint_count": hint_count,
            "governance_blocking": evidence_count > 0,
        }

    # ------------------------------------------------------------------
    # Artifact DB candidate helpers
    # ------------------------------------------------------------------

    def resolve_artifact_db_candidates(
        self,
        db_name: str,
    ) -> List[Path]:
        candidates: List[Path] = []

        explicit_map: Dict[str, Optional[Path]] = {
            FILE_SCAN_INVENTORY_DB_NAME: self.file_scan_inventory_db,
            CHART_ASSETS_DB_NAME: self.chart_assets_db,
            CHART_PATTERNS_DB_NAME: self.chart_patterns_db,
        }

        explicit = explicit_map.get(db_name)

        if explicit:
            candidates.append(
                explicit.expanduser().resolve()
            )

        discovered_key_map = {
            FILE_SCAN_INVENTORY_DB_NAME: "file_scan_inventory_db",
            CHART_ASSETS_DB_NAME: "chart_assets_db",
            CHART_PATTERNS_DB_NAME: "chart_patterns_db",
        }

        discovered_key = discovered_key_map.get(db_name)

        if discovered_key:
            for item in self.discovered_assets.get(discovered_key, []):
                path = Path(item).resolve()

                if path not in candidates:
                    candidates.append(path)

        # Defensive fallback:
        # If repository discovery missed a DB, perform a direct filename search.
        if not candidates:
            try:
                for path in self.repo_root.rglob(db_name):
                    resolved = path.resolve()

                    if resolved not in candidates:
                        candidates.append(resolved)

            except Exception:
                pass

        return candidates
    

    def resolve_all_artifact_db_candidates(self) -> Dict[str, List[Path]]:
        return {
            db_name: self.resolve_artifact_db_candidates(db_name)
            for db_name in ARTIFACT_DATABASE_NAMES
        }

    # v0.6 compatibility.
    def resolve_asset_db_candidates(self) -> List[Path]:
        return self.resolve_artifact_db_candidates(CHART_ASSETS_DB_NAME)

    # ------------------------------------------------------------------
    # SQLite inspection helpers
    # ------------------------------------------------------------------

    def inspect_sqlite_readonly(
        self,
        path: Path,
        *,
        logical_name: Optional[str] = None,
        sample_limit: int = 5,
    ) -> Dict[str, Any]:
        evidence: Dict[str, Any] = {
            "logical_name": logical_name,
            "path": str(path),
            "exists": path.exists(),
            "readable": False,
            "tables": [],
            "table_columns": {},
            "table_row_counts": {},
            "table_samples": {},
            "candidate_columns": {},
            "read_mode": "sqlite_readonly",
        }

        if not path.exists():
            return evidence

        try:
            uri = sqlite_readonly_uri(path)

            with sqlite3.connect(uri, uri=True) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                tables = [
                    row[0]
                    for row in cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                    ).fetchall()
                ]

                evidence["readable"] = True
                evidence["tables"] = tables

                for table in tables:
                    quoted_table = table_quote(table)

                    columns = [
                        row[1]
                        for row in cursor.execute(
                            f"PRAGMA table_info({quoted_table})"
                        ).fetchall()
                    ]

                    evidence["table_columns"][table] = columns

                    evidence["candidate_columns"][table] = {
                        "path": first_existing(columns, PATH_COLUMN_CANDIDATES),
                        "hash": first_existing(columns, HASH_COLUMN_CANDIDATES),
                        "text": first_existing(columns, TEXT_COLUMN_CANDIDATES),
                        "reference_url": first_existing(columns, REFERENCE_URL_COLUMN_CANDIDATES),
                        "type": first_existing(columns, TYPE_COLUMN_CANDIDATES),
                        "pattern": first_existing(columns, PATTERN_COLUMN_CANDIDATES),
                        "chart_id": first_existing(columns, CHART_ID_COLUMN_CANDIDATES),
                        "timestamp": first_existing(columns, TIMESTAMP_COLUMN_CANDIDATES),
                    }

                    try:
                        count = cursor.execute(
                            f"SELECT COUNT(*) FROM {quoted_table}"
                        ).fetchone()[0]

                        evidence["table_row_counts"][table] = count

                    except Exception as exc:
                        evidence["table_row_counts"][table] = {
                            "error": str(exc),
                        }

                    try:
                        rows = cursor.execute(
                            f"SELECT * FROM {quoted_table} LIMIT ?",
                            (sample_limit,),
                        ).fetchall()

                        evidence["table_samples"][table] = [
                            truncate_row(dict(row))
                            for row in rows
                        ]

                    except Exception as exc:
                        evidence["table_samples"][table] = {
                            "error": str(exc),
                        }

        except Exception as exc:
            evidence["error"] = str(exc)
            evidence["traceback"] = traceback.format_exc()

        return evidence

    def get_artifact_db_snapshots(
        self,
        db_name: str,
    ) -> List[Dict[str, Any]]:
        if db_name not in self.artifact_db_snapshots:
            logical_name = ARTIFACT_DATABASE_LOGICAL_NAMES.get(
                db_name,
                db_name,
            )

            self.artifact_db_snapshots[db_name] = [
                self.inspect_sqlite_readonly(
                    path,
                    logical_name=logical_name,
                )
                for path in self.resolve_artifact_db_candidates(db_name)
            ]

        return self.artifact_db_snapshots[db_name]

    def get_all_artifact_db_snapshots(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            db_name: self.get_artifact_db_snapshots(db_name)
            for db_name in ARTIFACT_DATABASE_NAMES
        }

    # v0.6 compatibility.
    def get_asset_db_snapshots(self) -> List[Dict[str, Any]]:
        if not self.asset_db_snapshots:
            self.asset_db_snapshots = self.get_artifact_db_snapshots(
                CHART_ASSETS_DB_NAME
            )

        return self.asset_db_snapshots

    # ------------------------------------------------------------------
    # DB record iteration helpers
    # ------------------------------------------------------------------

    def iter_artifact_db_records(self, db_name: str) -> List[Dict[str, Any]]:
        if db_name in self.artifact_db_records:
            return self.artifact_db_records[db_name]

        records: List[Dict[str, Any]] = []

        for snapshot in self.get_artifact_db_snapshots(db_name):
            db_path = snapshot.get("path")
            if not db_path or snapshot.get("error") or not snapshot.get("exists"):
                continue

            try:
                uri = sqlite_readonly_uri(Path(db_path))
                with sqlite3.connect(uri, uri=True) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    for table in snapshot.get("tables", []):
                        columns = snapshot.get("table_columns", {}).get(table, [])
                        candidate_columns = snapshot.get("candidate_columns", {}).get(table, {})
                        quoted_table = table_quote(table)

                        selected_columns = [
                            column
                            for column in [
                                candidate_columns.get("path"),
                                candidate_columns.get("hash"),
                                candidate_columns.get("text"),
                                candidate_columns.get("reference_url"),
                                candidate_columns.get("type"),
                                candidate_columns.get("pattern"),
                                candidate_columns.get("chart_id"),
                                candidate_columns.get("timestamp"),
                            ]
                            if column
                        ]

                        if not selected_columns:
                            continue

                        select_sql = ", ".join(
                            table_quote(column)
                            for column in selected_columns
                        )

                        rows = cursor.execute(
                            f"SELECT {select_sql} FROM {quoted_table}"
                        ).fetchall()

                        for row in rows:
                            row_dict = dict(row)

                            records.append(
                                {
                                    "db_name": db_name,
                                    "logical_name": ARTIFACT_DATABASE_LOGICAL_NAMES.get(
                                        db_name,
                                        db_name,
                                    ),
                                    "db_path": db_path,

                                    "table": table,
                                    "columns": columns,

                                    "path": (
                                        row_dict.get(candidate_columns.get("path"))
                                        if candidate_columns.get("path")
                                        else None
                                    ),

                                    "hash": (
                                        row_dict.get(candidate_columns.get("hash"))
                                        if candidate_columns.get("hash")
                                        else None
                                    ),

                                    "text": (
                                        row_dict.get(candidate_columns.get("text"))
                                        if candidate_columns.get("text")
                                        else None
                                    ),

                                    "reference_url": (
                                        row_dict.get(candidate_columns.get("reference_url"))
                                        if candidate_columns.get("reference_url")
                                        else None
                                    ),

                                    "asset_type": (
                                        row_dict.get(candidate_columns.get("type"))
                                        if candidate_columns.get("type")
                                        else None
                                    ),

                                    "pattern": (
                                        row_dict.get(candidate_columns.get("pattern"))
                                        if candidate_columns.get("pattern")
                                        else None
                                    ),

                                    "chart_id": (
                                        row_dict.get(candidate_columns.get("chart_id"))
                                        if candidate_columns.get("chart_id")
                                        else None
                                    ),

                                    "timestamp": (
                                        row_dict.get(candidate_columns.get("timestamp"))
                                        if candidate_columns.get("timestamp")
                                        else None
                                    ),

                                    # v1.0 governance metadata
                                    "artifact_backbone_member": (
                                        db_name in ARTIFACT_DATABASE_NAMES
                                    ),
                                }
                            )

            except Exception:
                continue

        self.artifact_db_records[db_name] = records
        return records

    def iter_all_artifact_db_records(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            db_name: self.iter_artifact_db_records(db_name)
            for db_name in ARTIFACT_DATABASE_NAMES
        }

    # v0.6 compatibility.
    def iter_asset_db_records(self) -> List[Dict[str, Any]]:
        return self.iter_artifact_db_records(CHART_ASSETS_DB_NAME)

    def iter_file_scan_inventory_records(self) -> List[Dict[str, Any]]:
        return self.iter_artifact_db_records(FILE_SCAN_INVENTORY_DB_NAME)

    def iter_chart_pattern_records(self) -> List[Dict[str, Any]]:
        return self.iter_artifact_db_records(CHART_PATTERNS_DB_NAME)

    # ------------------------------------------------------------------
    # Hash helpers
    # ------------------------------------------------------------------

    def compute_repository_asset_hashes(self) -> Dict[str, str]:
        if self.repository_asset_hashes:
            return self.repository_asset_hashes

        paths = [Path(item) for item in self.discovered_assets.get("type_A", [])]
        paths += [Path(item) for item in self.discovered_assets.get("type_B", [])]

        hashes: Dict[str, str] = {}

        for path in paths:
            try:
                hashes[str(path.resolve())] = sha256_file(path)
            except Exception:
                continue

        self.repository_asset_hashes = hashes
        return hashes

    def compute_repository_file_hashes(self) -> Dict[str, str]:
        if self.repository_file_hashes:
            return self.repository_file_hashes

        hashes: Dict[str, str] = {}

        try:
            for path in self.repo_root.rglob("*"):
                if not path.is_file():
                    continue

                # Skip git internals and generated artifacts to avoid noisy reports.
                normalized = normalize_path_text(path)
                if "/.git/" in normalized or "/artifacts/" in normalized:
                    continue

                try:
                    hashes[str(path.resolve())] = sha256_file(path)
                except Exception:
                    continue
        except Exception:
            pass

        self.repository_file_hashes = hashes
        return hashes

    # ------------------------------------------------------------------
    # Preconditions / capability helpers
    # ------------------------------------------------------------------

    def package_import_probe_passed(self) -> bool:
        for result in self.results:
            if result.domain == "package_layout" and result.check == "package_import_probe":
                return result.status == "pass"
        return False

    def runtime_import_probe_passed(self) -> bool:
        for result in self.results:
            if result.domain == "runtime_import" and result.check == "recommend_module_importable":
                return result.status == "pass"
        return False

    def dependency_reality_passed(self) -> bool:
        for result in self.results:
            if result.domain == "dependency_reality" and result.check == "runtime_dependency_probe":
                return result.status == "pass"
        return False

    def artifact_db_has_readable_rows(self, db_name: str) -> bool:
        snapshots = self.get_artifact_db_snapshots(db_name)

        for snapshot in snapshots:
            if not snapshot.get("exists") or snapshot.get("error"):
                continue

            for count in snapshot.get("table_row_counts", {}).values():
                if isinstance(count, int) and count > 0:
                    return True

        return False

    def artifact_db_present(self, db_name: str) -> bool:
        return bool(self.resolve_artifact_db_candidates(db_name))
        
    def artifact_backbone_present(self) -> bool:
        return all(
            self.artifact_db_present(db_name)
            for db_name in ARTIFACT_DATABASE_NAMES
        )

    def readable_artifact_db_count(self) -> int:
        count = 0

        for db_name in ARTIFACT_DATABASE_NAMES:
            for snapshot in self.get_artifact_db_snapshots(db_name):
                if snapshot.get("exists") and snapshot.get("readable") and not snapshot.get("error"):
                    count += 1

        return count
        
    def artifact_backbone_readable(self) -> bool:
        for db_name in ARTIFACT_DATABASE_NAMES:

            snapshots = self.get_artifact_db_snapshots(
                db_name
            )

            if not snapshots:
                return False

            readable = any(
                snapshot.get("exists")
                and snapshot.get("readable")
                and not snapshot.get("error")
                for snapshot in snapshots
            )

            if not readable:
                return False

        return True
        
    def artifact_relationship_readiness(self) -> Dict[str, bool]:
        return {
            "scan_db_has_rows": self.artifact_db_has_readable_rows(
                FILE_SCAN_INVENTORY_DB_NAME
            ),

            "asset_db_has_rows": self.artifact_db_has_readable_rows(
                CHART_ASSETS_DB_NAME
            ),

            "pattern_db_has_rows": self.artifact_db_has_readable_rows(
                CHART_PATTERNS_DB_NAME
            ),
        }
        
    def governance_readiness_snapshot(self) -> Dict[str, Any]:
        relationship_state = (
            self.artifact_relationship_readiness()
        )

        return {
            "artifact_backbone_present":
                self.artifact_backbone_present(),

            "artifact_backbone_readable":
                self.artifact_backbone_readable(),

            "relationship_state":
                relationship_state,

            "relationship_ready":
                all(relationship_state.values()),
        }

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def check_environment(self) -> None:
        self.add(
            domain="environment",
            check="python_runtime",
            status="info",
            summary="Python runtime information captured.",
            evidence={
                "python_executable": sys.executable,
                "python_version": sys.version,
                "platform": platform.platform(),
            },
        )

        token_present = bool(self.token)

        self.add(
            domain="environment",
            check="softr_api_token_present",
            status="pass" if token_present else "fail",
            summary=(
                "SOFTR_API_TOKEN is available to the verifier process."
                if token_present
                else "SOFTR_API_TOKEN is missing. This blocks REST checks only when --rest is enabled."
            ),
            evidence={
                "token_present": token_present,
                "rest_checks_enabled": self.run_rest,
            },
            suggested_fix=(
                None
                if token_present
                else "Set SOFTR_API_TOKEN or pass --token when running REST verification."
            ),
        )

    def check_repository_discovery(self) -> None:
        candidates = [asdict(candidate) for candidate in self.backend_candidates]
        best = candidates[0] if candidates else None

        if self.backend_root_mode == "auto_discovered":
            status = "pass"
            summary = "Backend root was discovered with sufficient confidence."
        elif self.backend_root_mode == "partial_discovery":
            status = "warning"
            summary = "Partial runtime candidate was discovered."
        elif self.backend_root_mode == "explicit":
            status = "pass"
            summary = "Backend root was provided explicitly."
        else:
            status = "fail"
            summary = "No runtime candidate was discovered; verifier is falling back to repo root."

        self.add(
            domain="repository_discovery",
            check="runtime_candidate_confidence",
            status=status,
            summary=summary,
            evidence={
                "repo_root": str(self.repo_root),
                "selected_backend_root": str(self.backend_root),
                "mode": self.backend_root_mode,
                "best_candidate": best,
                "all_candidates": candidates,
                "discovered_files": self.discovered_files,
                "discovered_packages": self.discovered_packages,
                "discovered_assets": self.discovered_assets,
            },
            suggested_fix=(
                None
                if status == "pass"
                else "Ensure backend root contains main.py, mcp_server.py, and importable src/rhythm_ingestion package files."
            ),
            governance_domain="architecture_contracts",
            contract_type="repository_discovery",
        )

    def check_repository_vs_runtime(self) -> None:
        canonical_package_root = self.backend_root / "src" / EXPECTED_PACKAGE

        repository_reality = {
            "backend_root_exists": self.backend_root.exists(),
            "canonical_package_root_exists": canonical_package_root.exists(),
            "main_py_exists": (self.backend_root / "main.py").exists(),
            "mcp_server_py_exists": (self.backend_root / "mcp_server.py").exists(),
            "artifact_database_candidates": {
                db_name: [str(path) for path in paths]
                for db_name, paths in self.resolve_all_artifact_db_candidates().items()
            },
        }

        import_reality: Dict[str, Any] = {
            "rhythm_ingestion_importable": None,
            "rhythm_ingestion_file": None,
            "error": None,
        }

        self.inject_pythonpath()

        try:
            module = importlib.import_module(EXPECTED_PACKAGE)
            import_reality["rhythm_ingestion_importable"] = True
            import_reality["rhythm_ingestion_file"] = getattr(module, "__file__", None)
        except Exception as exc:
            import_reality["rhythm_ingestion_importable"] = False
            import_reality["error"] = str(exc)

        runtime_reality = {
            "recommend_module_discovered": bool(self.discovered_files.get("recommend.py")),
            "runtime_meta_discovered": bool(self.discovered_files.get("runtime_meta.py")),
            "selected_backend_root": str(self.backend_root),
        }

        status = "pass"
        summary = "Repository, import, and runtime realities are distinguishable."

        if not repository_reality["canonical_package_root_exists"]:
            status = "fail"
            summary = "Repository reality does not show the canonical package root."
        elif import_reality["rhythm_ingestion_importable"] is False:
            status = "fail"
            summary = "Repository package exists but import reality failed."

        self.add(
            domain="repository_vs_runtime",
            check="reality_separation",
            status=status,
            summary=summary,
            evidence={
                "repository_reality": repository_reality,
                "import_reality": import_reality,
                "runtime_reality": runtime_reality,
            },
            suggested_fix=(
                None
                if status == "pass"
                else "Resolve package root and PYTHONPATH before diagnosing runtime wiring."
            ),
            governance_domain="architecture_contracts",
            contract_type="repository_import_runtime_separation",
        )

    def check_package_layout(self) -> None:
        expected_dirs = self.discovered_packages.get("expected", [])
        invalid_dirs = self.discovered_packages.get("invalid_aliases", [])
        other_dirs = self.discovered_packages.get("other_rhythm_like", [])

        self.add(
            domain="package_layout",
            check="package_directory_inventory",
            status="info",
            summary="Rhythm-related package directories inventoried.",
            evidence={
                "expected_package": EXPECTED_PACKAGE,
                "expected_dirs": expected_dirs,
                "invalid_alias_dirs": invalid_dirs,
                "other_rhythm_like_dirs": other_dirs,
            },
            governance_domain="architecture_contracts",
            contract_type="package_layout_inventory",
        )

        if invalid_dirs:
            self.add(
                domain="package_layout",
                check="package_alias_detection",
                status="fail",
                summary="Invalid package directory alias detected.",
                evidence={
                    "expected": EXPECTED_PACKAGE,
                    "invalid_aliases": INVALID_PACKAGE_ALIASES,
                    "invalid_alias_dirs": invalid_dirs,
                },
                suggested_fix=(
                    "Rename invalid package directory to src/rhythm_ingestion, "
                    "or restore the canonical Python package path."
                ),
                governance_domain="architecture_contracts",
                contract_type="package_identity",
            )
        else:
            self.add(
                domain="package_layout",
                check="package_alias_detection",
                status="pass",
                summary="No invalid rhythm package alias directory was detected.",
                evidence={
                    "expected": EXPECTED_PACKAGE,
                    "invalid_aliases": INVALID_PACKAGE_ALIASES,
                },
                governance_domain="architecture_contracts",
                contract_type="package_identity",
            )

        canonical_src = self.backend_root / "src"
        canonical_pkg = canonical_src / EXPECTED_PACKAGE

        self.add(
            domain="package_layout",
            check="package_root_resolution",
            status="pass" if canonical_pkg.exists() else "fail",
            summary=(
                "Canonical package root exists."
                if canonical_pkg.exists()
                else "Canonical package root does not exist at selected backend root."
            ),
            evidence={
                "backend_root": str(self.backend_root),
                "expected_src": str(canonical_src),
                "expected_package_root": str(canonical_pkg),
                "exists": canonical_pkg.exists(),
            },
            suggested_fix=(
                None
                if canonical_pkg.exists()
                else "Ensure src/rhythm_ingestion exists under the selected backend root."
            ),
            governance_domain="architecture_contracts",
            contract_type="package_root_resolution",
        )

    def check_package_import_probe(self) -> None:
        self.inject_pythonpath()

        probes = [
            "rhythm_ingestion",
            "rhythm_ingestion.api",
            "rhythm_ingestion.runtime_meta",
        ]

        results: Dict[str, Dict[str, Any]] = {}
        any_fail = False
        dependency_failures: List[str] = []

        for module_name in probes:
            try:
                module = importlib.import_module(module_name)
                results[module_name] = {
                    "status": "pass",
                    "file": getattr(module, "__file__", None),
                }
            except Exception as exc:
                any_fail = True
                failure_type = classify_import_failure(
                    str(exc),
                    self.discovered_packages,
                )

                if failure_type == "dependency_missing":
                    dependency_failures.append(str(exc))

                results[module_name] = {
                    "status": "fail",
                    "error": str(exc),
                    "root_cause": failure_type,
                    "traceback": traceback.format_exc(),
                }

        if any_fail and dependency_failures:
            suggested_fix = (
                "Install or expose missing runtime dependencies before treating this as a package layout issue. "
                "The package root may be valid while downstream imports fail."
            )
        elif any_fail:
            suggested_fix = (
                "Fix package directory name and PYTHONPATH. "
                "Expected canonical package: src/rhythm_ingestion."
            )
        else:
            suggested_fix = None

        self.add(
            domain="package_layout",
            check="package_import_probe",
            status="fail" if any_fail else "pass",
            summary=(
                "One or more package import probes failed."
                if any_fail
                else "Package import probes passed."
            ),
            evidence={
                "sys_path_prefix": sys.path[:5],
                "results": results,
                "dependency_failures": dependency_failures,
            },
            suggested_fix=suggested_fix,
            governance_domain="architecture_contracts",
            contract_type="import_reality",
        )

    def check_dependency_reality(self) -> None:
        self.inject_pythonpath()

        required_results: Dict[str, Dict[str, Any]] = {}
        optional_results: Dict[str, Dict[str, Any]] = {}
        api_runtime_results: Dict[str, Dict[str, Any]] = {}

        required_missing: List[str] = []
        api_runtime_missing: List[str] = []

        for module_name in REQUIRED_RUNTIME_DEPENDENCY_MODULES:
            result = import_module_probe(module_name)
            required_results[module_name] = result

            if result.get("status") != "pass":
                required_missing.append(module_name)

        for module_name in OPTIONAL_RUNTIME_DEPENDENCY_MODULES:
            result = import_module_probe(module_name)
            optional_results[module_name] = result

        for module_name in API_RUNTIME_DEPENDENCY_MODULES:
            result = import_module_probe(module_name)
            api_runtime_results[module_name] = result

            if result.get("status") != "pass":
                api_runtime_missing.append(module_name)

        if required_missing:
            status = "fail"
            summary = (
                "One or more required runtime dependencies are missing."
            )

            runtime_impact = "blocked_by_dependency"

        elif api_runtime_missing:
            status = "warning"
            summary = (
                "One or more API runtime dependencies are missing."
            )

            runtime_impact = "capability_reduced"

        else:
            status = "pass"
            summary = (
                "Required runtime dependencies are importable."
            )

            runtime_impact = "ready"

        self.add(
            domain="dependency_reality",
            check="runtime_dependency_probe",
            status=status,
            summary=summary,
            evidence={
                "runtime_impact":
                    runtime_impact,

                "required_modules":
                    REQUIRED_RUNTIME_DEPENDENCY_MODULES,

                "optional_modules":
                    OPTIONAL_RUNTIME_DEPENDENCY_MODULES,

                "api_runtime_modules":
                    API_RUNTIME_DEPENDENCY_MODULES,

                "required_results":
                    required_results,

                "optional_results":
                    optional_results,

                "api_runtime_results":
                    api_runtime_results,

                "required_missing":
                    required_missing,

                "api_runtime_missing":
                    api_runtime_missing,

                "dependency_classification": {
                    "required_missing":
                        "runtime_blocker",

                    "api_runtime_missing":
                        "capability_reduction",

                    "optional_missing":
                        "non_blocking",
                },

                "governance_note":
                    (
                        "Dependency failures should influence "
                        "runtime readiness but should not "
                        "automatically become governance failures."
                    ),
            },
            suggested_fix=(
                None
                if status == "pass"
                else (
                    "Install missing runtime dependencies or "
                    "adjust CI setup before running runtime/API verification."
                )
            ),
            governance_domain="runtime_dependencies",
            contract_type="dependency_reality",
        )

    def check_repo_shape(self) -> None:
        expected = {
            "main.py": self.backend_root / "main.py",
            "src": self.backend_root / "src",
            "api_recommend.py": self.backend_root / "src" / EXPECTED_PACKAGE / "api" / "recommend.py",
            "api_app.py": self.backend_root / "src" / EXPECTED_PACKAGE / "api" / "app.py",
            "runtime_meta.py": self.backend_root / "src" / EXPECTED_PACKAGE / "runtime_meta.py",
            "mcp_server.py": self.backend_root / "mcp_server.py",
        }

        for name, path in expected.items():
            exists = path.exists()

            self.add(
                domain="repo",
                check=f"exists_{name}",
                status="pass" if exists else "warning",
                summary=f"{name} {'exists' if exists else 'was not found'} at selected backend root.",
                evidence={
                    "path": str(path),
                    "exists": exists,
                    "backend_root": str(self.backend_root),
                },
                governance_domain="architecture_contracts",
                contract_type="repository_shape",
            )

    def check_python_imports(self) -> None:
        self.inject_pythonpath()

        try:
            recommend = importlib.import_module("rhythm_ingestion.api.recommend")
            router = getattr(recommend, "router", None)
            games_rec = getattr(recommend, "_GAMES_RECOMMENDER", None)
            orchestrator = getattr(recommend, "_ORCHESTRATOR", None)

            self.add(
                domain="runtime_import",
                check="recommend_module_importable",
                status="pass",
                summary="rhythm_ingestion.api.recommend imported successfully.",
                evidence={
                    "module_file": getattr(recommend, "__file__", None),
                    "router_type": str(type(router)),
                    "router_has_recommend_games": hasattr(router, "recommend_games"),
                    "games_recommender_is_none": games_rec is None,
                    "games_recommender_type": str(type(games_rec)),
                    "orchestrator_is_none": orchestrator is None,
                    "orchestrator_type": str(type(orchestrator)),
                    "backend_root": str(self.backend_root),
                },
                governance_domain="architecture_contracts",
                contract_type="runtime_import_reality",
            )

            if games_rec is None:
                self.add(
                    domain="runtime_wiring",
                    check="games_recommender_present",
                    status="fail",
                    summary="Games recommender is not injected into the Phase 6 API runtime.",
                    evidence={
                        "_GAMES_RECOMMENDER": None,
                        "expected_wiring": "create_app(..., games_recommender=...)",
                        "boundary_note": (
                            "This check verifies wiring only. It must not modify "
                            "Phase 6 or Phase 7 recommendation internals."
                        ),
                    },
                    suggested_fix=(
                        "Inject a Phase 7 games_recommender through "
                        "create_app(..., games_recommender=...) in the runtime builder."
                    ),
                    governance_domain="architecture_contracts",
                    contract_type="runtime_wiring",
                )
            else:
                self.add(
                    domain="runtime_wiring",
                    check="games_recommender_present",
                    status="pass",
                    summary="Games recommender appears to be injected.",
                    evidence={
                        "games_recommender_type": str(type(games_rec)),
                    },
                    governance_domain="architecture_contracts",
                    contract_type="runtime_wiring",
                )

        except Exception as exc:
            failure_type = classify_import_failure(str(exc), self.discovered_packages)

            if failure_type == "dependency_missing":
                suggested_fix = (
                    "Runtime module exists but a dependency is missing. "
                    "Run dependency_reality checks and install missing packages before diagnosing wiring."
                )
            else:
                suggested_fix = (
                    "Verify package layout and PYTHONPATH. "
                    "Expected importable package path: src/rhythm_ingestion."
                )

            self.add(
                domain="runtime_import",
                check="recommend_module_importable",
                status="fail",
                summary="Failed to import rhythm_ingestion.api.recommend.",
                evidence={
                    "error": str(exc),
                    "root_cause": failure_type,
                    "traceback": traceback.format_exc(),
                },
                suggested_fix=suggested_fix,
                governance_domain="architecture_contracts",
                contract_type="runtime_import_reality",
            )

    def check_runtime_meta_specs(self) -> None:
        self.inject_pythonpath()

        try:
            runtime_meta = importlib.import_module("rhythm_ingestion.runtime_meta")
            specs = getattr(runtime_meta, "ARTIFACT_SPECS", {})

            required = [
                "song_recommendation_meta",
                "game_recommendation_meta",
                "recommendation_meta",
                "personalization_meta",
                "localization_meta",
            ]

            # v1.0 artifact/runtime-adjacent expectations.
            # These remain verification-only. Missing keys are reported;
            # this verifier must not modify runtime_meta.py automatically.
            artifact_expected = [
                "file_scan_state",
                "song_db",
                "song_db_meta",
                "tips_meta",
            ]

            missing = [
                key
                for key in required
                if key not in specs
            ]

            artifact_missing = [
                key
                for key in artifact_expected
                if key not in specs
            ]

            if missing:
                status = "fail"
                summary = "Some required runtime metadata artifact specs are missing."
            elif artifact_missing:
                status = "warning"
                summary = "Core runtime specs exist, but some artifact-adjacent specs are missing."
            else:
                status = "pass"
                summary = "Required runtime metadata artifact specs are registered."

            self.add(
                domain="runtime_meta",
                check="artifact_specs",
                status=status,
                summary=summary,
                evidence={
                    "required": required,
                    "artifact_expected": artifact_expected,
                    "missing": missing,
                    "artifact_missing": artifact_missing,
                    "registered": (
                        sorted(list(specs.keys()))
                        if isinstance(specs, dict)
                        else []
                    ),
                    "boundary_note": (
                        "Runtime metadata is inspected as a contract surface. "
                        "The verifier must not rewrite runtime_meta.py."
                    ),
                },
                suggested_fix=(
                    None
                    if status == "pass"
                    else "Add missing artifact keys to ARTIFACT_SPECS in runtime_meta.py if they are intended runtime artifacts."
                ),
                governance_domain="architecture_contracts",
                contract_type="runtime_metadata_contract",
            )

        except Exception as exc:
            failure_type = classify_import_failure(str(exc), self.discovered_packages)

            self.add(
                domain="runtime_meta",
                check="artifact_specs",
                status="fail",
                summary="Could not inspect runtime_meta.ARTIFACT_SPECS.",
                evidence={
                    "error": str(exc),
                    "root_cause": failure_type,
                    "traceback": traceback.format_exc(),
                },
                governance_domain="architecture_contracts",
                contract_type="runtime_metadata_contract",
            )

    def check_asset_scope_policy(self) -> None:
        scoped_type_a = self.discovered_assets.get("type_A", [])
        scoped_type_b = self.discovered_assets.get("type_B", [])

        excluded_total = int(
            self.discovered_assets.get(
                "excluded_candidate_count",
                0,
            )
        )

        excluded_by_reason = self.discovered_assets.get(
            "excluded_by_reason",
            {},
        )

        excluded_examples = self.discovered_assets.get(
            "excluded_examples",
            {},
        )

        scoped_total = len(scoped_type_a) + len(scoped_type_b)

        if scoped_total > 0:
            status = "pass"
            summary = "Asset scope policy identified scoped asset candidates."

        elif excluded_total > 0:
            #
            # v1.0 refinement:
            #
            # If all asset-like files are excluded by explicit policy,
            # this is informational evidence, not automatically a warning.
            #
            status = "info"
            summary = (
                "Asset-like files were found, but all were excluded by "
                "explicit asset scope policy."
            )

        else:
            status = "info"
            summary = "No scoped asset candidates were discovered."

        self.add(
            domain="asset_scope_policy",
            check="scoped_asset_inventory",
            status=status,
            summary=summary,
            evidence={
                "strategy":
                    "explicit_scope_with_exclusions",

                "type_A_scoped_count":
                    len(scoped_type_a),

                "type_B_scoped_count":
                    len(scoped_type_b),

                "excluded_candidate_count":
                    excluded_total,

                #
                # Keep scoped files because they are usually the useful
                # positive evidence.
                #
                "type_A_scoped_files":
                    scoped_type_a,

                "type_B_scoped_files":
                    scoped_type_b,

                #
                # v1.0 evidence-volume refinement:
                #
                # Do not dump every excluded candidate into the report.
                # Summarize by reason and provide small examples instead.
                #
                "excluded_by_reason":
                    excluded_by_reason,

                "excluded_examples":
                    excluded_examples,

                "include_root_hints":
                    ASSET_SCOPE_INCLUDE_ROOT_HINTS,

                "exclude_root_hints":
                    ASSET_SCOPE_EXCLUDE_ROOT_HINTS,

                "exclude_filename_suffixes":
                    ASSET_SCOPE_EXCLUDE_FILENAME_SUFFIXES,

                "exclude_filename_contains":
                    ASSET_SCOPE_EXCLUDE_FILENAME_CONTAINS,

                "evidence_volume_policy": {
                    "full_excluded_candidate_dump": False,
                    "examples_per_reason": 10,
                    "reason_summary_required": True,
                },

                "note": (
                    "Repository files are not automatically chart assets. "
                    "v1.0 keeps asset scope explicit so schema, config, "
                    "fixture, registry, generated artifact, and localization "
                    "JSON files are not treated as chart assets by default."
                ),
            },
            suggested_fix=(
                None
                if scoped_total > 0 or excluded_total > 0
                else (
                    "If chart assets are expected, place them under explicit "
                    "asset/chart roots or update the asset scope policy if "
                    "the repository intentionally uses another location."
                )
            ),
            governance_domain="artifact_backbone",
            contract_type="asset_scope_policy",
        )

    def check_artifact_databases(self) -> None:
        snapshots_by_db = self.get_all_artifact_db_snapshots()
        candidates_by_db = self.resolve_all_artifact_db_candidates()

        db_status: Dict[str, Dict[str, Any]] = {}
        missing: List[str] = []
        unreadable: List[str] = []
        empty: List[str] = []

        for db_name in ARTIFACT_DATABASE_NAMES:
            candidates = candidates_by_db.get(db_name, [])
            snapshots = snapshots_by_db.get(db_name, [])

            exists_count = len(
                [
                    snapshot
                    for snapshot in snapshots
                    if snapshot.get("exists")
                ]
            )

            readable_count = len(
                [
                    snapshot
                    for snapshot in snapshots
                    if snapshot.get("exists")
                    and snapshot.get("readable")
                    and not snapshot.get("error")
                ]
            )

            row_count_total = 0

            for snapshot in snapshots:
                for count in snapshot.get("table_row_counts", {}).values():
                    if isinstance(count, int):
                        row_count_total += count

            if not candidates:
                missing.append(db_name)
            elif readable_count == 0:
                unreadable.append(db_name)
            elif row_count_total == 0:
                empty.append(db_name)

            db_status[db_name] = {
                "logical_name": ARTIFACT_DATABASE_LOGICAL_NAMES.get(db_name, db_name),
                "candidate_count": len(candidates),
                "candidates": [str(path) for path in candidates],
                "exists_count": exists_count,
                "readable_count": readable_count,
                "row_count_total": row_count_total,
                "snapshots": snapshots,
            }

        if missing:
            status = "fail"
            summary = "One or more required artifact databases are missing."
        elif unreadable:
            status = "fail"
            summary = "One or more artifact databases were found but are not readable."
        elif empty:
            status = "warning"
            summary = "All required artifact databases are present/readable, but one or more appear empty."
        else:
            status = "pass"
            summary = "Required artifact databases are present, readable, and contain rows."

        self.add(
            domain="artifact_databases",
            check="artifact_database_policy",
            status=status,
            summary=summary,
            evidence={

                #
                # Required backbone
                #

                "required_databases":
                    ARTIFACT_DATABASE_NAMES,

                "relationship_chain":
                    ARTIFACT_RELATIONSHIP_CHAIN,

                #
                # Findings
                #

                "missing":
                    missing,

                "unreadable":
                    unreadable,

                "empty":
                    empty,

                "database_status":
                    db_status,

                #
                # Verification policy
                #

                "role":
                    "root_contract",

                "read_mode":
                    "sqlite_readonly",

                "allowed_operations": [
                    "schema_inventory",
                    "readability_check",
                    "record_count",
                    "relationship_verification",
                ],

                "prohibited_operations": [
                    "insert",
                    "update",
                    "delete",
                    "schema_mutation",
                ],

                #
                # Governance cascade awareness
                #

                "derived_failures_if_missing": [
                    "artifact_relationships",
                    "artifact_backbone_contract",
                    "asset_coverage",
                    "hash_integrity",
                    "type_A_usability",
                    "runtime_artifact_readiness",
                ],

                #
                # Notes
                #

                "policy_note": (
                    "This check acts as a root artifact-backbone contract. "
                    "Missing or unreadable artifact databases may cause "
                    "derived failures in downstream artifact verification "
                    "domains."
                ),

                "governance_note": (
                    "Artifact database failures should be rendered as root "
                    "failures. Downstream contract failures should be marked "
                    "as derived whenever caused by missing backbone databases."
                ),
            },
            suggested_fix=(
                None
                if status == "pass"
                else (
                    "Create or provide file_scan_inventory.db, "
                    "chart_assets.db, and chart_patterns.db, then "
                    "ensure each database is readable and populated."
                )
            ),
            governance_domain="artifact_backbone",
            contract_type="artifact_database_policy",
        )

    def check_artifact_relationships(self) -> None:
        scan_records = self.iter_file_scan_inventory_records()
        asset_records = self.iter_asset_db_records()
        pattern_records = self.iter_chart_pattern_records()

        scan_paths = {
            normalize_path_text(record.get("path"))
            for record in scan_records
            if normalize_path_text(record.get("path"))
        }

        asset_paths = {
            normalize_path_text(record.get("path"))
            for record in asset_records
            if normalize_path_text(record.get("path"))
        }

        pattern_paths = {
            normalize_path_text(record.get("path"))
            for record in pattern_records
            if normalize_path_text(record.get("path"))
        }

        asset_chart_ids = {
            str(record.get("chart_id") or "").strip()
            for record in asset_records
            if str(record.get("chart_id") or "").strip()
        }

        pattern_chart_ids = {
            str(record.get("chart_id") or "").strip()
            for record in pattern_records
            if str(record.get("chart_id") or "").strip()
        }

        scan_to_asset_matches: Set[str] = set()
        orphan_scans: List[str] = []

        for scan_path in sorted(scan_paths):
            matched = False
            for asset_path in asset_paths:
                if (
                    scan_path == asset_path
                    or scan_path.endswith(asset_path)
                    or asset_path.endswith(Path(scan_path).name)
                ):
                    matched = True
                    scan_to_asset_matches.add(asset_path)
                    break

            if not matched:
                orphan_scans.append(scan_path)

        orphan_assets_from_scan = sorted([path for path in asset_paths if path not in scan_to_asset_matches])

        asset_to_pattern_path_matches: Set[str] = set()
        orphan_assets_without_patterns: List[str] = []

        for asset_path in sorted(asset_paths):
            matched = False
            for pattern_path in pattern_paths:
                if (
                    asset_path == pattern_path
                    or asset_path.endswith(pattern_path)
                    or pattern_path.endswith(Path(asset_path).name)
                ):
                    matched = True
                    asset_to_pattern_path_matches.add(pattern_path)
                    break

            if not matched:
                orphan_assets_without_patterns.append(asset_path)

        orphan_patterns_by_path = sorted([path for path in pattern_paths if path not in asset_to_pattern_path_matches])

        asset_to_pattern_id_matches = asset_chart_ids.intersection(pattern_chart_ids)
        orphan_asset_chart_ids = sorted([item for item in asset_chart_ids if item not in pattern_chart_ids])
        orphan_pattern_chart_ids = sorted([item for item in pattern_chart_ids if item not in asset_chart_ids])

        scan_to_asset_coverage = 100.0 if not scan_paths else round(
            ((len(scan_paths) - len(orphan_scans)) / len(scan_paths)) * 100,
            2,
        )

        asset_to_pattern_coverage_by_path = 100.0 if not asset_paths else round(
            ((len(asset_paths) - len(orphan_assets_without_patterns)) / len(asset_paths)) * 100,
            2,
        )

        id_relationship_available = bool(asset_chart_ids or pattern_chart_ids)
        asset_to_pattern_coverage_by_id = (
            100.0
            if not asset_chart_ids
            else round((len(asset_to_pattern_id_matches) / len(asset_chart_ids)) * 100, 2)
        )

        scan_db_ready = self.artifact_db_has_readable_rows(FILE_SCAN_INVENTORY_DB_NAME)
        asset_db_ready = self.artifact_db_has_readable_rows(CHART_ASSETS_DB_NAME)
        pattern_db_ready = self.artifact_db_has_readable_rows(CHART_PATTERNS_DB_NAME)

        pass_condition = (
            scan_db_ready
            and asset_db_ready
            and pattern_db_ready
            and not orphan_scans
            and not orphan_assets_from_scan
            and (
                not asset_paths
                or not orphan_assets_without_patterns
                or (
                    id_relationship_available
                    and not orphan_asset_chart_ids
                    and not orphan_pattern_chart_ids
                )
            )
        )

        if pass_condition:
            status = "pass"
            summary = "Artifact relationship chain is complete."
        else:
            status = "fail"
            summary = "Artifact relationship chain has missing links or orphan records."

        self.add(
            domain="artifact_relationships",
            check="artifact_relationship_chain",
            status=status,
            summary=summary,
            evidence={
                "relationship_chain": ARTIFACT_RELATIONSHIP_CHAIN,

                "scan_db_ready": scan_db_ready,
                "asset_db_ready": asset_db_ready,
                "pattern_db_ready": pattern_db_ready,

                "scan_record_count": len(scan_records),
                "asset_record_count": len(asset_records),
                "pattern_record_count": len(pattern_records),

                "scan_path_count": len(scan_paths),
                "asset_path_count": len(asset_paths),
                "pattern_path_count": len(pattern_paths),

                "scan_to_asset_coverage": scan_to_asset_coverage,

                "asset_to_pattern_coverage_by_path":
                    asset_to_pattern_coverage_by_path,

                "asset_chart_id_count":
                    len(asset_chart_ids),

                "pattern_chart_id_count":
                    len(pattern_chart_ids),

                "asset_to_pattern_id_match_count":
                    len(asset_to_pattern_id_matches),

                "asset_to_pattern_coverage_by_id":
                    asset_to_pattern_coverage_by_id,

                "orphan_scans": orphan_scans,
                "orphan_assets_from_scan": orphan_assets_from_scan,

                "orphan_assets_without_patterns":
                    orphan_assets_without_patterns,

                "orphan_patterns_by_path":
                    orphan_patterns_by_path,

                "orphan_asset_chart_ids":
                    orphan_asset_chart_ids,

                "orphan_pattern_chart_ids":
                    orphan_pattern_chart_ids,

                "relationship_type":
                    "data_connectivity",

                "matching_strategy":
                    (
                        "path/name suffix heuristic "
                        "plus chart_id comparison "
                        "where available"
                    ),
            },
            suggested_fix=(
                None
                if pass_condition
                else (
                    "Ensure scan results persist to "
                    "file_scan_inventory.db, "
                    "assets persist to chart_assets.db, "
                    "and pattern extraction persists "
                    "to chart_patterns.db using "
                    "stable path/hash/chart_id links."
                )
            ),
            governance_domain="artifact_backbone",
            contract_type="artifact_relationships",
        )

    def check_asset_pipeline(self) -> None:
        type_a = self.discovered_assets.get("type_A", [])
        type_b = self.discovered_assets.get("type_B", [])

        excluded_total = int(
            self.discovered_assets.get(
                "excluded_candidate_count",
                0,
            )
        )

        excluded_by_reason = self.discovered_assets.get(
            "excluded_by_reason",
            {},
        )

        excluded_examples = self.discovered_assets.get(
            "excluded_examples",
            {},
        )

        db_candidates = self.resolve_asset_db_candidates()
        all_db_candidates = self.resolve_all_artifact_db_candidates()

        max_file_examples = 50

        self.add(
            domain="asset_pipeline",
            check="asset_inventory",
            status="info",
            summary="Scoped chart asset inventory captured without modifying asset state.",
            evidence={
                "type_A_count":
                    len(type_a),

                "type_B_count":
                    len(type_b),

                "excluded_candidate_count":
                    excluded_total,

                #
                # v1.0 evidence-volume refinement:
                #
                # Keep examples instead of dumping every path.
                #
                "type_A_files_sample":
                    type_a[:max_file_examples],

                "type_A_files_truncated":
                    len(type_a) > max_file_examples,

                "type_B_files_sample":
                    type_b[:max_file_examples],

                "type_B_files_truncated":
                    len(type_b) > max_file_examples,

                "excluded_by_reason":
                    excluded_by_reason,

                "excluded_examples":
                    excluded_examples,

                "chart_assets_db_candidates":
                    [str(path) for path in db_candidates],

                "artifact_database_candidates": {
                    db_name: [str(path) for path in paths]
                    for db_name, paths in all_db_candidates.items()
                },

                "type_A_extensions":
                    sorted(TYPE_A_EXTENSIONS),

                "type_B_extensions":
                    sorted(TYPE_B_EXTENSIONS),

                "scope_policy": {
                    "include_root_hints":
                        ASSET_SCOPE_INCLUDE_ROOT_HINTS,

                    "exclude_root_hints":
                        ASSET_SCOPE_EXCLUDE_ROOT_HINTS,

                    "excluded_candidate_dump":
                        "summarized",
                },

                "note": (
                    "Asset inventory is summarized to keep the verifier report "
                    "readable. Full repository inventory remains available from "
                    "workflow artifacts when needed."
                ),
            },
            governance_domain="artifact_backbone",
            contract_type="asset_pipeline_inventory",
        )

        if not db_candidates:
            self.add(
                domain="asset_pipeline",
                check="chart_assets_db_presence",
                status="warning",
                summary="No chart_assets.db file was discovered.",
                evidence={
                    "searched_root":
                        str(self.repo_root),

                    "artifact_database_candidates": {
                        db_name: [str(path) for path in paths]
                        for db_name, paths in all_db_candidates.items()
                    },

                    "dependency_note": (
                        "Missing chart_assets.db may cause downstream asset "
                        "coverage, hash verification, Type A usability, and "
                        "runtime DB readiness checks to fail as derived issues."
                    ),
                },
                suggested_fix=(
                    "Create or provide chart_assets.db after asset pipeline "
                    "persistence is available."
                ),
                governance_domain="artifact_backbone",
                contract_type="asset_pipeline_persistence",
            )
            return

        db_evidence = self.get_asset_db_snapshots()

        sqlite_errors = [
            item
            for item in db_evidence
            if item.get("error")
        ]

        nonempty_tables = [
            item
            for item in db_evidence
            if any(
                (count or 0) > 0
                for count in item.get("table_row_counts", {}).values()
                if isinstance(count, int)
            )
        ]

        self.add(
            domain="asset_pipeline",
            check="chart_assets_db_readable",
            status="fail" if sqlite_errors else "pass",
            summary=(
                "chart_assets.db was inspected in read-only mode."
                if not sqlite_errors
                else (
                    "One or more chart_assets.db candidates could not be "
                    "inspected in read-only mode."
                )
            ),
            evidence={
                "databases":
                    db_evidence,

                "read_mode":
                    "sqlite_readonly",

                "modification":
                    "prohibited",
            },
            suggested_fix=(
                None
                if not sqlite_errors
                else (
                    "Verify chart_assets.db is a valid SQLite database and "
                    "is accessible to CI."
                )
            ),
            governance_domain="artifact_backbone",
            contract_type="asset_pipeline_persistence",
        )

        self.add(
            domain="asset_pipeline",
            check="asset_db_has_rows",
            status="pass" if nonempty_tables else "warning",
            summary=(
                "At least one discovered chart_assets.db table contains rows."
                if nonempty_tables
                else "No non-empty chart_assets.db table was confirmed."
            ),
            evidence={
                "nonempty_database_count":
                    len(nonempty_tables),

                "database_count":
                    len(db_evidence),

                "dependency_note": (
                    "Empty chart asset databases may cause downstream "
                    "coverage and runtime readiness checks to remain blocked "
                    "or review-needed."
                ),
            },
            suggested_fix=(
                None
                if nonempty_tables
                else (
                    "Run the asset persistence pipeline and verify its output "
                    "table names and rows."
                )
            ),
            governance_domain="artifact_backbone",
            contract_type="asset_pipeline_population",
        )

    def check_asset_coverage(self) -> None:
        repository_assets = [
            str(Path(item).resolve())
            for item in self.discovered_assets.get("type_A", [])
        ]

        repository_assets += [
            str(Path(item).resolve())
            for item in self.discovered_assets.get("type_B", [])
        ]

        repository_assets_set = set(repository_assets)

        records = self.iter_asset_db_records()

        db_paths = {
            normalize_path_text(record.get("path"))
            for record in records
            if normalize_path_text(record.get("path"))
        }

        db_path_matches: Set[str] = set()
        orphan_files: List[str] = []

        for asset in sorted(repository_assets_set):
            normalized_asset = normalize_path_text(asset)
            matched = False

            for db_path in db_paths:
                if db_path and (
                    db_path == normalized_asset
                    or normalized_asset.endswith(db_path)
                    or db_path.endswith(Path(asset).name)
                ):
                    matched = True
                    db_path_matches.add(db_path)
                    break

            if not matched:
                orphan_files.append(asset)

        orphan_db_entries = sorted(
            [
                path
                for path in db_paths
                if path not in db_path_matches
            ]
        )

        coverage_percentage = 100.0 if not repository_assets_set else round(
            ((len(repository_assets_set) - len(orphan_files)) / len(repository_assets_set)) * 100,
            2,
        )

        pass_condition = (
            bool(repository_assets_set)
            and coverage_percentage == 100.0
            and not orphan_db_entries
        )

        self.add(
            domain="asset_coverage",
            check="repository_db_asset_coverage",
            status="pass" if pass_condition else "fail",
            summary=(
                "Scoped repository asset coverage "
                "matches chart_assets.db records."
                if pass_condition
                else
                "Scoped repository asset coverage "
                "has gaps or unmatched DB entries."
            ),
            evidence={
                "repository_asset_count":
                    len(repository_assets_set),

                "db_asset_path_count":
                    len(db_paths),

                "coverage_percentage":
                    coverage_percentage,

                "orphan_files":
                    orphan_files,

                "orphan_db_entries":
                    orphan_db_entries,

                "verification_layer":
                    "coverage",

                "matching_strategy":
                    "path/name suffix heuristic",

                "scope_note":
                    (
                        "Coverage operates on "
                        "scoped assets only."
                    ),
            },
            suggested_fix=(
                None
                if pass_condition
                else (
                    "Persist all scoped assets "
                    "to chart_assets.db and "
                    "resolve orphan DB records."
                )
            ),
            governance_domain="artifact_backbone",
            contract_type="asset_coverage",
        )
        
    def check_artifact_backbone_contract(self) -> None:
        readiness = self.governance_readiness_snapshot()

        backbone_present = (
            readiness.get(
                "artifact_backbone_present",
                False,
            )
        )

        backbone_readable = (
            readiness.get(
                "artifact_backbone_readable",
                False,
            )
        )

        relationship_ready = (
            readiness.get(
                "relationship_ready",
                False,
            )
        )

        pass_condition = (
            backbone_present
            and backbone_readable
            and relationship_ready
        )

        self.add(
            domain="artifact_backbone",
            check="artifact_backbone_contract",
            status="pass" if pass_condition else "fail",
            summary=(
                "Artifact backbone contract satisfied."
                if pass_condition
                else
                "Artifact backbone contract not satisfied."
            ),
            evidence={
                "required_databases":
                    ARTIFACT_DATABASE_NAMES,

                "required_relationships":
                    [
                        "scan_to_asset",
                        "asset_to_pattern",
                    ],

                "required_capabilities":
                    [
                        "runtime_asset_resolution",
                        "runtime_pattern_resolution",
                        "runtime_recommendation_support",
                    ],

                "readiness":
                    readiness,
            },
            suggested_fix=(
                None
                if pass_condition
                else (
                    "Restore missing database, "
                    "relationship, or runtime "
                    "artifact capability."
                )
            ),
            governance_domain="artifact_backbone",
            contract_type="artifact_backbone_contract",
        )

    def check_hash_verification(self) -> None:
        repository_hashes = self.compute_repository_asset_hashes()
        records = self.iter_asset_db_records()

        db_hashes: Dict[str, List[Dict[str, Any]]] = {}

        for record in records:
            hash_value = str(record.get("hash") or "").strip()

            if not hash_value:
                continue

            db_hashes.setdefault(hash_value, []).append(record)

        duplicate_hashes = {
            hash_value: len(rows)
            for hash_value, rows in db_hashes.items()
            if len(rows) > 1
        }

        file_hash_set = set(repository_hashes.values())
        db_hash_set = set(db_hashes.keys())

        missing_hash_files = sorted(
            [
                path
                for path, digest in repository_hashes.items()
                if digest not in db_hash_set
            ]
        )

        orphan_db_hashes = sorted(
            [
                digest
                for digest in db_hash_set
                if digest not in file_hash_set
            ]
        )

        matched_hash_count = len(
            file_hash_set.intersection(db_hash_set)
        )

        pass_condition = (
            bool(repository_hashes)
            and not missing_hash_files
            and not orphan_db_hashes
            and not duplicate_hashes
        )

        self.add(
            domain="hash_verification",
            check="repository_db_hash_consistency",
            status="pass" if pass_condition else "fail",
            summary=(
                "Scoped repository asset hashes are consistent with chart_assets.db."
                if pass_condition
                else "Hash verification found missing, orphan, or duplicate hashes."
            ),
            evidence={
                "repository_hash_count": len(repository_hashes),
                "db_hash_count": len(db_hash_set),
                "matched_hash_count": matched_hash_count,
                "missing_hash_files": missing_hash_files,
                "orphan_db_hashes": orphan_db_hashes,
                "duplicate_hashes": duplicate_hashes,
                "verification_layer": "hash_integrity",
                "scope_note": (
                    "v1.0 hashes scoped asset candidates rather than all repository files."
                ),
            },
            suggested_fix=(
                None
                if pass_condition
                else (
                    "Store SHA-256 hashes for persisted scoped assets and "
                    "resolve missing/orphan/duplicate hash records."
                )
            ),
            governance_domain="artifact_backbone",
            contract_type="hash_integrity",
        )

    def check_type_A_usability(self) -> None:
        records = self.iter_asset_db_records()
        type_a_records: List[Dict[str, Any]] = []

        for record in records:
            explicit_type = str(record.get("asset_type") or "").lower()
            path_text = normalize_path_text(record.get("path"))
            suffix_type = (
                classify_asset_path(Path(path_text))
                if path_text
                else "unknown"
            )

            if (
                explicit_type in {"type_a", "type-a", "a", "deterministic"}
                or suffix_type == "type_A"
            ):
                type_a_records.append(record)

        unusable: List[Dict[str, Any]] = []
        usable_count = 0

        for record in type_a_records:
            text = record.get("text")
            text_value = str(text or "")
            usable = (
                bool(text_value.strip())
                and len(text_value.strip()) >= MIN_TYPE_A_TEXT_LENGTH
            )

            if usable:
                usable_count += 1
            else:
                unusable.append(
                    {
                        "db_path": record.get("db_path"),
                        "table": record.get("table"),
                        "path": record.get("path"),
                        "text_length": len(text_value.strip()),
                    }
                )

        pass_condition = bool(type_a_records) and not unusable

        self.add(
            domain="type_A_usability",
            check="text_representation_usability",
            status="pass" if pass_condition else "fail",
            summary=(
                "Type A assets have usable text representations."
                if pass_condition
                else "One or more Type A assets lack usable text representations."
            ),
            evidence={
                "type_A_record_count": len(type_a_records),
                "usable_count": usable_count,
                "unusable_count": len(unusable),
                "minimum_text_length": MIN_TYPE_A_TEXT_LENGTH,
                "unusable_records": unusable,
                "verification_layer": "type_A_runtime_usability",
                "type_A_contract": {
                    "expected": [
                        "text_representation",
                        "converter_success",
                        "usable_content",
                        "usability_verified",
                    ],
                },
            },
            suggested_fix=(
                None
                if pass_condition
                else (
                    "Convert Type A assets into non-empty text_representation "
                    "values before deletion readiness."
                )
            ),
            governance_domain="artifact_backbone",
            contract_type="type_A_usability",
        )

    def check_type_B_intelligence(self) -> None:
        type_b_files = self.discovered_assets.get("type_B", [])
        records = self.iter_asset_db_records()

        type_b_records: List[Dict[str, Any]] = []

        for record in records:
            explicit_type = str(record.get("asset_type") or "").lower()
            path_text = normalize_path_text(record.get("path"))
            suffix_type = (
                classify_asset_path(Path(path_text))
                if path_text
                else "unknown"
            )

            if (
                explicit_type in {
                    "type_b",
                    "type-b",
                    "b",
                    "reference",
                    "reference_only",
                }
                or suffix_type == "type_B"
            ):
                type_b_records.append(record)

        if not type_b_files and not type_b_records:
            self.add(
                domain="type_B_intelligence",
                check="reference_intelligence_readiness",
                status="skipped",
                summary="No Type B assets were discovered; Type B intelligence verification was skipped.",
                evidence={
                    "type_B_file_count": 0,
                    "type_B_record_count": 0,
                    "expected": [
                        "reference_url",
                        "reference_metadata",
                        "source_classification",
                        "runtime_reference_visibility",
                    ],
                    "skip_reason": "No Type B file or DB record candidates were discovered.",
                },
                governance_domain="artifact_backbone",
                contract_type="type_B_reference_intelligence",
            )
            return

        missing_reference_url: List[Dict[str, Any]] = []
        reference_url_count = 0

        for record in type_b_records:
            reference_url = str(record.get("reference_url") or "").strip()

            if reference_url:
                reference_url_count += 1
            else:
                missing_reference_url.append(
                    {
                        "db_path": record.get("db_path"),
                        "table": record.get("table"),
                        "path": record.get("path"),
                    }
                )

        pass_condition = bool(type_b_records) and not missing_reference_url

        self.add(
            domain="type_B_intelligence",
            check="reference_intelligence_readiness",
            status="pass" if pass_condition else "fail",
            summary=(
                "Type B reference intelligence is usable."
                if pass_condition
                else "One or more Type B records lack reference_url evidence."
            ),
            evidence={
                "type_B_file_count": len(type_b_files),
                "type_B_record_count": len(type_b_records),
                "reference_url_count": reference_url_count,
                "missing_reference_url_count": len(missing_reference_url),
                "missing_reference_url": missing_reference_url,
                "verification_layer": "type_B_reference_intelligence",
                "expected": [
                    "reference_url",
                    "reference_metadata",
                    "source_classification",
                    "runtime_reference_visibility",
                ],
            },
            suggested_fix=(
                None
                if pass_condition
                else (
                    "Persist a usable reference_url for every Type B asset "
                    "before treating it as runtime-ready."
                )
            ),
            governance_domain="artifact_backbone",
            contract_type="type_B_reference_intelligence",
        )

    def check_runtime_db_read(self) -> None:
        snapshots_by_db = self.get_all_artifact_db_snapshots()
        records_by_db = self.iter_all_artifact_db_records()

        chart_asset_candidates = self.resolve_asset_db_candidates()
        chart_asset_snapshots = self.get_asset_db_snapshots()
        chart_asset_records = self.iter_asset_db_records()

        chart_pattern_candidates = self.resolve_artifact_db_candidates(
            CHART_PATTERNS_DB_NAME
        )
        chart_pattern_snapshots = self.get_artifact_db_snapshots(
            CHART_PATTERNS_DB_NAME
        )
        chart_pattern_records = self.iter_chart_pattern_records()

        readable_artifact_db_count = self.readable_artifact_db_count()

        asset_readable_db_count = len(
            [
                snapshot
                for snapshot in chart_asset_snapshots
                if snapshot.get("exists")
                and snapshot.get("readable")
                and not snapshot.get("error")
            ]
        )

        pattern_readable_db_count = len(
            [
                snapshot
                for snapshot in chart_pattern_snapshots
                if snapshot.get("exists")
                and snapshot.get("readable")
                and not snapshot.get("error")
            ]
        )

        path_resolvable_count = len(
            [
                record
                for record in chart_asset_records
                if normalize_path_text(record.get("path"))
            ]
        )

        text_readable_count = len(
            [
                record
                for record in chart_asset_records
                if str(record.get("text") or "").strip()
            ]
        )

        reference_readable_count = len(
            [
                record
                for record in chart_asset_records
                if str(record.get("reference_url") or "").strip()
            ]
        )

        pattern_readable_count = len(
            [
                record
                for record in chart_pattern_records
                if str(record.get("pattern") or "").strip()
                or str(record.get("chart_id") or "").strip()
            ]
        )

        runtime_reader_modules = [
            "rhythm_ingestion.assets.readers",
            "rhythm_ingestion.asset_pipeline.readers",
            "rhythm_ingestion.readers.chart_assets",
            "rhythm_ingestion.chart_assets.reader",
            "rhythm_ingestion.readers.chart_patterns",
            "rhythm_ingestion.chart_patterns.reader",
            "rhythm_ingestion.readers.file_scan_inventory",
            "rhythm_ingestion.file_scan_inventory.reader",
        ]

        import_results: Dict[str, Dict[str, Any]] = {}
        any_reader_imported = False

        self.inject_pythonpath()

        for module_name in runtime_reader_modules:
            result = import_module_probe(module_name)
            import_results[module_name] = result

            if result.get("status") == "pass":
                any_reader_imported = True

        asset_pass_condition = (
            bool(chart_asset_candidates)
            and asset_readable_db_count > 0
            and bool(chart_asset_records)
            and path_resolvable_count > 0
            and (
                text_readable_count > 0
                or reference_readable_count > 0
            )
        )

        pattern_pass_condition = (
            bool(chart_pattern_candidates)
            and pattern_readable_db_count > 0
            and bool(chart_pattern_records)
            and pattern_readable_count > 0
        )

        pass_condition = (
            readable_artifact_db_count > 0
            and asset_pass_condition
            and pattern_pass_condition
            and any_reader_imported
        )

        self.add(
            domain="runtime_db_read",
            check="runtime_db_asset_pattern_readiness",
            status="pass" if pass_condition else "fail",
            summary=(
                "Runtime DB read readiness evidence is sufficient for assets and patterns."
                if pass_condition
                else "Runtime DB read readiness is incomplete for assets, patterns, or readers."
            ),
            evidence={
                "artifact_database_names": ARTIFACT_DATABASE_NAMES,
                "readable_artifact_db_count": readable_artifact_db_count,
                "records_by_db_count": {
                    db_name: len(records)
                    for db_name, records in records_by_db.items()
                },
                "snapshots_by_db_count": {
                    db_name: len(snapshots)
                    for db_name, snapshots in snapshots_by_db.items()
                },
                "chart_asset_db_candidate_count": len(chart_asset_candidates),
                "chart_asset_readable_db_count": asset_readable_db_count,
                "chart_asset_record_count": len(chart_asset_records),
                "path_resolvable_count": path_resolvable_count,
                "text_readable_count": text_readable_count,
                "reference_readable_count": reference_readable_count,
                "chart_pattern_db_candidate_count": len(chart_pattern_candidates),
                "chart_pattern_readable_db_count": pattern_readable_db_count,
                "chart_pattern_record_count": len(chart_pattern_records),
                "pattern_readable_count": pattern_readable_count,
                "asset_pass_condition": asset_pass_condition,
                "pattern_pass_condition": pattern_pass_condition,
                "reader_import_results": import_results,
                "any_reader_imported": any_reader_imported,
                "runtime_operability_layer": "artifact_db_readiness",
                "note": (
                    "v1.0 runtime DB readiness requires read-only DB evidence, "
                    "usable asset rows, usable pattern rows, and at least one "
                    "importable reader module."
                ),
            },
            suggested_fix=(
                None
                if pass_condition
                else (
                    "Verify artifact DB readers and ensure chart_assets.db and "
                    "chart_patterns.db contain readable runtime rows."
                )
            ),
            governance_domain="artifact_backbone",
            contract_type="runtime_artifact_readiness",
        )

    def check_deletion_readiness(self) -> None:
        scan_records = self.iter_file_scan_inventory_records()
        asset_records = self.iter_asset_db_records()
        pattern_records = self.iter_chart_pattern_records()
        repository_assets = self.discovered_assets.get("type_A", []) + self.discovered_assets.get("type_B", [])

        asset_coverage_result = next(
            (
                result
                for result in self.results
                if result.domain == "asset_coverage"
                and result.check == "repository_db_asset_coverage"
            ),
            None,
        )

        hash_result = next(
            (
                result
                for result in self.results
                if result.domain == "hash_verification"
                and result.check == "repository_db_hash_consistency"
            ),
            None,
        )

        type_a_result = next(
            (
                result
                for result in self.results
                if result.domain == "type_A_usability"
                and result.check == "text_representation_usability"
            ),
            None,
        )

        runtime_db_result = next(
            (
                result
                for result in self.results
                if result.domain == "runtime_db_read"
                and result.check == "runtime_db_asset_pattern_readiness"
            ),
            None,
        )

        artifact_db_result = next(
            (
                result
                for result in self.results
                if result.domain == "artifact_databases"
                and result.check == "artifact_database_policy"
            ),
            None,
        )

        artifact_relationship_result = next(
            (
                result
                for result in self.results
                if result.domain == "artifact_relationships"
                and result.check == "artifact_relationship_chain"
            ),
            None,
        )

        required = {
            "file_scan_inventory_complete": bool(scan_records),
            "chart_assets_db_complete": bool(asset_records),
            "chart_patterns_db_complete": bool(pattern_records),
            "repository_coverage_complete": bool(repository_assets),
            "artifact_databases_verified": artifact_db_result is not None and artifact_db_result.status == "pass",
            "scan_to_asset_verified": artifact_relationship_result is not None and artifact_relationship_result.status == "pass",
            "asset_to_pattern_verified": artifact_relationship_result is not None and artifact_relationship_result.status == "pass",
            "asset_coverage_verified": asset_coverage_result is not None and asset_coverage_result.status == "pass",
            "hash_consistency_verified": hash_result is not None and hash_result.status == "pass",
            "type_A_text_usable": type_a_result is not None and type_a_result.status == "pass",
            "runtime_can_use_db_assets": runtime_db_result is not None and runtime_db_result.status == "pass",
            "runtime_can_use_db_patterns": runtime_db_result is not None and runtime_db_result.status == "pass",
        }

        passed = all(required.values())

        self.add(
            domain="governance",
            check="deletion_readiness",
            status="pass" if passed else "fail",
            summary=(
                "Deletion readiness gate passed."
                if passed
                else
                "Deletion readiness gate failed. Source chart files must be retained."
            ),
            evidence={
                "required": required,

                "repository_asset_count":
                    len(repository_assets),

                "file_scan_inventory_record_count":
                    len(scan_records),

                "chart_asset_record_count":
                    len(asset_records),

                "chart_pattern_record_count":
                    len(pattern_records),

                "failure_action":
                    (
                        "block_deletion_recommendation"
                        if not passed
                        else None
                    ),

                "verification_layer":
                    "deletion_governance",
            },
            suggested_fix=(
                None
                if passed
                else (
                    "Keep source chart files until "
                    "artifact coverage, hashes, "
                    "Type A usability, "
                    "relationship verification, "
                    "and runtime DB readiness pass."
                )
            ),
            governance_domain="artifact_backbone",
            contract_type="deletion_readiness",
        )

    def check_flow_verification(self) -> None:
        dependency_result = next(
            (
                result
                for result in self.results
                if result.domain == "dependency_reality"
                and result.check == "runtime_dependency_probe"
            ),
            None,
        )

        runtime_import_result = next(
            (
                result
                for result in self.results
                if result.domain == "runtime_import"
                and result.check == "recommend_module_importable"
            ),
            None,
        )

        dependency_ready = dependency_result is not None and dependency_result.status == "pass"
        runtime_import_ready = runtime_import_result is not None and runtime_import_result.status == "pass"

        if not dependency_ready or not runtime_import_ready:
            self.add(
                domain="flow_verification",
                check="runtime_flow_entrypoints",
                status="skipped",
                summary="Flow verification was skipped because dependency or runtime import readiness is incomplete.",
                evidence={
                    "dependency_ready": dependency_ready,
                    "runtime_import_ready": runtime_import_ready,
                    "reason": "Flow verification requires dependency reality and runtime import reality to pass first.",
                    "flows": sorted(FLOW_KEYWORDS.keys()),
                },
            )
            return

        python_files: List[Path] = []

        try:
            for path in self.backend_root.rglob("*.py"):
                if path.is_file():
                    python_files.append(path)
        except Exception:
            pass

        flow_evidence: Dict[str, Dict[str, Any]] = {}

        for flow_name, keywords in FLOW_KEYWORDS.items():
            matched_files: List[str] = []
            keyword_hits: Dict[str, List[str]] = {keyword: [] for keyword in keywords}

            for path in python_files:
                normalized_path = normalize_path_text(path)
                text = read_text_safely(path)
                combined = f"{normalized_path}\n{text}".lower()

                file_matched = False

                for keyword in keywords:
                    if keyword.lower() in combined:
                        keyword_hits[keyword].append(str(path.resolve()))
                        file_matched = True

                if file_matched:
                    matched_files.append(str(path.resolve()))

            missing_keywords = [
                keyword
                for keyword, hits in keyword_hits.items()
                if not hits
            ]

            flow_evidence[flow_name] = {
                "expected_keywords": keywords,
                "matched_files": sorted(set(matched_files)),
                "keyword_hits": {
                    keyword: sorted(set(hits))
                    for keyword, hits in keyword_hits.items()
                },
                "missing_keywords": missing_keywords,
                "ready": not missing_keywords,
            }

        failed_flows = [
            flow_name
            for flow_name, evidence in flow_evidence.items()
            if not evidence.get("ready")
        ]

        pass_condition = not failed_flows

        self.add(
            domain="flow_verification",
            check="runtime_flow_entrypoints",
            status="pass" if pass_condition else "warning",
            summary=(
                "Runtime flow entrypoint evidence was found for chart-first, player-first, and progression flows."
                if pass_condition
                else
                "Some runtime flow evidence is incomplete."
            ),
            evidence={
                "flow_evidence": flow_evidence,
                "failed_flows": failed_flows,
                "verification_style":
                    "static_keyword_entrypoint_check",

                "verification_scope":
                    "flow_existence",

                "note":
                    "Flow verification checks flow presence and wiring evidence only.",
            },
            suggested_fix=(
                None
                if pass_condition
                else (
                    "Expose clearer entrypoints and stopping points "
                    "for chart-first, player-first, "
                    "and progression-driven flows."
                )
            ),
            governance_domain="flow_contracts",
            contract_type="flow_existence",
        )

    def check_layer_separation(self) -> None:
        python_files: List[Path] = []

        try:
            for path in self.backend_root.rglob("*.py"):
                if path.is_file():
                    python_files.append(path)
        except Exception:
            pass

        layer_files: Dict[str, List[str]] = {
            layer: []
            for layer in LAYER_KEYWORDS
        }

        hint_findings: List[Dict[str, Any]] = []
        suspicion_findings: List[Dict[str, Any]] = []
        evidence_findings: List[Dict[str, Any]] = []

        def classify_boundary_signal(
            *,
            layer: str,
            hint: str,
            line_text: str,
        ) -> Tuple[str, str]:
            stripped = line_text.strip()
            lowered = stripped.lower()
            hint_lower = hint.lower()

            #
            # Ignore obvious comments.
            # This reduces false positives from documentation such as:
            # "# readers should not write"
            #
            if not stripped or stripped.startswith("#"):
                return (
                    "ignored",
                    "Comment or empty line; not treated as boundary evidence.",
                )

            #
            # Tier 3 — evidence.
            #
            # These indicate likely executable side-effect or ownership crossing.
            #
            evidence_tokens = [
                ".commit(",
                ".execute(",
                ".executemany(",
                "insert into",
                "update ",
                "delete from",
                "create table",
                "drop table",
                "alter table",
                ".persist(",
                ".save(",
                ".write(",
                "open(",
            ]

            if any(token in lowered for token in evidence_tokens):
                return (
                    "evidence",
                    "Executable side-effect or persistence-like operation detected.",
                )

            #
            # Tier 2 — suspicion.
            #
            # Imports from prohibited layers are stronger than plain text hits,
            # but still not automatically proof of mutation.
            #
            import_like = (
                lowered.startswith("import ")
                or lowered.startswith("from ")
            )

            if import_like and hint_lower in lowered:
                return (
                    "suspicion",
                    "Import-like reference to prohibited layer detected.",
                )

            #
            # Tier 1 — hint.
            #
            # Plain string match. Useful for audit context, but not enough to block governance.
            #
            if hint_lower in lowered:
                return (
                    "hint",
                    "Textual hint only; requires corroborating evidence.",
                )

            return (
                "ignored",
                "No actionable boundary signal.",
            )

        for path in python_files:
            normalized_path = normalize_path_text(path).lower()
            text = read_text_safely(path)

            matched_layers: Set[str] = set()

            for layer, keywords in LAYER_KEYWORDS.items():
                if any(keyword.lower() in normalized_path for keyword in keywords):
                    matched_layers.add(layer)
                    layer_files[layer].append(str(path.resolve()))

            if not matched_layers:
                continue

            lines = text.splitlines()

            for layer in matched_layers:
                prohibited_hints = PROHIBITED_LAYER_IMPORT_HINTS.get(layer, [])

                for line_number, line_text in enumerate(lines, start=1):
                    for hint in prohibited_hints:
                        if hint not in line_text:
                            continue

                        confidence, justification = classify_boundary_signal(
                            layer=layer,
                            hint=hint,
                            line_text=line_text,
                        )

                        if confidence == "ignored":
                            continue

                        finding = {
                            "layer": layer,
                            "file": str(path.resolve()),
                            "line": line_number,
                            "matched_hint": hint,
                            "confidence": confidence,
                            "snippet": line_text.strip()[:300],
                            "justification": justification,
                        }

                        if confidence == "evidence":
                            evidence_findings.append(finding)
                        elif confidence == "suspicion":
                            suspicion_findings.append(finding)
                        else:
                            hint_findings.append(finding)

        evidence_count = len(evidence_findings)
        suspicion_count = len(suspicion_findings)
        hint_count = len(hint_findings)

        if evidence_count > 0:
            status = "critical"
            summary = "Layer boundary audit found evidence-level prohibited boundary violations."
        elif suspicion_count > 0:
            status = "warning"
            summary = "Layer boundary audit found suspicious boundary references, but no evidence-level violations."
        elif hint_count > 0:
            status = "info"
            summary = "Layer boundary audit found textual boundary hints only; no actionable violations confirmed."
        else:
            status = "pass"
            summary = "Layer boundary audit found no prohibited boundary signals."

        self.add(
            domain="layer_separation",
            check="layer_boundary_audit",
            status=status,
            summary=summary,
            evidence={
                "layer_files": {
                    layer: sorted(set(files))
                    for layer, files in layer_files.items()
                },
                "risk_summary": {
                    "evidence_count": evidence_count,
                    "suspicion_count": suspicion_count,
                    "hint_count": hint_count,
                    "governance_blocking": evidence_count > 0,
                },
                "evidence_findings": evidence_findings,
                "suspicion_findings": suspicion_findings,
                "hint_findings": hint_findings,
                "prohibited_layer_import_hints": PROHIBITED_LAYER_IMPORT_HINTS,
                "audit_style": "tiered_static_boundary_governance",
                "verification_scope": "layer_responsibility",
                "layer_model": list(LAYER_KEYWORDS.keys()),
                "confidence_model": {
                    "hint": {
                        "meaning": "Textual keyword match only.",
                        "severity": "info",
                        "governance_blocking": False,
                    },
                    "suspicion": {
                        "meaning": "Import-like or structural reference to prohibited responsibility.",
                        "severity": "warning",
                        "governance_blocking": False,
                    },
                    "evidence": {
                        "meaning": "Executable side-effect or persistence-like operation detected in wrong layer.",
                        "severity": "critical",
                        "governance_blocking": True,
                    },
                },
                "false_positive_controls": [
                    "Comments and empty lines are ignored.",
                    "Plain keyword hits are classified as hint, not violation.",
                    "Import-like references are classified as suspicion, not critical violation.",
                    "Only executable side-effect evidence escalates to critical.",
                ],
                "note": (
                    "This audit separates hints, suspicions, and evidence-level violations. "
                    "Only evidence-level findings should block governance."
                ),
            },
            suggested_fix=(
                None
                if evidence_count == 0
                else (
                    "Move executable side effects or persistence ownership into the correct layer. "
                    "Converters, validators, readers, models, normalizers, and classifiers "
                    "must remain responsibility-separated."
                )
            ),
            governance_domain="layer_boundaries",
            contract_type="layer_boundary",
        )
        
        self.update_layer_boundary_risk(
            evidence_count=evidence_count,
            suspicion_count=suspicion_count,
            hint_count=hint_count,
            status=status,
        )

    def check_mcp_config(self) -> None:
        if not self.mcp_config:
            self.add(
                domain="mcp",
                check="config_present",
                status="skipped",
                summary="No MCP config path was provided.",
                evidence={},
            )
            return

        if not self.mcp_config.exists():
            self.add(
                domain="mcp",
                check="config_present",
                status="warning",
                summary="Provided MCP config path does not exist.",
                evidence={
                    "path": str(self.mcp_config),
                },
            )
            return

        data = self.read_json_file(self.mcp_config)

        if data is None:
            return

        servers = data.get("servers", {}) if isinstance(data, dict) else {}
        server = servers.get("rhythm-game-assistant") if isinstance(servers, dict) else None

        if not server:
            self.add(
                domain="mcp",
                check="rga_server_defined",
                status="fail",
                summary="rhythm-game-assistant MCP server is not defined.",
                evidence={
                    "path": str(self.mcp_config),
                    "server_keys": sorted(list(servers.keys())) if isinstance(servers, dict) else [],
                },
            )
            return

        server_type = server.get("type")
        env = server.get("env") or {}
        args = server.get("args", [])
        command = server.get("command")

        command_text = str(command or "")
        args_text = " ".join(str(item) for item in args)

        references_mcp_server = "mcp_server.py" in command_text or "mcp_server.py" in args_text

        env_keys = sorted(list(env.keys())) if isinstance(env, dict) else []
        has_rest_url = "RGA_REST_URL" in env_keys or any("RGA_REST_URL" in str(item) for item in args)

        self.add(
            domain="mcp_contract",
            check="mcp_server_contract",
            status="pass" if server_type == "stdio" else "fail",
            summary=(
                "MCP contract satisfied."
                if server_type == "stdio"
                else
                "RGA MCP server does not satisfy stdio contract."
            ),
            evidence={
                "type": server_type,
                "command": command,
                "args": args,

                "env_keys":
                    env_keys,

                "references_mcp_server":
                    references_mcp_server,

                "has_rest_url_evidence":
                    has_rest_url,

                "required_server":
                    {
                        "id": "rhythm-game-assistant",
                        "type": "stdio",
                    },
            },
            suggested_fix=(
                None
                if server_type == "stdio"
                else (
                    "Use mcp_server.py as the stdio MCP adapter "
                    "and forward requests through RGA_REST_URL."
                )
            ),
            governance_domain="mcp_contracts",
            contract_type="mcp_server_contract",
        )

        self.add(
            domain="mcp_contract",
            check="mcp_adapter_contract",
            status="pass" if references_mcp_server else "warning",
            summary=(
                "MCP config references mcp_server.py."
                if references_mcp_server
                else "MCP config does not clearly reference mcp_server.py."
            ),
            evidence={
                "command": command,
                "args": args,
                "references_mcp_server": references_mcp_server,
                "server_keys": sorted(list(server.keys())) if isinstance(server, dict) else [],
            },
            suggested_fix=(
                None
                if references_mcp_server
                else "Point the rhythm-game-assistant MCP server command/args to the local mcp_server.py adapter."
            ),
            governance_domain="mcp_contracts",
            contract_type="mcp_adapter_contract",
        )

        tool_like_keys = []

        if isinstance(server, dict):
            for key in ["tools", "toolsets", "capabilities"]:
                if key in server:
                    tool_like_keys.append(key)

        self.add(
            domain="mcp_contract",
            check="tool_surface_evidence",
            status="info",
            summary="MCP tool registration visibility evidence captured from config.",
            evidence={
                "tool_like_keys_present": tool_like_keys,
                "server_keys": sorted(list(server.keys())) if isinstance(server, dict) else [],
                "note": "Some MCP adapters register tools dynamically at runtime, so absence of tool keys in config is not automatically a failure.",
            },
            governance_domain="mcp_contracts",
            contract_type="mcp_tool_surface",
        )

    def check_rest_contract(self) -> None:
        if not self.run_rest:
            self.add(
                domain="rest_api",
                check="rest_verification_enabled",
                status="skipped",
                summary="REST checks were skipped. Use --rest to enable REST verification.",
                evidence={
                    "api_url": self.api_url,
                },
                governance_domain="architecture_contracts",
                contract_type="rest_contract",
            )
            return

        payloads = {
            "song_mode_post": {
                "mode": "song",
                "game_id": "proseka",
                "locale": "en-US",
                "max_items": 1,
                "song_ids": ["local-test-song"],
                "player_signals": {},
                "player_profile": {},
                "player_history": {},
                "preferences": {},
                "evidence": {},
            },
            "game_mode_post": {
                "mode": "game",
                "game_id": "proseka",
                "locale": "en-US",
                "max_items": 3,
                "player_signals": {
                    "expert_fc_count": "120",
                    "master_fc_count": "20",
                    "highest_confirmed_difficulty": "32",
                },
                "player_profile": {},
                "player_history": {},
                "preferences": {},
                "evidence": {},
            },
        }

        for check, payload in payloads.items():
            try:
                result = self.post_json(payload)

                self.add(
                    domain="rest_api",
                    check=check,
                    status="pass",
                    summary=f"{check} completed.",
                    evidence={
                        "response_keys": (
                            sorted(list(result.keys()))
                            if isinstance(result, dict)
                            else []
                        ),
                        "contract_type": "rest_response_contract",
                    },
                    governance_domain="architecture_contracts",
                    contract_type="rest_contract",
                )

            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                summary = f"{check} returned HTTP {exc.code}."

                if (
                    check == "game_mode_post"
                    and exc.code == 501
                    and "Games recommender not configured" in body
                ):
                    summary = "Game mode confirms games_recommender is not configured."

                self.add(
                    domain="rest_api",
                    check=check,
                    status="fail",
                    summary=summary,
                    evidence={
                        "status": exc.code,
                        "body": body,
                        "contract_type": "rest_response_contract",
                    },
                    suggested_fix=(
                        "Inject a Phase 7 games_recommender into create_app(...)."
                        if exc.code == 501
                        else None
                    ),
                    governance_domain="architecture_contracts",
                    contract_type="rest_contract",
                )

            except Exception as exc:
                self.add(
                    domain="rest_api",
                    check=check,
                    status="fail",
                    summary=f"{check} failed.",
                    evidence={
                        "error": str(exc),
                        "contract_type": "rest_response_contract",
                    },
                    governance_domain="architecture_contracts",
                    contract_type="rest_contract",
                )

    def check_flow_contract_verification(self) -> None:
        flow_result = next(
            (
                result
                for result in self.results
                if result.domain == "flow_verification"
                and result.check == "runtime_flow_entrypoints"
            ),
            None,
        )

        if flow_result is None:
            self.add(
                domain="flow_contract_verification",
                check="flow_contract_compliance",
                status="skipped",
                summary="Flow contract verification was skipped because flow verification has not produced evidence.",
                evidence={
                    "reason": "runtime_flow_entrypoints result not found",
                    "required_flows": sorted(FLOW_KEYWORDS.keys()),
                },
                governance_domain="flow_contracts",
                contract_type="flow_contract",
            )
            return

        if flow_result.status == "skipped":
            self.add(
                domain="flow_contract_verification",
                check="flow_contract_compliance",
                status="skipped",
                summary="Flow contract verification was skipped because flow verification preconditions were not met.",
                evidence={
                    "source_status": flow_result.status,
                    "source_summary": flow_result.summary,
                    "required_flows": sorted(FLOW_KEYWORDS.keys()),
                },
                governance_domain="flow_contracts",
                contract_type="flow_contract",
            )
            return

        flow_evidence = flow_result.evidence.get("flow_evidence", {})
        failed_flows = flow_result.evidence.get("failed_flows", [])

        contract_expectations = {
            "chart_first": {
                "entry_artifact": "chart",
                "required": [
                    "chart_resolution",
                    "pattern_detection",
                    "tips",
                    "personalization",
                    "localization",
                ],
            },
            "player_first": {
                "entry_artifact": "player",
                "required": [
                    "player_signals",
                    "song_recommendation",
                ],
                "optional": [
                    "tips",
                ],
            },
            "progression": {
                "entry_artifact": "progression",
                "required": [
                    "game_recommendation",
                    "song_recommendation",
                ],
                "optional": [
                    "tips",
                ],
            },
        }

        pass_condition = flow_result.status == "pass" and not failed_flows

        self.add(
            domain="flow_contract_verification",
            check="flow_contract_compliance",
            status="pass" if pass_condition else "fail",
            summary=(
                "Flow contracts are supported by runtime flow evidence."
                if pass_condition
                else "One or more flow contracts lack supporting runtime flow evidence."
            ),
            evidence={
                "contract_expectations": contract_expectations,
                "flow_evidence": flow_evidence,
                "failed_flows": failed_flows,
                "verification_scope": "flow_contract_compliance",
                "note": (
                    "This check verifies flow boundary evidence only. "
                    "It does not validate recommendation quality or gameplay inference correctness."
                ),
            },
            suggested_fix=(
                None
                if pass_condition
                else (
                    "Expose clearer entrypoints, main artifacts, and stopping points "
                    "for chart-first, player-first, and progression-driven flows."
                )
            ),
            governance_domain="flow_contracts",
            contract_type="flow_contract",
        )

    def check_governance_verdict(self) -> None:
        blocking_reasons = list(
            self.governance_state.get(
                "blocking_reasons",
                [],
            )
        )

        warnings = list(
            self.governance_state.get(
                "warnings",
                [],
            )
        )

        #
        # ----------------------------------------------------------
        # Separate governance failures from dependency failures.
        # ----------------------------------------------------------
        #

        dependency_failures: List[Dict[str, Any]] = []
        governance_failures: List[Dict[str, Any]] = []
        
        #
        # ----------------------------------------------------------
        # Root vs Derived Failure Classification
        #
        # Root failures represent problems that can independently
        # invalidate a governance contract.
        #
        # Derived failures are expected consequences of an
        # upstream root failure.
        # ----------------------------------------------------------
        #

        dependency_failures: List[Dict[str, Any]] = []
        governance_failures: List[Dict[str, Any]] = []

        root_failures: List[Dict[str, Any]] = []
        derived_failures: List[Dict[str, Any]] = []

        DERIVED_FAILURE_POLICY = {

            #
            # Artifact backbone cascade
            #

            "artifact_relationships":
                "artifact_database_policy",

            "artifact_backbone_contract":
                "artifact_database_policy",

            "asset_coverage":
                "artifact_database_policy",

            "hash_integrity":
                "artifact_database_policy",

            "type_A_usability":
                "artifact_database_policy",

            "runtime_artifact_readiness":
                "artifact_database_policy",
        }
        
        for item in governance_failures:

            contract_type = item.get("contract_type")

            dependency_of = (
                DERIVED_FAILURE_POLICY.get(
                    contract_type
                )
            )

            if dependency_of:
                item["dependency_of"] = (
                    dependency_of
                )
            
                derived_failures.append(
                    item
                )
                
            else:
                root_failures.append(
                    item
                )

        critical_results: List[Any] = []
        fail_results: List[Any] = []

        for result in self.results:
            if result.severity == "critical":
                critical_results.append(result)

            if result.severity == "fail":
                fail_results.append(result)

        dependency_contracts = {
            "dependency_reality",
            "import_reality",
            "runtime_import_reality",
        }

        for result in (critical_results + fail_results):
            contract_type = getattr(
                result,
                "contract_type",
                None,
            )

            item = {
                "domain": result.domain,
                "check": result.check,
                "severity": result.severity,
                "summary": result.summary,
                "governance_domain": getattr(
                    result,
                    "governance_domain",
                    None,
                ),
                "contract_type": contract_type,
            }

            if contract_type in dependency_contracts:
                dependency_failures.append(item)
            else:
                governance_failures.append(item)

        root_failures, derived_failures = (
            self.classify_governance_failure_lineage(
                governance_failures=governance_failures,
            )
        )

        dependency_fail_count = len(
            dependency_failures
        )

        governance_fail_count = len(
            governance_failures
        )

        root_failure_count = len(
            root_failures
        )

        derived_failure_count = len(
            derived_failures
        )

        #
        # ----------------------------------------------------------
        # Runtime dependency reality
        # ----------------------------------------------------------
        #

        runtime_dependency_result = next(
            (
                result
                for result in self.results
                if result.domain == "dependency_reality"
                and result.check == "runtime_dependency_probe"
            ),
            None,
        )

        runtime_import_result = next(
            (
                result
                for result in self.results
                if result.domain == "runtime_import"
                and result.check == "recommend_module_importable"
            ),
            None,
        )

        runtime_verdict = (
            "ready"
            if (
                runtime_dependency_result is not None
                and runtime_dependency_result.status == "pass"
                and runtime_import_result is not None
                and runtime_import_result.status == "pass"
            )
            else "blocked_by_dependency"
        )

        #
        # ----------------------------------------------------------
        # Deletion readiness
        # ----------------------------------------------------------
        #

        deletion_result = next(
            (
                result
                for result in self.results
                if result.domain == "governance"
                and result.check == "deletion_readiness"
            ),
            None,
        )

        deletion_verdict = (
            "ready"
            if deletion_result is not None
            and deletion_result.status == "pass"
            else "blocked"
        )

        #
        # ----------------------------------------------------------
        # Artifact backbone
        # ----------------------------------------------------------
        #

        artifact_backbone_result = next(
            (
                result
                for result in self.results
                if result.domain == "artifact_backbone"
                and result.check == "artifact_backbone_contract"
            ),
            None,
        )

        artifact_backbone_verdict = (
            "ready"
            if artifact_backbone_result is not None
            and artifact_backbone_result.status == "pass"
            else "blocked"
        )

        #
        # ----------------------------------------------------------
        # Layer audit
        # ----------------------------------------------------------
        #

        layer_risk = self.governance_state.get(
            "layer_boundary_risk",
            {},
        )

        layer_boundary_verdict = (
            "blocked"
            if layer_risk.get(
                "evidence_count",
                0,
            ) > 0
            else (
                "review_needed"
                if layer_risk.get(
                    "suspicion_count",
                    0,
                ) > 0
                else "ready"
            )
        )

        #
        # ----------------------------------------------------------
        # MCP
        # ----------------------------------------------------------
        #

        mcp_result = next(
            (
                result
                for result in self.results
                if result.domain == "mcp_contract"
                and result.check == "mcp_server_contract"
            ),
            None,
        )

        mcp_contract_verdict = (
            "ready"
            if mcp_result is not None
            and mcp_result.status == "pass"
            else "partial_or_blocked"
        )

        #
        # ----------------------------------------------------------
        # Flow contracts
        # ----------------------------------------------------------
        #

        flow_contract_result = next(
            (
                result
                for result in self.results
                if result.domain == "flow_contract_verification"
                and result.check == "flow_contract_compliance"
            ),
            None,
        )

        flow_contract_verdict = (
            "ready"
            if flow_contract_result is not None
            and flow_contract_result.status == "pass"
            else "partial_or_blocked"
        )

        #
        # ----------------------------------------------------------
        # Architecture verdict
        #
        # IMPORTANT:
        # Dependency failures do NOT automatically block
        # architecture governance.
        # ----------------------------------------------------------
        #
        
        architecture_failure_contracts = {
            "repository_discovery",
            "repository_runtime_alignment",
            "package_layout",
            "import_reality",
            "layer_boundary",
            "flow_contract",
        }
        
        architecture_blockers = [
            item
            for item in governance_failures
            if item.get("contract_type")
            in architecture_failure_contracts
        ]

        architecture_verdict = (
            "blocked"
            if architecture_blockers
            else "ready"
        )

        #
        # ----------------------------------------------------------
        # Governance verdict
        #
        # Dependency failures influence runtime readiness,
        # but should not automatically be treated as
        # architecture-governance failures.
        # ----------------------------------------------------------
        #

        governance_verdict = (
            "blocked"
            if (
                architecture_verdict == "blocked"
                or deletion_verdict == "blocked"
                or artifact_backbone_verdict == "blocked"
                or layer_boundary_verdict == "blocked"
            )
            else (
                "review_needed"
                if (
                    layer_boundary_verdict == "review_needed"
                    or runtime_verdict == "blocked_by_dependency"
                )
                else "ready"
            )
        )

        self.governance_state.update(
            {
                "architecture_verdict":
                    architecture_verdict,

                "runtime_verdict":
                    runtime_verdict,

                "artifact_backbone_verdict":
                    artifact_backbone_verdict,

                "flow_contract_verdict":
                    flow_contract_verdict,

                "layer_boundary_verdict":
                    layer_boundary_verdict,

                "mcp_contract_verdict":
                    mcp_contract_verdict,

                "deletion_verdict":
                    deletion_verdict,

                "governance_verdict":
                    governance_verdict,

                "dependency_failures":
                    dependency_failures,

                "governance_failures":
                    governance_failures,
                    
                "root_failures":
                    root_failures,

                "derived_failures":
                    derived_failures,

                "dependency_fail_count":
                    dependency_fail_count,

                "governance_fail_count":
                    governance_fail_count,
                    
                "root_failure_count":
                    root_failure_count,
                 
                "derived_failure_count":
                    derived_failure_count,

                "blocking_reasons":
                    blocking_reasons,

                "warnings":
                    warnings,
                    
                "root_cause_summary": {
                    "primary_root_contracts": [
                        item.get("contract_type")
                        for item in root_failures
                    ],
                    "derived_contracts": [
                        item.get("contract_type")
                        for item in derived_failures
                    ],
                    "derived_dependency_map": {
                        item.get("contract_type"): item.get("dependency_of")
                        for item in derived_failures
                    },
                },
            }
        )

        self.add(
            domain="governance",
            check="governance_verdict",
            status=(
                "pass"
                if governance_verdict == "ready"
                else (
                    "warning"
                    if governance_verdict == "review_needed"
                    else "fail"
                )
            ),
            summary=(
                "RGA governance verdict is ready."
                if governance_verdict == "ready"
                else (
                    "RGA governance verdict requires review."
                    if governance_verdict == "review_needed"
                    else "RGA governance verdict is blocked."
                )
            ),
            evidence={
                #
                # --------------------------------------------------
                # Top-level verdicts
                # --------------------------------------------------
                #

                "governance_verdict":
                    governance_verdict,

                "architecture_verdict":
                    architecture_verdict,

                "runtime_verdict":
                    runtime_verdict,

                "artifact_backbone_verdict":
                    artifact_backbone_verdict,

                "flow_contract_verdict":
                    flow_contract_verdict,

                "layer_boundary_verdict":
                    layer_boundary_verdict,

                "mcp_contract_verdict":
                    mcp_contract_verdict,

                "deletion_verdict":
                    deletion_verdict,

                #
                # --------------------------------------------------
                # Failure classes
                # --------------------------------------------------
                #

                "dependency_failures":
                    dependency_failures,

                "governance_failures":
                    governance_failures,

                "root_failures":
                    root_failures,

                "derived_failures":
                    derived_failures,

                #
                # --------------------------------------------------
                # Failure counts
                # --------------------------------------------------
                #

                "dependency_fail_count":
                    dependency_fail_count,

                "governance_fail_count":
                    governance_fail_count,

                "root_failure_count":
                    root_failure_count,

                "derived_failure_count":
                    derived_failure_count,

                #
                # --------------------------------------------------
                # Compact root-cause summary
                #
                # This is intended for downstream Advisor /
                # Maintenance Planner bots.
                # --------------------------------------------------
                #

                "root_cause_summary": {
                    "primary_root_contracts": [
                        item.get("contract_type")
                        for item in root_failures
                    ],

                    "derived_contracts": [
                        item.get("contract_type")
                        for item in derived_failures
                    ],

                    "derived_dependency_map": {
                        item.get("contract_type"):
                            item.get("dependency_of")
                        for item in derived_failures
                    },
                },

                #
                # --------------------------------------------------
                # Governance accounting
                # --------------------------------------------------
                #

                "blocking_reasons":
                    blocking_reasons,

                "warnings":
                    warnings,

                #
                # --------------------------------------------------
                # Root / derived lineage policy
                # --------------------------------------------------
                #

                "lineage_policy": {
                    "root_failure_contract_types":
                        sorted(ROOT_FAILURE_CONTRACT_TYPES),

                    "derived_failure_policy":
                        DERIVED_FAILURE_POLICY,

                    "governance_meta_contract_types":
                        sorted(GOVERNANCE_META_CONTRACT_TYPES),

                    "classification_note": (
                        "Root failures represent independently actionable "
                        "governance blockers. Derived failures are downstream "
                        "consequences of an upstream root contract failure and "
                        "should be re-evaluated after the root contract passes."
                    ),
                },

                #
                # --------------------------------------------------
                # Governance policy
                # --------------------------------------------------
                #

                "policy": {
                    "default_deletion":
                        "blocked",

                    "completed_phases":
                        "immutable",

                    "verifier_mode":
                        "read_only",

                    "dependency_failures_are_not_governance_failures":
                        True,

                    "root_failures_should_be_resolved_first":
                        True,

                    "derived_failures_should_not_be_counted_as_independent_root_causes":
                        True,
                },
            },
            suggested_fix=(
                None
                if governance_verdict == "ready"
                else (
                    "Resolve root governance blockers first. "
                    "Derived failures should be re-evaluated after their "
                    "upstream root contracts pass. Dependency failures should "
                    "remain separated from architecture governance violations."
                )
            ),
            governance_domain="governance",
            contract_type="governance_verdict",
        )
        
    def run_all(self) -> Dict[str, Any]:
        self.check_environment()

        self.check_repository_discovery()
        self.check_repository_vs_runtime()

        self.check_package_layout()
        self.check_repo_shape()
        self.check_package_import_probe()

        self.check_dependency_reality()
        self.check_python_imports()
        self.check_runtime_meta_specs()

        self.check_asset_scope_policy()
        self.check_artifact_databases()
        self.check_artifact_relationships()
        self.check_artifact_backbone_contract()

        self.check_asset_pipeline()
        self.check_asset_coverage()
        self.check_hash_verification()
        self.check_type_A_usability()
        self.check_type_B_intelligence()
        self.check_runtime_db_read()
        self.check_deletion_readiness()

        self.check_flow_verification()
        self.check_flow_contract_verification()
        self.check_layer_separation()

        self.check_mcp_config()
        self.check_rest_contract()

        self.check_governance_verdict()

        counts: Dict[str, int] = {}
        severities: Dict[str, int] = {}

        for result in self.results:
            counts[result.status] = counts.get(result.status, 0) + 1
            severities[result.severity] = severities.get(result.severity, 0) + 1

        artifact_db_candidates = {
            db_name: [str(path) for path in paths]
            for db_name, paths in self.resolve_all_artifact_db_candidates().items()
        }

        artifact_db_record_counts = {
            db_name: len(records)
            for db_name, records in self.iter_all_artifact_db_records().items()
        }

        return {
            "schema": "rga.runtime_verifier.report.v1.0",
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "repo_root": str(self.repo_root),
            "backend_root": str(self.backend_root),
            "backend_root_mode": self.backend_root_mode,
            "backend_root_candidates": [
                asdict(candidate)
                for candidate in self.backend_candidates
            ],
            "discovered_files": self.discovered_files,
            "discovered_packages": self.discovered_packages,
            "discovered_assets": self.discovered_assets,
            "artifact_databases": {
                "required": ARTIFACT_DATABASE_NAMES,
                "relationship_chain": ARTIFACT_RELATIONSHIP_CHAIN,
                "candidates": artifact_db_candidates,
                "record_counts": artifact_db_record_counts,
            },
            "governance": self.governance_state,
            "api_url": self.api_url,
            "summary": counts,
            "severity_summary": severities,
            "results": [
                asdict(result)
                for result in self.results
            ],
        }


# -----------------------------------------------------------------------------
# Output helpers
# -----------------------------------------------------------------------------

def write_markdown(report: Dict[str, Any], out_path: Path) -> None:
    lines: List[str] = []

    lines.append("# RGA Runtime Verifier Report")
    lines.append("")
    lines.append(f"Schema: `{report.get('schema')}`")
    lines.append(f"Generated: `{report.get('generated_at')}`")
    lines.append(f"Repo root: `{report.get('repo_root')}`")
    lines.append(f"Backend root: `{report.get('backend_root')}`")
    lines.append(f"Backend root mode: `{report.get('backend_root_mode')}`")
    lines.append(f"API URL: `{report.get('api_url')}`")
    lines.append("")

    governance = report.get(
        "governance",
        {},
    )

    root_failures = governance.get(
        "root_failures",
        [],
    )

    derived_failures = governance.get(
        "derived_failures",
        [],
    )

    dependency_failures = governance.get(
        "dependency_failures",
        [],
    )

    governance_failures = governance.get(
        "governance_failures",
        [],
    )

    lines.append("## Governance Overview")
    lines.append("")

    governance_overview = [
        (
            "Governance verdict",
            governance.get("governance_verdict"),
        ),
        (
            "Architecture verdict",
            governance.get("architecture_verdict"),
        ),
        (
            "Runtime verdict",
            governance.get("runtime_verdict"),
        ),
        (
            "Artifact backbone verdict",
            governance.get("artifact_backbone_verdict"),
        ),
        (
            "Flow contract verdict",
            governance.get("flow_contract_verdict"),
        ),
        (
            "Layer boundary verdict",
            governance.get("layer_boundary_verdict"),
        ),
        (
            "MCP contract verdict",
            governance.get("mcp_contract_verdict"),
        ),
        (
            "Deletion verdict",
            governance.get("deletion_verdict"),
        ),
    ]

    for label, value in governance_overview:
        lines.append(
            f"- {label}: `{value}`"
        )

    lines.append("")

    lines.append(
        f"- Dependency failures: "
        f"`{governance.get('dependency_fail_count', 0)}`"
    )

    lines.append(
        f"- Governance failures: "
        f"`{governance.get('governance_fail_count', 0)}`"
    )

    lines.append(
        f"- Root failures: "
        f"`{governance.get('root_failure_count', 0)}`"
    )

    lines.append(
        f"- Derived failures: "
        f"`{governance.get('derived_failure_count', 0)}`"
    )

    lines.append("")

    #
    # Root Failures
    #

    lines.append("## Root Failures")
    lines.append("")

    if not root_failures:
        lines.append("(none)")
    else:
        for item in root_failures:

            contract_type = item.get(
                "contract_type",
                "unknown",
            )

            lines.append(
                f"- `{contract_type}` "
                f"({item.get('domain')} / {item.get('check')})"
            )

            summary = item.get("summary")

            if summary:
                lines.append(
                    f"  - {summary}"
                )

    lines.append("")

    #
    # Derived Failures
    #

    lines.append("## Derived Failures")
    lines.append("")

    if not derived_failures:
        lines.append("(none)")
    else:
        for item in derived_failures:

            contract_type = item.get(
                "contract_type",
                "unknown",
            )

            dependency_of = item.get(
                "dependency_of",
                "unknown",
            )

            lines.append(
                f"- `{contract_type}` "
                f"(dependency_of=`{dependency_of}`)"
            )

            summary = item.get("summary")

            if summary:
                lines.append(
                    f"  - {summary}"
                )

    lines.append("")

    #
    # Dependency Failures
    #

    lines.append("## Dependency Failures")
    lines.append("")

    if not dependency_failures:
        lines.append("(none)")
    else:

        for item in dependency_failures:

            lines.append(
                f"- `{item.get('contract_type')}` "
                f"({item.get('domain')} / {item.get('check')})"
            )

            summary = item.get("summary")

            if summary:
                lines.append(
                    f"  - {summary}"
                )

    lines.append("")

    #
    # Governance Failures
    #

    lines.append("## Governance Failures")
    lines.append("")

    if not governance_failures:
        lines.append("(none)")
    else:

        for item in governance_failures:

            lines.append(
                f"- `{item.get('contract_type')}` "
                f"({item.get('domain')} / {item.get('check')})"
            )

            summary = item.get("summary")

            if summary:
                lines.append(
                    f"  - {summary}"
                )

    lines.append("")

    #
    # Governance State
    #

    lines.append("## Governance State")
    lines.append("")

    lines.append("```json")

    lines.append(
        json.dumps(
            governance,
            indent=2,
            ensure_ascii=False,
        )
    )

    lines.append("```")
    lines.append("")

    lines.append("## Summary")
    for key, value in sorted(report.get("summary", {}).items()):
        lines.append(f"- **{key}**: {value}")
    lines.append("")

    lines.append("## Severity Summary")
    for key, value in sorted(report.get("severity_summary", {}).items()):
        lines.append(f"- **{key}**: {value}")
    lines.append("")

    lines.append("## Backend Candidates")
    lines.append("```json")
    lines.append(
        json.dumps(
            report.get("backend_root_candidates", []),
            indent=2,
            ensure_ascii=False,
        )
    )
    lines.append("```")
    lines.append("")

    lines.append("## Artifact Databases")
    lines.append("```json")
    lines.append(
        json.dumps(
            report.get("artifact_databases", {}),
            indent=2,
            ensure_ascii=False,
        )
    )
    lines.append("```")
    lines.append("")

    lines.append("## Discovered Files")
    lines.append("```json")
    lines.append(
        json.dumps(
            report.get("discovered_files", {}),
            indent=2,
            ensure_ascii=False,
        )
    )
    lines.append("```")
    lines.append("")

    lines.append("## Discovered Packages")
    lines.append("```json")
    lines.append(
        json.dumps(
            report.get("discovered_packages", {}),
            indent=2,
            ensure_ascii=False,
        )
    )
    lines.append("```")
    lines.append("")

    lines.append("## Discovered Assets")
    lines.append("```json")
    lines.append(
        json.dumps(
            report.get("discovered_assets", {}),
            indent=2,
            ensure_ascii=False,
        )
    )
    lines.append("```")
    lines.append("")

    lines.append("## Results")

    for item in report.get("results", []):
        lines.append(
            f"### [{item['status'].upper()} / {item['severity'].upper()}] "
            f"{item['domain']} / {item['check']}"
        )
        lines.append("")
        lines.append(item.get("summary", ""))

        if item.get("governance_domain") or item.get("contract_type"):
            lines.append("")
            lines.append(
                f"Governance domain: `{item.get('governance_domain')}`"
            )
            lines.append(
                f"Contract type: `{item.get('contract_type')}`"
            )

        evidence = item.get("evidence") or {}

        if evidence:
            lines.append("")
            lines.append("```json")
            lines.append(
                json.dumps(
                    evidence,
                    indent=2,
                    ensure_ascii=False,
                )
            )
            lines.append("```")

        if item.get("suggested_fix"):
            lines.append("")
            lines.append(f"Suggested fix: {item['suggested_fix']}")

        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser("RGA Systems Auditor")

    parser.add_argument("--repo-root", default=".", help="Repository root or backend root.")
    parser.add_argument("--backend-root", default=None, help="Explicit backend root. Overrides auto-discovery.")

    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8000/api/v1/recommend",
        help="RGA REST recommend endpoint.",
    )

    parser.add_argument(
        "--token",
        default=None,
        help="Bearer token. Defaults to SOFTR_API_TOKEN environment variable.",
    )

    parser.add_argument(
        "--mcp-config",
        default=None,
        help="Optional path to VS Code mcp.json.",
    )

    parser.add_argument(
        "--asset-db",
        default=None,
        help="Optional explicit path to chart_assets.db. Kept for v0.6 compatibility.",
    )

    parser.add_argument(
        "--file-scan-inventory-db",
        default=None,
        help="Optional explicit path to file_scan_inventory.db.",
    )

    parser.add_argument(
        "--chart-assets-db",
        default=None,
        help="Optional explicit path to chart_assets.db.",
    )

    parser.add_argument(
        "--chart-patterns-db",
        default=None,
        help="Optional explicit path to chart_patterns.db.",
    )

    parser.add_argument(
        "--rest",
        action="store_true",
        help="Run REST endpoint checks. Requires backend to be running.",
    )

    parser.add_argument(
        "--json-out",
        default=None,
        help="Optional JSON report output path.",
    )

    parser.add_argument(
        "--md-out",
        default=None,
        help="Optional Markdown report output path.",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any fail severity results are found.",
    )

    parser.add_argument(
        "--strict-severity",
        choices=["fail", "critical"],
        default="fail",
        help="Severity threshold used by --strict.",
    )

    args = parser.parse_args()

    verifier = RuntimeVerifier(
        repo_root=Path(args.repo_root),
        backend_root=Path(args.backend_root) if args.backend_root else None,
        api_url=args.api_url,
        token=args.token,
        mcp_config=Path(args.mcp_config).expanduser() if args.mcp_config else None,
        asset_db=Path(args.asset_db).expanduser() if args.asset_db else None,
        file_scan_inventory_db=(
            Path(args.file_scan_inventory_db).expanduser()
            if args.file_scan_inventory_db
            else None
        ),
        chart_assets_db=(
            Path(args.chart_assets_db).expanduser()
            if args.chart_assets_db
            else None
        ),
        chart_patterns_db=(
            Path(args.chart_patterns_db).expanduser()
            if args.chart_patterns_db
            else None
        ),
        run_rest=args.rest,
    )

    report = verifier.run_all()
    text = json.dumps(report, indent=2, ensure_ascii=False)

    print(text)

    if args.json_out:
        json_out = Path(args.json_out)
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(text, encoding="utf-8")

    if args.md_out:
        write_markdown(report, Path(args.md_out))

    if args.strict:
        severity = report.get("severity_summary", {})

        if args.strict_severity == "critical":
            if severity.get("critical", 0) > 0:
                return 1

        if args.strict_severity == "fail":
            if severity.get("fail", 0) > 0 or severity.get("critical", 0) > 0:
                return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
