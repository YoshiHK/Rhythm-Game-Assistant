"""
runtime_auditor.py

MCP Auditor Bot v1.0
RGA Systems Auditor

New in v1.0:
- Governance Audit
- Architecture Contract Audit
- Artifact Backbone Audit
- Flow Contract Audit
- MCP Contract Audit
- Completed Phase Boundary Audit
- Layer Governance Audit

Carried forward from v0.7:
- Artifact Database Audit
- Artifact Relationship Audit
- Dependency Reality Audit
- Asset Scope Policy Audit
- Flow Audit
- Layer Separation Audit
- Type B Intelligence Audit

Carried forward from v0.6:
- Asset Coverage Audit
- Hash Audit
- Type A Usability Audit
- Runtime DB Read Audit
- Repository Reality vs Import Reality vs Runtime Reality separation
- Asset Pipeline Audit
- chart_assets.db discovery and read-only inspection
- Type A / Type B asset evidence
- Deletion readiness gate
- MCP tool visibility / registration evidence

Purpose:
- Read-only architecture, runtime, artifact and governance audit
  for Rhythm Game Assistant (RGA).

Auditor responsibilities:
- repository reality audit
- runtime reality audit
- architecture governance audit
- artifact backbone audit
- flow contract audit
- deletion readiness governance

Boundary:
- Audit-only.
- Read-only.
- Must not modify Completed Phases 1–7.
- Must not write to databases.
- Must not mutate runtime behavior.
- Must not replace authoritative runtime output.

Governance model:
- GitHub Advanced Security:
    security validation

- RGA Auditor:
    architecture and runtime governance

Recommended placement:
- tools/runtime_auditor.py

Phase Boundary Policy
---------------------

Completed Phases are immutable:

    Phase 1–2
        chart understanding
        tip generation

    Phase 3
        canonical_row ingestion backbone

    Phase 4–4.5
        personalization
        localization

    Phase 5–7
        production and recommendation layers

Auditor extensions may:

    inspect
    verify
    classify
    report

Auditor extensions must not:

    mutate phase logic
    rewrite runtime outputs
    modify canonical_row
    modify personalization
    modify localization
    modify recommendation internals
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

    #
    # Discovery metadata.
    #
    runtime_ready_hint: bool = False

    artifact_backbone_hint: bool = False

@dataclass
class ArtifactDatabaseSnapshot:

    logical_name: str

    path: str

    exists: bool
    readable: bool

    tables: List[str]

    table_columns: Dict[
        str,
        List[str],
    ]

    table_row_counts: Dict[
        str,
        Any,
    ]

    candidate_columns: Dict[
        str,
        Dict[str, Optional[str]]
    ]

    #
    # Governance metadata.
    #
    artifact_contract_root: str = (
        "artifact_database_policy"
    )

    read_mode: str = (
        "sqlite_readonly"
    )

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

#
# Canonical artifact backbone.
#
# file_scan_inventory.db
#       ->
# chart_assets.db
#       ->
# chart_patterns.db
#
# audit helpers may inspect this chain.
# They must not mutate it.
#
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
# but introduces explicit scope helpers so audit can distinguish:
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

    #
    # Evidence-aware governance states.
    #
    "ready",
    "review_needed",
    "runtime_limited",
    "blocked",
]

#
# Discovery weighting used by repository/runtime candidate scoring.
#
# Kept separate from ARTIFACT_WEIGHTS so governance scoring can evolve
# independently from repository detection scoring.
#
GOVERNANCE_DISCOVERY_WEIGHT = 25

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
# These contracts are considered independently actionable.
#
ROOT_CONTRACT_METADATA: Dict[str, Dict[str, Any]] = {

    "artifact_database_policy": {
        "domain": "artifact_backbone",
        "severity": "root",
    },

    "deletion_readiness": {
        "domain": "artifact_backbone",
        "severity": "root",
    },
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
    # and audit contracts from succeeding.
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


def score_candidate(
    root: Path,
) -> RuntimeCandidate:

    matched: List[str] = []
    missing: List[str] = []

    score = 0

    for artifact, weight in (
        ARTIFACT_WEIGHTS.items()
    ):

        exists, _matched_path = (
            artifact_exists_with_alias(
                root,
                artifact,
            )
        )

        if exists:

            matched.append(
                artifact
            )

            score += weight

        else:

            missing.append(
                artifact
            )

    if score >= 90:
        confidence = "high"

    elif score >= 60:
        confidence = "medium"

    elif score >= 40:
        confidence = "partial"

    else:
        confidence = "low"

    candidate = RuntimeCandidate(
        root=str(
            root.resolve()
        ),

        score=score,

        confidence=confidence,

        matched=matched,

        missing=missing,

        governance_score=0,
    )

    candidate.governance_score = (
        governance_candidate_score(
            candidate
        )
    )

    return candidate

def discover_files(search_root: Path) -> Dict[str, List[str]]:
    patterns = {
        "main.py": "main.py",
        "recommend.py": "recommend.py",
        "app.py": "app.py",
        "runtime_meta.py": "runtime_meta.py",
        "mcp_server.py": "mcp_server.py",
        "runtime_auditor.py": "runtime_auditor.py",
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

def discover_runtime_candidates(
    search_root: Path,
) -> List[
    RuntimeCandidate
]:

    roots: Dict[str, Path] = {}

    try:

        for main_py in (
            search_root.rglob(
                "main.py"
            )
        ):

            root = (
                main_py.parent.resolve()
            )

            roots[
                str(root)
            ] = root

        for rec_py in (
            search_root.rglob(
                "recommend.py"
            )
        ):

            parts = list(
                rec_py.parts
            )

            if "src" in parts:

                idx = parts.index(
                    "src"
                )

                if idx > 0:

                    candidate = (
                        Path(
                            *parts[:idx]
                        )
                        .resolve()
                    )

                    roots[
                        str(candidate)
                    ] = candidate

    except Exception:
        pass

    candidates = [
        score_candidate(
            root
        )
        for root
        in roots.values()
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

    if (
        "No module named 'rhythm_ingestion'"
        in error_text
    ):

        if (
            package_dirs.get(
                "invalid_aliases"
            )
            and not package_dirs.get(
                "expected"
            )
        ):
            return (
                "package_identity_failure"
            )

        return (
            "missing_pythonpath_or_package"
        )

    if (
        "No module named"
        in error_text
    ):
        return (
            "dependency_missing"
        )

    if (
        "cannot import name"
        in error_text
    ):
        return (
            "runtime_contract_break"
        )

    return (
        "import_failure"
    )

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
        or normalized.endswith("runtime_auditor_report.json")
        or normalized.endswith("runtime_auditor_report.md")
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

        discovered[key] = sorted(
            set(
                discovered.get(
                    key,
                    [],
                )
            )
        )

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

    matched = set(
        candidate.matched
    )

    required = {
        FILE_SCAN_INVENTORY_DB_NAME,
        CHART_ASSETS_DB_NAME,
        CHART_PATTERNS_DB_NAME,
        "mcp_server.py",
    }

    score += (
        len(
            required.intersection(
                matched
            )
        )
        * GOVERNANCE_DISCOVERY_WEIGHT
    )

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
# Auditor
# -----------------------------------------------------------------------------

class RuntimeAuditor:

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

        #
        # ----------------------------------------------------------
        # Repository / Runtime Discovery
        # ----------------------------------------------------------
        #

        self.repo_root = (
            repo_root.resolve()
        )

        (
            self.backend_root,
            self.backend_candidates,
            self.backend_root_mode,
        ) = choose_backend_root(
            self.repo_root,
            backend_root,
        )

        self.api_url = api_url

        self.token = (
            token
            or os.getenv(
                "SOFTR_API_TOKEN"
            )
        )

        self.mcp_config = (
            mcp_config
        )

        self.run_rest = (
            run_rest
        )

        #
        # ----------------------------------------------------------
        # Artifact DB Inputs
        # ----------------------------------------------------------
        #

        #
        # v0.6 compatibility
        #

        self.asset_db = (
            asset_db
        )

        #
        # v0.7+ explicit DB support
        #

        self.file_scan_inventory_db = (
            file_scan_inventory_db
        )

        self.chart_assets_db = (
            chart_assets_db
            or asset_db
        )

        self.chart_patterns_db = (
            chart_patterns_db
        )

        #
        # ----------------------------------------------------------
        # Repository Discovery Evidence
        # ----------------------------------------------------------
        #

        self.discovered_files = (
            discover_files(
                self.repo_root
            )
        )

        self.discovered_packages = (
            discover_package_dirs(
                self.repo_root
            )
        )

        self.discovered_assets = (
            discover_asset_files(
                self.repo_root
            )
        )

        #
        # ----------------------------------------------------------
        # Result State
        # ----------------------------------------------------------
        #

        self.results: List[
            CheckResult
        ] = []

        #
        # ----------------------------------------------------------
        # Snapshot Caches
        # ----------------------------------------------------------
        #

        #
        # v0.6 compatibility
        #

        self.asset_db_snapshots: List[
            Dict[str, Any]
        ] = []

        #
        # v0.7+
        #

        self.artifact_db_snapshots: Dict[
            str,
            List[
                Dict[str, Any]
            ],
        ] = {}

        self.artifact_db_records: Dict[
            str,
            List[
                Dict[str, Any]
            ],
        ] = {}

        #
        # ----------------------------------------------------------
        # Hash Caches
        # ----------------------------------------------------------
        #

        self.repository_asset_hashes: Dict[
            str,
            str,
        ] = {}

        self.repository_file_hashes: Dict[
            str,
            str,
        ] = {}

        #
        # ----------------------------------------------------------
        # Governance State
        #
        # Governance must distinguish:
        #
        #   hint
        #       != suspicion
        #       != evidence
        #
        # Dependency blockers
        #       != governance blockers
        #
        # Runtime blockers
        #       != governance blockers
        #
        # Completed phases remain immutable.
        # Auditor remains read-only.
        # ----------------------------------------------------------
        #

        self.governance_state: Dict[
            str,
            Any,
        ] = {

            #
            # Top-level verdicts
            #

            "architecture_verdict":
                None,

            "runtime_verdict":
                None,

            "artifact_backbone_verdict":
                None,

            "flow_contract_verdict":
                None,

            "layer_boundary_verdict":
                None,

            "mcp_contract_verdict":
                None,

            "deletion_verdict":
                None,

            "governance_verdict":
                None,

            #
            # Failure lineage
            #

            "root_failures":
                [],

            "derived_failures":
                [],

            #
            # Runtime reality
            #

            "dependency_failures":
                [],

            "governance_failures":
                [],

            #
            # Layer boundary telemetry
            #

            "layer_boundary_risk": {

                "status":
                    None,

                "highest_confidence":
                    "none",

                "evidence_count":
                    0,

                "suspicion_count":
                    0,

                "hint_count":
                    0,

                "governance_blocking":
                    False,
            },

            #
            # Accounting
            #

            "blocking_reasons":
                [],

            "warnings":
                [],

            #
            # Confidence model
            #

            "confidence_summary": {

                "evidence":
                    0,

                "suspicion":
                    0,

                "hint":
                    0,
            },

            #
            # Audit Policy
            #

            "policy": {

                "completed_phases":
                    "immutable",

                "auditor_mode":
                    "read_only",

                "false_positive_isolation":
                    True,

                "dependency_failures_are_not_governance_failures":
                    True,

                "runtime_failures_are_not_governance_failures":
                    True,

                "boundary_confidence_model": {

                    "hint": {
                        "severity":
                            "info",

                        "governance_blocking":
                            False,
                    },

                    "suspicion": {
                        "severity":
                            "warning",

                        "governance_blocking":
                            False,
                    },

                    "evidence": {
                        "severity":
                            "critical",

                        "governance_blocking":
                            True,
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

        #
        # ----------------------------------------------------------
        # Environment
        # ----------------------------------------------------------
        #

        if (
            domain == "environment"
            and check
            == "softr_api_token_present"
        ):

            if self.token:
                return (
                    "pass",
                    "info",
                )

            if self.run_rest:
                return (
                    "fail",
                    "fail",
                )

            return (
                "warning",
                "warning",
            )

        #
        # ----------------------------------------------------------
        # Explicit skips
        # ----------------------------------------------------------
        #

        if (
            domain == "mcp"
            and check == "config_present"
            and base_status == "skipped"
        ):
            return (
                "skipped",
                "info",
            )

        if (
            domain == "rest_api"
            and check
            == "rest_audit_enabled"
            and base_status == "skipped"
        ):
            return (
                "skipped",
                "info",
            )

        if (
            domain == "flow_audit"
            and base_status == "skipped"
        ):
            return (
                "skipped",
                "info",
            )

        if (
            domain == "flow_contract_audit"
            and base_status == "skipped"
        ):
            return (
                "skipped",
                "info",
            )

        if (
            domain == "type_B_intelligence"
            and base_status == "skipped"
        ):
            return (
                "skipped",
                "info",
            )

        #
        # ----------------------------------------------------------
        # Repository Reality
        # ----------------------------------------------------------
        #

        if (
            domain == "repo"
            and base_status == "warning"
        ):

            if self.backend_root_mode in {
                "auto_discovered",
                "explicit",
                "partial_discovery",
            }:
                return (
                    "warning",
                    "warning",
                )

            return (
                "fail",
                "fail",
            )

        #
        # ----------------------------------------------------------
        # Dependency Reality
        #
        # Runtime blocker.
        # Not automatic governance blocker.
        # ----------------------------------------------------------
        #

        if (
            domain
            == "dependency_reality"
        ):

            if base_status == "pass":
                return (
                    "pass",
                    "info",
                )

            if base_status == "warning":
                return (
                    "warning",
                    "warning",
                )

            if base_status == "fail":
                return (
                    "fail",
                    "warning",
                )

        #
        # ----------------------------------------------------------
        # Runtime import reality
        # ----------------------------------------------------------
        #

        if (
            domain
            == "runtime_import"
        ):
            if base_status == "fail":
                return (
                    "fail",
                    "warning",
                )

        #
        # ----------------------------------------------------------
        # Layer boundaries
        # ----------------------------------------------------------
        #

        if (
            domain
            == "layer_separation"
        ):

            mapping = {
                "pass":
                    ("pass", "info"),

                "info":
                    ("info", "info"),

                "warning":
                    (
                        "warning",
                        "warning",
                    ),

                "critical":
                    (
                        "critical",
                        "critical",
                    ),
            }

            return mapping.get(
                base_status,
                (
                    base_status,
                    "warning",
                ),
            )

        #
        # ----------------------------------------------------------
        # Governance
        # ----------------------------------------------------------
        #

        if (
            domain
            == "governance"
        ):

            if base_status == "warning":
                return (
                    "warning",
                    "warning",
                )

            if base_status == "fail":
                return (
                    "fail",
                    "critical",
                )

            if base_status == "critical":
                return (
                    "critical",
                    "critical",
                )

        #
        # ----------------------------------------------------------
        # Root governance contracts
        # ----------------------------------------------------------
        #

        if (
            domain in {
                "artifact_relationships",
                "artifact_backbone",
                "mcp_contract",
                "flow_contract_audit",
            }
            and base_status == "fail"
        ):
            return (
                "fail",
                "fail",
            )

        #
        # ----------------------------------------------------------
        # Default mapping
        # ----------------------------------------------------------
        #

        mapping = {
            "pass": "info",
            "info": "info",
            "warning": "warning",
            "skipped": "info",
            "fail": "fail",
            "critical": "critical",
        }

        return (
            base_status,
            mapping.get(
                base_status,
                "warning",
            ),
        )

    def add(
        self,
        *,
        domain: str,
        check: str,
        status: str,
        summary: str,
        evidence: Optional[
            Dict[str, Any]
        ] = None,
        suggested_fix: Optional[str] = None,
        governance_domain: Optional[str] = None,
        contract_type: Optional[str] = None,
    ) -> None:

        final_status, severity = (
            self.classify(
                domain=domain,
                check=check,
                base_status=status,
            )
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

        self.results.append(
            result
        )

        #
        # Governance accounting only.
        # Final verdict generation occurs later.
        #

        if severity in {
            "fail",
            "critical",
        }:

            self.governance_state[
                "blocking_reasons"
            ].append(
                {
                    "domain": domain,
                    "check": check,
                    "severity": severity,
                    "summary": summary,
                    "governance_domain":
                        governance_domain,
                    "contract_type":
                        contract_type,
                }
            )

        elif (
            final_status
            == "warning"
        ):

            self.governance_state[
                "warnings"
            ].append(
                {
                    "domain": domain,
                    "check": check,
                    "summary": summary,
                    "governance_domain":
                        governance_domain,
                    "contract_type":
                        contract_type,
                }
            )

    def inject_pythonpath(
        self,
    ) -> None:

        src = (
            self.backend_root
            / "src"
        )

        src_pkg = (
            src
            / EXPECTED_PACKAGE
        )

        for path in [
            src,
            src_pkg,
            self.backend_root,
        ]:

            path_text = str(
                path
            )

            if (
                path_text
                not in sys.path
            ):
                sys.path.insert(
                    0,
                    path_text,
                )

    def read_json_file(
        self,
        path: Path,
    ) -> Optional[
        Dict[str, Any]
    ]:

        try:

            data = json.loads(
                path.read_text(
                    encoding="utf-8",
                )
            )

            if isinstance(
                data,
                dict,
            ):
                return data

            self.add(
                domain="file",
                check="json_shape",
                status="fail",
                summary=(
                    f"JSON file is valid but does not contain "
                    f"an object: {path}"
                ),
                evidence={
                    "path":
                        str(path),
                    "actual_type":
                        type(
                            data
                        ).__name__,
                },
            )

            return None

        except Exception as exc:

            self.add(
                domain="file",
                check="json_parse",
                status="fail",
                summary=(
                    f"Could not parse JSON file: {path}"
                ),
                evidence={
                    "path":
                        str(path),
                    "error":
                        str(exc),
                },
            )

            return None

    def post_json(
        self,
        payload: Dict[str, Any],
    ) -> Any:

        body = json.dumps(
            payload
        ).encode(
            "utf-8"
        )

        headers = {
            "Content-Type":
                "application/json",

            "Accept":
                "application/json",
        }

        if self.token:
            headers[
                "Authorization"
            ] = (
                f"Bearer {self.token}"
            )

        request = (
            urllib.request.Request(
                self.api_url,
                data=body,
                headers=headers,
                method="POST",
            )
        )

        with urllib.request.urlopen(
            request,
            timeout=15,
        ) as response:

            text = (
                response.read()
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )

            if not text:
                return {}

            return json.loads(
                text
            )

    def record_boundary_signal(
        self,
        *,
        confidence: str,
    ) -> None:

        summary = (
            self.governance_state.setdefault(
                "confidence_summary",
                {},
            )
        )

        summary[
            confidence
        ] = (
            summary.get(
                confidence,
                0,
            )
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

        governance_blocking = (
            evidence_count > 0
        )

        highest_confidence = (
            "evidence"
            if evidence_count > 0
            else (
                "suspicion"
                if suspicion_count > 0
                else (
                    "hint"
                    if hint_count > 0
                    else "none"
                )
            )
        )

        self.governance_state[
            "layer_boundary_risk"
        ] = {

            "status":
                status,

            "highest_confidence":
                highest_confidence,

            "evidence_count":
                evidence_count,

            "suspicion_count":
                suspicion_count,

            "hint_count":
                hint_count,

            "governance_blocking":
                governance_blocking,

            "confidence_model": [
                "hint",
                "suspicion",
                "evidence",
            ],

            "blocking_confidence": [
                "evidence",
            ],
        }

        self.governance_state[
            "confidence_summary"
        ] = {
            "evidence":
                evidence_count,
            "suspicion":
                suspicion_count,
            "hint":
                hint_count,
        }

    # ------------------------------------------------------------------
    # Artifact DB candidate helpers
    # ------------------------------------------------------------------

    def resolve_artifact_db_candidates(
        self,
        db_name: str,
    ) -> List[Path]:
        #
        # ----------------------------------------------------------
        # Artifact DB Candidate Resolution
        #
        # Resolution order:
        #
        #   1. Explicit CLI override
        #   2. Repository discovery evidence
        #   3. Defensive filename search
        #
        # Candidate resolution is discovery only.
        # No file creation or mutation is permitted.
        # ----------------------------------------------------------
        #

        candidates: List[Path] = []

        explicit_map: Dict[str, Optional[Path]] = {
            FILE_SCAN_INVENTORY_DB_NAME:
                self.file_scan_inventory_db,

            CHART_ASSETS_DB_NAME:
                self.chart_assets_db,

            CHART_PATTERNS_DB_NAME:
                self.chart_patterns_db,
        }

        explicit = explicit_map.get(
            db_name
        )

        if explicit:

            try:
                resolved = (
                    explicit
                    .expanduser()
                    .resolve()
                )

                candidates.append(
                    resolved
                )

            except Exception:
                pass

        discovered_key_map = {
            FILE_SCAN_INVENTORY_DB_NAME:
                "file_scan_inventory_db",

            CHART_ASSETS_DB_NAME:
                "chart_assets_db",

            CHART_PATTERNS_DB_NAME:
                "chart_patterns_db",
        }

        discovered_key = (
            discovered_key_map.get(
                db_name
            )
        )

        if discovered_key:

            for item in self.discovered_assets.get(
                discovered_key,
                [],
            ):

                try:
                    path = (
                        Path(
                            item
                        )
                        .resolve()
                    )

                    if path not in candidates:
                        candidates.append(
                            path
                        )

                except Exception:
                    continue

        #
        # Defensive fallback.
        #
        # Repository discovery may miss databases when
        # runtime roots are incomplete.
        #
        # Filename search remains discovery-only evidence.
        #

        if not candidates:

            try:
                for path in self.repo_root.rglob(
                    db_name
                ):

                    try:
                        resolved = (
                            path.resolve()
                        )

                        if (
                            resolved
                            not in candidates
                        ):
                            candidates.append(
                                resolved
                            )

                    except Exception:
                        continue

            except Exception:
                pass

        #
        # Stable deterministic ordering.
        #

        candidates = sorted(
            set(
                candidates
            ),
            key=lambda p: str(p),
        )

        return candidates


    def resolve_all_artifact_db_candidates(
        self,
    ) -> Dict[str, List[Path]]:
        return {
            db_name:
                self.resolve_artifact_db_candidates(
                    db_name
                )
            for db_name
            in ARTIFACT_DATABASE_NAMES
        }


    #
    # v0.6 compatibility
    #

    def resolve_asset_db_candidates(
        self,
    ) -> List[Path]:
        return self.resolve_artifact_db_candidates(
            CHART_ASSETS_DB_NAME
        )


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
        #
        # ----------------------------------------------------------
        # SQLite Read-Only Inspection
        #
        # Evidence collection only.
        #
        # Allowed:
        #   schema inventory
        #   column discovery
        #   row counts
        #   samples
        #
        # Prohibited:
        #   insert
        #   update
        #   delete
        #   schema mutation
        # ----------------------------------------------------------
        #

        sample_limit = max(
            int(sample_limit or 0),
            1,
        )

        evidence: Dict[str, Any] = {
            "logical_name":
                logical_name,

            "path":
                str(path),

            "exists":
                path.exists(),

            "readable":
                False,

            "tables":
                [],

            "table_columns":
                {},

            "table_row_counts":
                {},

            "table_samples":
                {},

            "candidate_columns":
                {},

            "read_mode":
                "sqlite_readonly",

            "artifact_contract_root":
                "artifact_database_policy",
        }

        if not path.exists():
            return evidence

        try:
            uri = sqlite_readonly_uri(
                path
            )

            with sqlite3.connect(
                uri,
                uri=True,
            ) as conn:

                conn.row_factory = (
                    sqlite3.Row
                )

                cursor = conn.cursor()

                tables = [
                    row[0]
                    for row in cursor.execute(
                        (
                            "SELECT name "
                            "FROM sqlite_master "
                            "WHERE type='table' "
                            "ORDER BY name"
                        )
                    ).fetchall()
                ]

                evidence[
                    "readable"
                ] = True

                evidence[
                    "tables"
                ] = tables

                for table in tables:

                    quoted_table = (
                        table_quote(
                            table
                        )
                    )

                    columns = [
                        row[1]
                        for row in cursor.execute(
                            f"PRAGMA table_info({quoted_table})"
                        ).fetchall()
                    ]

                    evidence[
                        "table_columns"
                    ][table] = columns

                    candidate_columns = {
                        "path":
                            first_existing(
                                columns,
                                PATH_COLUMN_CANDIDATES,
                            ),

                        "hash":
                            first_existing(
                                columns,
                                HASH_COLUMN_CANDIDATES,
                            ),

                        "text":
                            first_existing(
                                columns,
                                TEXT_COLUMN_CANDIDATES,
                            ),

                        "reference_url":
                            first_existing(
                                columns,
                                REFERENCE_URL_COLUMN_CANDIDATES,
                            ),

                        "type":
                            first_existing(
                                columns,
                                TYPE_COLUMN_CANDIDATES,
                            ),

                        "pattern":
                            first_existing(
                                columns,
                                PATTERN_COLUMN_CANDIDATES,
                            ),

                        "chart_id":
                            first_existing(
                                columns,
                                CHART_ID_COLUMN_CANDIDATES,
                            ),

                        "timestamp":
                            first_existing(
                                columns,
                                TIMESTAMP_COLUMN_CANDIDATES,
                            ),
                    }

                    evidence[
                        "candidate_columns"
                    ][table] = candidate_columns

                    #
                    # Row counts
                    #

                    try:
                        count = (
                            cursor.execute(
                                f"SELECT COUNT(*) FROM {quoted_table}"
                            )
                            .fetchone()[0]
                        )

                        evidence[
                            "table_row_counts"
                        ][table] = count

                    except Exception as exc:

                        evidence[
                            "table_row_counts"
                        ][table] = {
                            "error":
                                str(
                                    exc
                                )
                        }

                    #
                    # Samples
                    #

                    try:
                        rows = (
                            cursor.execute(
                                (
                                    f"SELECT * "
                                    f"FROM {quoted_table} "
                                    f"LIMIT ?"
                                ),
                                (
                                    sample_limit,
                                ),
                            )
                            .fetchall()
                        )

                        evidence[
                            "table_samples"
                        ][table] = [
                            truncate_row(
                                dict(row)
                            )
                            for row in rows
                        ]

                    except Exception as exc:

                        evidence[
                            "table_samples"
                        ][table] = {
                            "error":
                                str(
                                    exc
                                )
                        }

        except Exception as exc:

            evidence[
                "error"
            ] = str(
                exc
            )

            evidence[
                "traceback"
            ] = traceback.format_exc()

            evidence[
                "readable"
            ] = False

        return evidence


    def get_artifact_db_snapshots(
        self,
        db_name: str,
    ) -> List[Dict[str, Any]]:
        #
        # Cached snapshot accessor.
        #

        if (
            db_name
            not in self.artifact_db_snapshots
        ):

            logical_name = (
                ARTIFACT_DATABASE_LOGICAL_NAMES.get(
                    db_name,
                    db_name,
                )
            )

            self.artifact_db_snapshots[
                db_name
            ] = [
                self.inspect_sqlite_readonly(
                    path,
                    logical_name=logical_name,
                )
                for path in self.resolve_artifact_db_candidates(
                    db_name
                )
            ]

        return self.artifact_db_snapshots[
            db_name
        ]


    def get_all_artifact_db_snapshots(
        self,
    ) -> Dict[str, List[Dict[str, Any]]]:

        return {
            db_name:
                self.get_artifact_db_snapshots(
                    db_name
                )
            for db_name
            in ARTIFACT_DATABASE_NAMES
        }


    #
    # v0.6 compatibility
    #

    def get_asset_db_snapshots(
        self,
    ) -> List[Dict[str, Any]]:

        if not self.asset_db_snapshots:

            self.asset_db_snapshots = (
                self.get_artifact_db_snapshots(
                    CHART_ASSETS_DB_NAME
                )
            )

        return self.asset_db_snapshots

    # ------------------------------------------------------------------
    # DB record iteration helpers
    # ------------------------------------------------------------------

    def iter_artifact_db_records(
        self,
        db_name: str,
    ) -> List[Dict[str, Any]]:
        #
        # ----------------------------------------------------------
        # Artifact DB Record Iteration
        #
        # Read-only helper.
        #
        # Discovers usable artifact records from configured
        # artifact backbone databases.
        #
        # No mutation is permitted.
        # ----------------------------------------------------------
        #

        if db_name in self.artifact_db_records:
            return self.artifact_db_records[
                db_name
            ]

        records: List[Dict[str, Any]] = []

        for snapshot in self.get_artifact_db_snapshots(
            db_name
        ):

            db_path = snapshot.get(
                "path"
            )

            if (
                not db_path
                or snapshot.get(
                    "error"
                )
                or not snapshot.get(
                    "exists"
                )
            ):
                continue

            try:
                uri = sqlite_readonly_uri(
                    Path(
                        db_path
                    )
                )

                with sqlite3.connect(
                    uri,
                    uri=True,
                ) as conn:

                    conn.row_factory = (
                        sqlite3.Row
                    )

                    cursor = conn.cursor()

                    for table in snapshot.get(
                        "tables",
                        [],
                    ):

                        columns = (
                            snapshot.get(
                                "table_columns",
                                {},
                            ).get(
                                table,
                                [],
                            )
                        )

                        candidate_columns = (
                            snapshot.get(
                                "candidate_columns",
                                {},
                            ).get(
                                table,
                                {},
                            )
                        )

                        quoted_table = (
                            table_quote(
                                table
                            )
                        )

                        selected_columns = [
                            column
                            for column in [
                                candidate_columns.get(
                                    "path"
                                ),
                                candidate_columns.get(
                                    "hash"
                                ),
                                candidate_columns.get(
                                    "text"
                                ),
                                candidate_columns.get(
                                    "reference_url"
                                ),
                                candidate_columns.get(
                                    "type"
                                ),
                                candidate_columns.get(
                                    "pattern"
                                ),
                                candidate_columns.get(
                                    "chart_id"
                                ),
                                candidate_columns.get(
                                    "timestamp"
                                ),
                            ]
                            if column
                        ]

                        if not selected_columns:
                            continue

                        select_sql = ", ".join(
                            table_quote(
                                column
                            )
                            for column
                            in selected_columns
                        )

                        rows = cursor.execute(
                            (
                                f"SELECT {select_sql} "
                                f"FROM {quoted_table}"
                            )
                        ).fetchall()

                        for row in rows:
                            row_dict = dict(
                                row
                            )

                            records.append(
                                {
                                    "db_name":
                                        db_name,

                                    "logical_name":
                                        ARTIFACT_DATABASE_LOGICAL_NAMES.get(
                                            db_name,
                                            db_name,
                                        ),

                                    "db_path":
                                        db_path,

                                    "table":
                                        table,

                                    "columns":
                                        columns,

                                    "path": (
                                        row_dict.get(
                                            candidate_columns.get(
                                                "path"
                                            )
                                        )
                                        if candidate_columns.get(
                                            "path"
                                        )
                                        else None
                                    ),

                                    "hash": (
                                        row_dict.get(
                                            candidate_columns.get(
                                                "hash"
                                            )
                                        )
                                        if candidate_columns.get(
                                            "hash"
                                        )
                                        else None
                                    ),

                                    "text": (
                                        row_dict.get(
                                            candidate_columns.get(
                                                "text"
                                            )
                                        )
                                        if candidate_columns.get(
                                            "text"
                                        )
                                        else None
                                    ),

                                    "reference_url": (
                                        row_dict.get(
                                            candidate_columns.get(
                                                "reference_url"
                                            )
                                        )
                                        if candidate_columns.get(
                                            "reference_url"
                                        )
                                        else None
                                    ),

                                    "asset_type": (
                                        row_dict.get(
                                            candidate_columns.get(
                                                "type"
                                            )
                                        )
                                        if candidate_columns.get(
                                            "type"
                                        )
                                        else None
                                    ),

                                    "pattern": (
                                        row_dict.get(
                                            candidate_columns.get(
                                                "pattern"
                                            )
                                        )
                                        if candidate_columns.get(
                                            "pattern"
                                        )
                                        else None
                                    ),

                                    "chart_id": (
                                        row_dict.get(
                                            candidate_columns.get(
                                                "chart_id"
                                            )
                                        )
                                        if candidate_columns.get(
                                            "chart_id"
                                        )
                                        else None
                                    ),

                                    "timestamp": (
                                        row_dict.get(
                                            candidate_columns.get(
                                                "timestamp"
                                            )
                                        )
                                        if candidate_columns.get(
                                            "timestamp"
                                        )
                                        else None
                                    ),

                                    #
                                    # Governance metadata
                                    #

                                    "artifact_backbone_member":
                                        (
                                            db_name
                                            in ARTIFACT_DATABASE_NAMES
                                        ),

                                    "read_mode":
                                        "readonly",

                                    "source":
                                        "artifact_backbone",
                                }
                            )

            except Exception:
                #
                # Read helpers should remain resilient.
                #
                continue

        self.artifact_db_records[
            db_name
        ] = records

        return records


    def iter_all_artifact_db_records(
        self,
    ) -> Dict[str, List[Dict[str, Any]]]:

        return {
            db_name:
                self.iter_artifact_db_records(
                    db_name
                )
            for db_name
            in ARTIFACT_DATABASE_NAMES
        }


    #
    # v0.6 compatibility wrappers
    #

    def iter_asset_db_records(
        self,
    ) -> List[Dict[str, Any]]:
        return self.iter_artifact_db_records(
            CHART_ASSETS_DB_NAME
        )


    def iter_file_scan_inventory_records(
        self,
    ) -> List[Dict[str, Any]]:
        return self.iter_artifact_db_records(
            FILE_SCAN_INVENTORY_DB_NAME
        )


    def iter_chart_pattern_records(
        self,
    ) -> List[Dict[str, Any]]:
        return self.iter_artifact_db_records(
            CHART_PATTERNS_DB_NAME
        )


    # ------------------------------------------------------------------
    # Hash helpers
    # ------------------------------------------------------------------

    def compute_repository_asset_hashes(
        self,
    ) -> Dict[str, str]:
        #
        # Scoped asset hashes only.
        #
        # Validation evidence.
        # Not a repository-wide integrity pass.
        #

        if self.repository_asset_hashes:
            return self.repository_asset_hashes

        paths = [
            Path(item)
            for item in self.discovered_assets.get(
                "type_A",
                [],
            )
        ]

        paths += [
            Path(item)
            for item in self.discovered_assets.get(
                "type_B",
                [],
            )
        ]

        hashes: Dict[str, str] = {}

        for path in paths:

            try:
                hashes[
                    str(
                        path.resolve()
                    )
                ] = sha256_file(
                    path
                )

            except Exception:
                continue

        self.repository_asset_hashes = (
            hashes
        )

        return hashes


    def compute_repository_file_hashes(
        self,
    ) -> Dict[str, str]:
        #
        # Repository-wide evidence helper.
        #
        # Not used for deletion readiness.
        #

        if self.repository_file_hashes:
            return self.repository_file_hashes

        hashes: Dict[str, str] = {}

        try:
            for path in self.repo_root.rglob(
                "*"
            ):

                if not path.is_file():
                    continue

                normalized = (
                    normalize_path_text(
                        path
                    )
                )

                #
                # Ignore git internals and generated
                # workflow artifacts.
                #

                if (
                    "/.git/" in normalized
                    or "/artifacts/" in normalized
                ):
                    continue

                try:
                    hashes[
                        str(
                            path.resolve()
                        )
                    ] = sha256_file(
                        path
                    )

                except Exception:
                    continue

        except Exception:
            pass

        self.repository_file_hashes = (
            hashes
        )

        return hashes


    # ------------------------------------------------------------------
    # Preconditions / capability helpers
    # ------------------------------------------------------------------

    def package_import_probe_passed(
        self,
    ) -> bool:

        for result in self.results:

            if (
                result.domain
                == "package_layout"
                and result.check
                == "package_import_probe"
            ):
                return (
                    result.status
                    == "pass"
                )

        return False


    def runtime_import_probe_passed(
        self,
    ) -> bool:

        for result in self.results:

            if (
                result.domain
                == "runtime_import"
                and result.check
                == "recommend_module_importable"
            ):
                return (
                    result.status
                    == "pass"
                )

        return False


    def dependency_reality_passed(
        self,
    ) -> bool:

        for result in self.results:

            if (
                result.domain
                == "dependency_reality"
                and result.check
                == "runtime_dependency_probe"
            ):
                return (
                    result.status
                    == "pass"
                )

        return False


    def artifact_db_has_readable_rows(
        self,
        db_name: str,
    ) -> bool:
        #
        # audit helper.
        #
        # Presence alone is insufficient.
        # At least one readable row must exist.
        #

        snapshots = (
            self.get_artifact_db_snapshots(
                db_name
            )
        )

        for snapshot in snapshots:

            if (
                not snapshot.get(
                    "exists"
                )
                or snapshot.get(
                    "error"
                )
            ):
                continue

            for count in snapshot.get(
                "table_row_counts",
                {},
            ).values():

                if (
                    isinstance(
                        count,
                        int,
                    )
                    and count > 0
                ):
                    return True

        return False


    def artifact_db_present(
        self,
        db_name: str,
    ) -> bool:

        return bool(
            self.resolve_artifact_db_candidates(
                db_name
            )
        )


    def artifact_backbone_present(
        self,
    ) -> bool:
        #
        # Presence only.
        #
        # Readability is evaluated separately.
        #

        return all(
            self.artifact_db_present(
                db_name
            )
            for db_name
            in ARTIFACT_DATABASE_NAMES
        )


    def readable_artifact_db_count(
        self,
    ) -> int:

        count = 0

        for db_name in ARTIFACT_DATABASE_NAMES:

            for snapshot in self.get_artifact_db_snapshots(
                db_name
            ):

                if (
                    snapshot.get(
                        "exists"
                    )
                    and snapshot.get(
                        "readable"
                    )
                    and not snapshot.get(
                        "error"
                    )
                ):
                    count += 1

        return count


    def artifact_backbone_readable(
        self,
    ) -> bool:
        #
        # Every required backbone DB must have
        # at least one readable candidate.
        #

        for db_name in ARTIFACT_DATABASE_NAMES:

            snapshots = (
                self.get_artifact_db_snapshots(
                    db_name
                )
            )

            if not snapshots:
                return False

            readable = any(
                snapshot.get(
                    "exists"
                )
                and snapshot.get(
                    "readable"
                )
                and not snapshot.get(
                    "error"
                )
                for snapshot
                in snapshots
            )

            if not readable:
                return False

        return True


    def artifact_relationship_readiness(
        self,
    ) -> Dict[str, bool]:
        #
        # Readiness helper.
        #
        # Presence + readable rows.
        #

        return {
            "scan_db_has_rows":
                self.artifact_db_has_readable_rows(
                    FILE_SCAN_INVENTORY_DB_NAME
                ),

            "asset_db_has_rows":
                self.artifact_db_has_readable_rows(
                    CHART_ASSETS_DB_NAME
                ),

            "pattern_db_has_rows":
                self.artifact_db_has_readable_rows(
                    CHART_PATTERNS_DB_NAME
                ),
        }


    def governance_readiness_snapshot(
        self,
    ) -> Dict[str, Any]:
        #
        # Compact backbone readiness snapshot.
        #
        # Intended for governance verdict generation.
        # No mutation authority.
        #

        relationship_state = (
            self.artifact_relationship_readiness()
        )

        readiness_state = (
            "ready"
            if (
                self.artifact_backbone_present()
                and self.artifact_backbone_readable()
                and all(
                    relationship_state.values()
                )
            )
            else "incomplete"
        )

        return {
            "artifact_backbone_present":
                self.artifact_backbone_present(),

            "artifact_backbone_readable":
                self.artifact_backbone_readable(),

            "relationship_state":
                relationship_state,

            "relationship_ready":
                all(
                    relationship_state.values()
                ),

            "readiness_state":
                readiness_state,

            "audit_layer":
                "artifact_backbone_governance",

            "governance_interpretation": (
                "This snapshot summarizes artifact backbone readiness. "
                "It does not authorize deletion, mutation, or remediation."
            ),
        }

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def check_environment(self) -> None:
        #
        # ----------------------------------------------------------
        # Environment
        #
        # Environment evidence only.
        #
        # This check does not verify repository layout,
        # dependency installation, runtime wiring,
        # recommendation behavior, or governance readiness.
        # ----------------------------------------------------------
        #

        self.add(
            domain="environment",
            check="python_runtime",
            status="info",
            summary="Python runtime information captured.",
            evidence={
                "python_executable":
                    sys.executable,

                "python_version":
                    sys.version,

                "platform":
                    platform.platform(),

                "audit_layer":
                    "environment",

                "note": (
                    "Environment capture records runtime facts only."
                ),
            },
        )

        token_present = bool(
            self.token
        )

        token_state = (
            "present"
            if token_present
            else "missing"
        )

        self.add(
            domain="environment",
            check="softr_api_token_present",
            status=(
                "pass"
                if token_present
                else "fail"
            ),
            summary=(
                "SOFTR_API_TOKEN is available to the auditor process."
                if token_present
                else (
                    "SOFTR_API_TOKEN is missing. "
                    "This blocks authenticated REST auditing only "
                    "when --rest is enabled."
                )
            ),
            evidence={
                "token_present":
                    token_present,

                "token_state":
                    token_state,

                "rest_checks_enabled":
                    self.run_rest,

                "runtime_impact": (
                    "authenticated_rest_possible"
                    if token_present
                    else (
                        "authenticated_rest_blocked"
                        if self.run_rest
                        else "no_runtime_effect"
                    )
                ),

                "governance_note": (
                    "Missing API credentials should not automatically "
                    "be treated as a governance failure."
                ),

                "audit_layer":
                    "environment",
            },
            suggested_fix=(
                None
                if token_present
                else (
                    "Set SOFTR_API_TOKEN or pass --token when "
                    "running REST auditing."
                )
            ),
        )


    def check_repository_discovery(self) -> None:
        #
        # ----------------------------------------------------------
        # Repository Discovery
        #
        # Discovery determines which backend candidate appears
        # most consistent with RGA runtime structure.
        #
        # Discovery does not verify package importability,
        # dependency availability, or runtime wiring.
        # ----------------------------------------------------------
        #

        candidates = [
            asdict(
                candidate
            )
            for candidate in self.backend_candidates
        ]

        best = (
            candidates[0]
            if candidates
            else None
        )

        if (
            self.backend_root_mode
            == "auto_discovered"
        ):
            status = "pass"

            summary = (
                "Backend root was discovered with sufficient confidence."
            )

            discovery_state = (
                "auto_discovered"
            )

        elif (
            self.backend_root_mode
            == "partial_discovery"
        ):
            status = "warning"

            summary = (
                "Partial runtime candidate was discovered."
            )

            discovery_state = (
                "partial_discovery"
            )

        elif (
            self.backend_root_mode
            == "explicit"
        ):
            status = "pass"

            summary = (
                "Backend root was provided explicitly."
            )

            discovery_state = (
                "explicit"
            )

        else:
            status = "fail"

            summary = (
                "No runtime candidate was discovered; auditor is "
                "falling back to repo root."
            )

            discovery_state = (
                "fallback_to_repo_root"
            )

        self.add(
            domain="repository_discovery",
            check="runtime_candidate_confidence",
            status=status,
            summary=summary,
            evidence={
                "repo_root":
                    str(
                        self.repo_root
                    ),

                "selected_backend_root":
                    str(
                        self.backend_root
                    ),

                "mode":
                    self.backend_root_mode,

                "discovery_state":
                    discovery_state,

                "candidate_count":
                    len(
                        candidates
                    ),

                "best_candidate":
                    best,

                "all_candidates":
                    candidates,

                "discovered_files":
                    self.discovered_files,

                "discovered_packages":
                    self.discovered_packages,

                "discovered_assets":
                    self.discovered_assets,

                "audit_layer":
                    "repository_discovery",

                "boundary_note": (
                    "Repository discovery identifies candidate roots only. "
                    "Import reality, dependency reality, and runtime wiring "
                    "must be audited separately."
                ),
            },
            suggested_fix=(
                None
                if status == "pass"
                else (
                    "Ensure backend root contains main.py, "
                    "mcp_server.py, and an importable "
                    "src/rhythm_ingestion package tree."
                )
            ),
            governance_domain="architecture_contracts",
            contract_type="repository_discovery",
        )


    def check_repository_vs_runtime(self) -> None:
        #
        # ----------------------------------------------------------
        # Repository vs Runtime Reality
        #
        # Separates:
        #
        #   repository reality
        #   import reality
        #   runtime reality
        #
        # These realities are related,
        # but not interchangeable.
        # ----------------------------------------------------------
        #

        canonical_package_root = (
            self.backend_root
            / "src"
            / EXPECTED_PACKAGE
        )

        repository_reality = {
            "backend_root_exists":
                self.backend_root.exists(),

            "canonical_package_root_exists":
                canonical_package_root.exists(),

            "main_py_exists":
                (
                    self.backend_root
                    / "main.py"
                ).exists(),

            "mcp_server_py_exists":
                (
                    self.backend_root
                    / "mcp_server.py"
                ).exists(),

            "artifact_database_candidates": {
                db_name: [
                    str(path)
                    for path in paths
                ]
                for db_name, paths
                in self.resolve_all_artifact_db_candidates().items()
            },
        }

        import_reality: Dict[str, Any] = {
            "rhythm_ingestion_importable":
                None,

            "rhythm_ingestion_file":
                None,

            "error":
                None,
        }

        self.inject_pythonpath()

        try:
            module = importlib.import_module(
                EXPECTED_PACKAGE
            )

            import_reality[
                "rhythm_ingestion_importable"
            ] = True

            import_reality[
                "rhythm_ingestion_file"
            ] = getattr(
                module,
                "__file__",
                None,
            )

        except Exception as exc:

            import_reality[
                "rhythm_ingestion_importable"
            ] = False

            import_reality[
                "error"
            ] = str(
                exc
            )

        runtime_reality = {
            "recommend_module_discovered":
                bool(
                    self.discovered_files.get(
                        "recommend.py"
                    )
                ),

            "runtime_meta_discovered":
                bool(
                    self.discovered_files.get(
                        "runtime_meta.py"
                    )
                ),

            "selected_backend_root":
                str(
                    self.backend_root
                ),
        }

        if not repository_reality[
            "canonical_package_root_exists"
        ]:
            status = "fail"

            summary = (
                "Repository reality does not show the canonical package root."
            )

            separation_state = (
                "repository_structure_failure"
            )

        elif (
            import_reality[
                "rhythm_ingestion_importable"
            ]
            is False
        ):
            status = "fail"

            summary = (
                "Repository package exists but import reality failed."
            )

            separation_state = (
                "import_reality_failure"
            )

        else:
            status = "pass"

            summary = (
                "Repository, import, and runtime realities are distinguishable."
            )

            separation_state = (
                "reality_separation_verified"
            )

        self.add(
            domain="repository_vs_runtime",
            check="reality_separation",
            status=status,
            summary=summary,
            evidence={
                "repository_reality":
                    repository_reality,

                "import_reality":
                    import_reality,

                "runtime_reality":
                    runtime_reality,

                "separation_state":
                    separation_state,

                "audit_layer":
                    "repository_import_runtime_separation",

                "architectural_principle": {
                    "repository_reality":
                        "filesystem structure",

                    "import_reality":
                        "python importability",

                    "runtime_reality":
                        "runtime discovery and execution surface",
                },

                "governance_note": (
                    "Repository failures, import failures, and runtime "
                    "wiring failures should be diagnosed independently."
                ),

                "completed_phase_protection": {
                    "does_not_modify_phase_logic":
                        True,

                    "does_not_modify_runtime_behavior":
                        True,

                    "does_not_modify_package_wiring":
                        True,
                },
            },
            suggested_fix=(
                None
                if status == "pass"
                else (
                    "Resolve canonical package root and PYTHONPATH "
                    "before diagnosing runtime wiring or recommendation execution."
                )
            ),
            governance_domain="architecture_contracts",
            contract_type="repository_import_runtime_separation",
        )

    def check_package_layout(self) -> None:
        #
        # ----------------------------------------------------------
        # Package Layout
        #
        # Repository structure audit only.
        #
        # This check verifies:
        #   package identity
        #   canonical package root
        #
        # This check does not verify dependency health.
        # ----------------------------------------------------------
        #

        expected_dirs = (
            self.discovered_packages.get(
                "expected",
                [],
            )
        )

        invalid_dirs = (
            self.discovered_packages.get(
                "invalid_aliases",
                [],
            )
        )

        other_dirs = (
            self.discovered_packages.get(
                "other_rhythm_like",
                [],
            )
        )

        self.add(
            domain="package_layout",
            check="package_directory_inventory",
            status="info",
            summary="Rhythm-related package directories inventoried.",
            evidence={
                "expected_package":
                    EXPECTED_PACKAGE,

                "expected_dirs":
                    expected_dirs,

                "invalid_alias_dirs":
                    invalid_dirs,

                "other_rhythm_like_dirs":
                    other_dirs,

                "audit_layer":
                    "package_inventory",

                "note": (
                    "Package inventory captures repository structure "
                    "evidence only."
                ),
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
                    "expected":
                        EXPECTED_PACKAGE,

                    "invalid_aliases":
                        INVALID_PACKAGE_ALIASES,

                    "invalid_alias_dirs":
                        invalid_dirs,

                    "identity_state":
                        "invalid_alias_detected",
                },
                suggested_fix=(
                    "Rename invalid package directory to "
                    "src/rhythm_ingestion or restore the "
                    "canonical package path."
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
                    "expected":
                        EXPECTED_PACKAGE,

                    "invalid_aliases":
                        INVALID_PACKAGE_ALIASES,

                    "identity_state":
                        "canonical_identity",
                },
                governance_domain="architecture_contracts",
                contract_type="package_identity",
            )

        canonical_src = (
            self.backend_root
            / "src"
        )

        canonical_pkg = (
            canonical_src
            / EXPECTED_PACKAGE
        )

        package_root_exists = (
            canonical_pkg.exists()
        )

        self.add(
            domain="package_layout",
            check="package_root_resolution",
            status=(
                "pass"
                if package_root_exists
                else "fail"
            ),
            summary=(
                "Canonical package root exists."
                if package_root_exists
                else (
                    "Canonical package root does not exist "
                    "at selected backend root."
                )
            ),
            evidence={
                "backend_root":
                    str(
                        self.backend_root
                    ),

                "expected_src":
                    str(
                        canonical_src
                    ),

                "expected_package_root":
                    str(
                        canonical_pkg
                    ),

                "exists":
                    package_root_exists,

                "audit_layer":
                    "package_root_resolution",
            },
            suggested_fix=(
                None
                if package_root_exists
                else (
                    "Ensure src/rhythm_ingestion exists under "
                    "the selected backend root."
                )
            ),
            governance_domain="architecture_contracts",
            contract_type="package_root_resolution",
        )


    def check_package_import_probe(self) -> None:
        #
        # ----------------------------------------------------------
        # Package Import Reality
        #
        # Package layout and dependency reality are different.
        #
        # Import failure:
        #   may be dependency-related
        #
        # Import failure:
        #   does not automatically imply package-root failure.
        # ----------------------------------------------------------
        #

        self.inject_pythonpath()

        probes = [
            "rhythm_ingestion",
            "rhythm_ingestion.api",
            "rhythm_ingestion.runtime_meta",
        ]

        results: Dict[str, Dict[str, Any]] = {}

        any_fail = False

        dependency_failures: List[str] = []
        package_failures: List[str] = []

        for module_name in probes:

            try:
                module = importlib.import_module(
                    module_name
                )

                results[module_name] = {
                    "status":
                        "pass",

                    "file":
                        getattr(
                            module,
                            "__file__",
                            None,
                        ),
                }

            except Exception as exc:

                any_fail = True

                failure_type = (
                    classify_import_failure(
                        str(exc),
                        self.discovered_packages,
                    )
                )

                if (
                    failure_type
                    == "dependency_missing"
                ):
                    dependency_failures.append(
                        module_name
                    )
                else:
                    package_failures.append(
                        module_name
                    )

                results[module_name] = {
                    "status":
                        "fail",

                    "error":
                        str(exc),

                    "root_cause":
                        failure_type,

                    "traceback":
                        traceback.format_exc(),
                }

        if (
            any_fail
            and dependency_failures
        ):
            suggested_fix = (
                "Install or expose missing runtime dependencies "
                "before treating this as a package-layout issue."
            )

        elif any_fail:

            suggested_fix = (
                "Verify package directory name and PYTHONPATH. "
                "Expected canonical package path: "
                "src/rhythm_ingestion."
            )

        else:
            suggested_fix = None

        self.add(
            domain="package_layout",
            check="package_import_probe",
            status=(
                "fail"
                if any_fail
                else "pass"
            ),
            summary=(
                "One or more package import probes failed."
                if any_fail
                else "Package import probes passed."
            ),
            evidence={
                "sys_path_prefix":
                    sys.path[:5],

                "results":
                    results,

                "dependency_failures":
                    dependency_failures,

                "package_failures":
                    package_failures,

                "audit_layer":
                    "import_reality",

                "dependency_note": (
                    "Dependency failures should remain separate "
                    "from package-root audit."
                ),
            },
            suggested_fix=suggested_fix,
            governance_domain="architecture_contracts",
            contract_type="import_reality",
        )


    def check_dependency_reality(self) -> None:
        #
        # ----------------------------------------------------------
        # Dependency Reality
        #
        # Dependency failures influence runtime readiness.
        #
        # Dependency failures should not automatically become
        # governance failures.
        # ----------------------------------------------------------
        #

        self.inject_pythonpath()

        required_results: Dict[str, Dict[str, Any]] = {}
        optional_results: Dict[str, Dict[str, Any]] = {}
        api_runtime_results: Dict[str, Dict[str, Any]] = {}

        required_missing: List[str] = []
        api_runtime_missing: List[str] = []

        for module_name in REQUIRED_RUNTIME_DEPENDENCY_MODULES:

            result = import_module_probe(
                module_name
            )

            required_results[
                module_name
            ] = result

            if result.get(
                "status"
            ) != "pass":
                required_missing.append(
                    module_name
                )

        for module_name in OPTIONAL_RUNTIME_DEPENDENCY_MODULES:

            optional_results[
                module_name
            ] = import_module_probe(
                module_name
            )

        for module_name in API_RUNTIME_DEPENDENCY_MODULES:

            result = import_module_probe(
                module_name
            )

            api_runtime_results[
                module_name
            ] = result

            if result.get(
                "status"
            ) != "pass":
                api_runtime_missing.append(
                    module_name
                )

        if required_missing:

            status = "fail"

            runtime_impact = (
                "blocked_by_dependency"
            )

            summary = (
                "One or more required runtime dependencies "
                "are missing."
            )

        elif api_runtime_missing:

            status = "warning"

            runtime_impact = (
                "capability_reduced"
            )

            summary = (
                "One or more API runtime dependencies "
                "are missing."
            )

        else:

            status = "pass"

            runtime_impact = "ready"

            summary = (
                "Required runtime dependencies are importable."
            )

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

                "audit_layer":
                    "dependency_reality",

                "dependency_classification": {
                    "required_missing":
                        "runtime_blocker",

                    "api_runtime_missing":
                        "capability_reduction",

                    "optional_missing":
                        "non_blocking",
                },

                "governance_note": (
                    "Dependency failures should influence runtime readiness "
                    "but should not automatically become governance failures."
                ),
            },
            suggested_fix=(
                None
                if status == "pass"
                else (
                    "Install missing runtime dependencies or adjust "
                    "CI/runtime setup before running runtime audit."
                )
            ),
            governance_domain="runtime_dependencies",
            contract_type="dependency_reality",
        )


    def check_repo_shape(self) -> None:
        #
        # ----------------------------------------------------------
        # Repository Shape
        #
        # Repository structure audit only.
        # ----------------------------------------------------------
        #

        expected = {
            "main.py":
                self.backend_root
                / "main.py",

            "src":
                self.backend_root
                / "src",

            "api_recommend.py":
                (
                    self.backend_root
                    / "src"
                    / EXPECTED_PACKAGE
                    / "api"
                    / "recommend.py"
                ),

            "api_app.py":
                (
                    self.backend_root
                    / "src"
                    / EXPECTED_PACKAGE
                    / "api"
                    / "app.py"
                ),

            "runtime_meta.py":
                (
                    self.backend_root
                    / "src"
                    / EXPECTED_PACKAGE
                    / "runtime_meta.py"
                ),

            "mcp_server.py":
                self.backend_root
                / "mcp_server.py",
        }

        for name, path in expected.items():

            exists = path.exists()

            self.add(
                domain="repo",
                check=f"exists_{name}",
                status=(
                    "pass"
                    if exists
                    else "warning"
                ),
                summary=(
                    f"{name} exists at selected backend root."
                    if exists
                    else (
                        f"{name} was not found at selected backend root."
                    )
                ),
                evidence={
                    "path":
                        str(path),

                    "exists":
                        exists,

                    "backend_root":
                        str(
                            self.backend_root
                        ),

                    "audit_layer":
                        "repository_shape",
                },
                governance_domain="architecture_contracts",
                contract_type="repository_shape",
            )


    def check_python_imports(self) -> None:
        #
        # ----------------------------------------------------------
        # Runtime Import Reality
        #
        # Runtime import audit only.
        #
        # Recommendation logic is not modified.
        # Wiring inspection only.
        # ----------------------------------------------------------
        #

        self.inject_pythonpath()

        try:
            recommend = importlib.import_module(
                "rhythm_ingestion.api.recommend"
            )

            router = getattr(
                recommend,
                "router",
                None,
            )

            games_rec = getattr(
                recommend,
                "_GAMES_RECOMMENDER",
                None,
            )

            orchestrator = getattr(
                recommend,
                "_ORCHESTRATOR",
                None,
            )

            self.add(
                domain="runtime_import",
                check="recommend_module_importable",
                status="pass",
                summary=(
                    "rhythm_ingestion.api.recommend imported successfully."
                ),
                evidence={
                    "module_file":
                        getattr(
                            recommend,
                            "__file__",
                            None,
                        ),

                    "router_type":
                        str(
                            type(
                                router
                            )
                        ),

                    "router_has_recommend_games":
                        hasattr(
                            router,
                            "recommend_games",
                        ),

                    "games_recommender_is_none":
                        games_rec is None,

                    "games_recommender_type":
                        str(
                            type(
                                games_rec
                            )
                        ),

                    "orchestrator_is_none":
                        orchestrator is None,

                    "orchestrator_type":
                        str(
                            type(
                                orchestrator
                            )
                        ),

                    "backend_root":
                        str(
                            self.backend_root
                        ),

                    "audit_layer":
                        "runtime_import_reality",

                    "phase_boundary_note": (
                        "Import audit does not modify "
                        "recommendation internals."
                    ),
                },
                governance_domain="architecture_contracts",
                contract_type="runtime_import_reality",
            )

            if games_rec is None:

                self.add(
                    domain="runtime_wiring",
                    check="games_recommender_present",
                    status="fail",
                    summary=(
                        "Games recommender is not injected into the runtime."
                    ),
                    evidence={
                        "_GAMES_RECOMMENDER":
                            None,

                        "expected_wiring":
                            (
                                "create_app(..., "
                                "games_recommender=...)"
                            ),

                        "audit_layer":
                            "runtime_wiring",

                        "boundary_note": (
                            "This verifies wiring only. "
                            "It does not modify recommendation internals."
                        ),
                    },
                    suggested_fix=(
                        "Inject a Phase 7 games_recommender via "
                        "create_app(..., games_recommender=...)."
                    ),
                    governance_domain="architecture_contracts",
                    contract_type="runtime_wiring",
                )

            else:

                self.add(
                    domain="runtime_wiring",
                    check="games_recommender_present",
                    status="pass",
                    summary=(
                        "Games recommender appears to be injected."
                    ),
                    evidence={
                        "games_recommender_type":
                            str(
                                type(
                                    games_rec
                                )
                            ),

                        "audit_layer":
                            "runtime_wiring",
                    },
                    governance_domain="architecture_contracts",
                    contract_type="runtime_wiring",
                )

        except Exception as exc:

            failure_type = (
                classify_import_failure(
                    str(exc),
                    self.discovered_packages,
                )
            )

            if (
                failure_type
                == "dependency_missing"
            ):
                suggested_fix = (
                    "Runtime module exists but a dependency is missing. "
                    "Resolve dependency reality before diagnosing wiring."
                )
            else:
                suggested_fix = (
                    "Verify package layout and PYTHONPATH. "
                    "Expected importable package path: "
                    "src/rhythm_ingestion."
                )

            self.add(
                domain="runtime_import",
                check="recommend_module_importable",
                status="fail",
                summary=(
                    "Failed to import rhythm_ingestion.api.recommend."
                ),
                evidence={
                    "error":
                        str(exc),

                    "root_cause":
                        failure_type,

                    "traceback":
                        traceback.format_exc(),

                    "audit_layer":
                        "runtime_import_reality",
                },
                suggested_fix=suggested_fix,
                governance_domain="architecture_contracts",
                contract_type="runtime_import_reality",
            )

    def check_runtime_meta_specs(self) -> None:
        #
        # ----------------------------------------------------------
        # Runtime Metadata Specs
        #
        # Runtime metadata is treated as an architecture contract
        # surface.
        #
        # This auditor inspects runtime_meta.py but must never
        # rewrite or mutate it.
        # ----------------------------------------------------------
        #

        self.inject_pythonpath()

        try:
            runtime_meta = importlib.import_module(
                "rhythm_ingestion.runtime_meta"
            )

            specs = getattr(
                runtime_meta,
                "ARTIFACT_SPECS",
                {},
            )

            required = [
                "song_recommendation_meta",
                "game_recommendation_meta",
                "recommendation_meta",
                "personalization_meta",
                "localization_meta",
            ]

            #
            # v1.0 artifact/runtime-adjacent expectations.
            #
            # These are audit-only expectations. Missing keys
            # are reported, but the auditor must not modify
            # runtime_meta.py automatically.
            #

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

                summary = (
                    "Some required runtime metadata artifact specs are missing."
                )

                metadata_state = "missing_required_specs"

            elif artifact_missing:
                status = "warning"

                summary = (
                    "Core runtime specs exist, but some artifact-adjacent specs are missing."
                )

                metadata_state = "missing_artifact_adjacent_specs"

            else:
                status = "pass"

                summary = (
                    "Required runtime metadata artifact specs are registered."
                )

                metadata_state = "registered"

            self.add(
                domain="runtime_meta",
                check="artifact_specs",
                status=status,
                summary=summary,
                evidence={
                    "required":
                        required,

                    "artifact_expected":
                        artifact_expected,

                    "missing":
                        missing,

                    "artifact_missing":
                        artifact_missing,

                    "registered": (
                        sorted(
                            list(
                                specs.keys()
                            )
                        )
                        if isinstance(
                            specs,
                            dict,
                        )
                        else []
                    ),

                    "metadata_state":
                        metadata_state,

                    "audit_layer":
                        "runtime_metadata_contract",

                    "boundary_note": (
                        "Runtime metadata is inspected as a contract surface. "
                        "The auditor must not rewrite runtime_meta.py."
                    ),

                    "completed_phase_protection": {
                        "does_not_modify_phase_logic":
                            True,

                        "does_not_modify_personalization_logic":
                            True,

                        "does_not_modify_localization_logic":
                            True,

                        "does_not_modify_recommendation_logic":
                            True,
                    },
                },
                suggested_fix=(
                    None
                    if status == "pass"
                    else (
                        "Add missing artifact keys to ARTIFACT_SPECS in runtime_meta.py "
                        "only if those keys are intended runtime artifacts."
                    )
                ),
                governance_domain="architecture_contracts",
                contract_type="runtime_metadata_contract",
            )

        except Exception as exc:
            failure_type = classify_import_failure(
                str(
                    exc
                ),
                self.discovered_packages,
            )

            self.add(
                domain="runtime_meta",
                check="artifact_specs",
                status="fail",
                summary="Could not inspect runtime_meta.ARTIFACT_SPECS.",
                evidence={
                    "error":
                        str(
                            exc
                        ),

                    "root_cause":
                        failure_type,

                    "traceback":
                        traceback.format_exc(),

                    "audit_layer":
                        "runtime_metadata_contract",

                    "governance_interpretation": (
                        "Import failures should be interpreted against dependency "
                        "reality before being treated as runtime metadata defects."
                    ),
                },
                suggested_fix=(
                    "Resolve dependency or import reality first, then re-run "
                    "runtime metadata audit."
                ),
                governance_domain="architecture_contracts",
                contract_type="runtime_metadata_contract",
            )


    def check_asset_scope_policy(self) -> None:
        #
        # ----------------------------------------------------------
        # Asset Scope Policy
        #
        # Repository files are not automatically chart assets.
        #
        # Asset scope is explicit so schemas, fixtures, registries,
        # generated artifacts, tooling, localization JSON, and phase
        # support files are not counted as chart assets by default.
        # ----------------------------------------------------------
        #

        scoped_type_a = (
            self.discovered_assets.get(
                "type_A",
                [],
            )
        )

        scoped_type_b = (
            self.discovered_assets.get(
                "type_B",
                [],
            )
        )

        excluded_total = int(
            self.discovered_assets.get(
                "excluded_candidate_count",
                0,
            )
        )

        excluded_by_reason = (
            self.discovered_assets.get(
                "excluded_by_reason",
                {},
            )
        )

        excluded_examples = (
            self.discovered_assets.get(
                "excluded_examples",
                {},
            )
        )

        scoped_total = (
            len(
                scoped_type_a
            )
            + len(
                scoped_type_b
            )
        )

        if scoped_total > 0:
            status = "pass"

            summary = (
                "Asset scope policy identified scoped asset candidates."
            )

            scope_state = "scoped_assets_found"

        elif excluded_total > 0:
            #
            # v1.0 refinement:
            #
            # If all asset-like files are excluded by explicit policy,
            # this is informational evidence, not automatically a
            # warning.
            #

            status = "info"

            summary = (
                "Asset-like files were found, but all were excluded by "
                "explicit asset scope policy."
            )

            scope_state = "all_candidates_excluded_by_policy"

        else:
            status = "info"

            summary = (
                "No scoped asset candidates were discovered."
            )

            scope_state = "no_asset_candidates_discovered"

        self.add(
            domain="asset_scope_policy",
            check="scoped_asset_inventory",
            status=status,
            summary=summary,
            evidence={
                "strategy":
                    "explicit_scope_with_exclusions",

                "scope_state":
                    scope_state,

                "type_A_scoped_count":
                    len(
                        scoped_type_a
                    ),

                "type_B_scoped_count":
                    len(
                        scoped_type_b
                    ),

                "scoped_total":
                    scoped_total,

                "excluded_candidate_count":
                    excluded_total,

                #
                # Keep scoped files because they are the positive
                # evidence most useful for review.
                #

                "type_A_scoped_files":
                    scoped_type_a,

                "type_B_scoped_files":
                    scoped_type_b,

                #
                # Evidence-volume refinement:
                #
                # Do not dump every excluded candidate into the report.
                # Summarize by reason and include examples instead.
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
                    "full_excluded_candidate_dump":
                        False,

                    "examples_per_reason":
                        10,

                    "reason_summary_required":
                        True,
                },

                "coverage_interpretation": (
                    "No scoped assets means insufficient coverage evidence, "
                    "not 100% coverage."
                ),

                "note": (
                    "Repository files are not automatically chart assets. "
                    "v1.0 keeps asset scope explicit so schema, config, "
                    "fixture, registry, generated artifact, tooling, and "
                    "localization JSON files are not treated as chart assets "
                    "by default."
                ),

                "completed_phase_protection": {
                    "does_not_modify_phase_logic":
                        True,

                    "does_not_modify_canonical_ingestion":
                        True,

                    "does_not_modify_personalization_or_localization":
                        True,

                    "does_not_modify_asset_pipeline":
                        True,
                },
            },
            suggested_fix=(
                None
                if (
                    scoped_total > 0
                    or excluded_total > 0
                )
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
        #
        # ----------------------------------------------------------
        # Artifact Database Policy
        #
        # This is a root artifact-backbone contract.
        #
        # Required backbone:
        #
        #   file_scan_inventory.db
        #       -> chart_assets.db
        #       -> chart_patterns.db
        #
        # This check is strictly read-only.
        # ----------------------------------------------------------
        #

        snapshots_by_db = (
            self.get_all_artifact_db_snapshots()
        )

        candidates_by_db = (
            self.resolve_all_artifact_db_candidates()
        )

        db_status: Dict[str, Dict[str, Any]] = {}

        missing: List[str] = []
        unreadable: List[str] = []
        empty: List[str] = []

        for db_name in ARTIFACT_DATABASE_NAMES:
            candidates = (
                candidates_by_db.get(
                    db_name,
                    [],
                )
            )

            snapshots = (
                snapshots_by_db.get(
                    db_name,
                    [],
                )
            )

            exists_count = len(
                [
                    snapshot
                    for snapshot in snapshots
                    if snapshot.get(
                        "exists"
                    )
                ]
            )

            readable_count = len(
                [
                    snapshot
                    for snapshot in snapshots
                    if snapshot.get(
                        "exists"
                    )
                    and snapshot.get(
                        "readable"
                    )
                    and not snapshot.get(
                        "error"
                    )
                ]
            )

            row_count_total = 0

            for snapshot in snapshots:
                for count in snapshot.get(
                    "table_row_counts",
                    {},
                ).values():
                    if isinstance(
                        count,
                        int,
                    ):
                        row_count_total += count

            if not candidates:
                missing.append(
                    db_name
                )

            elif readable_count == 0:
                unreadable.append(
                    db_name
                )

            elif row_count_total == 0:
                empty.append(
                    db_name
                )

            db_status[
                db_name
            ] = {
                "logical_name":
                    ARTIFACT_DATABASE_LOGICAL_NAMES.get(
                        db_name,
                        db_name,
                    ),

                "candidate_count":
                    len(
                        candidates
                    ),

                "candidates": [
                    str(
                        path
                    )
                    for path in candidates
                ],

                "exists_count":
                    exists_count,

                "readable_count":
                    readable_count,

                "row_count_total":
                    row_count_total,

                "state": (
                    "missing"
                    if not candidates
                    else (
                        "unreadable"
                        if readable_count == 0
                        else (
                            "empty"
                            if row_count_total == 0
                            else "ready"
                        )
                    )
                ),

                "snapshots":
                    snapshots,
            }

        if missing:
            status = "fail"

            summary = (
                "One or more required artifact databases are missing."
            )

            database_policy_state = "missing_required_databases"

        elif unreadable:
            status = "fail"

            summary = (
                "One or more artifact databases were found but are not readable."
            )

            database_policy_state = "unreadable_required_databases"

        elif empty:
            status = "warning"

            summary = (
                "All required artifact databases are present/readable, "
                "but one or more appear empty."
            )

            database_policy_state = "empty_required_databases"

        else:
            status = "pass"

            summary = (
                "Required artifact databases are present, readable, and contain rows."
            )

            database_policy_state = "ready"

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

                "database_policy_state":
                    database_policy_state,

                "missing":
                    missing,

                "unreadable":
                    unreadable,

                "empty":
                    empty,

                "database_status":
                    db_status,

                #
                # audit policy
                #

                "role":
                    "root_contract",

                "read_mode":
                    "sqlite_readonly",

                "allowed_operations": [
                    "schema_inventory",
                    "readability_check",
                    "record_count",
                    "relationship_audit",
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

                "impact_scope": {
                    "directly_blocks": [
                        "artifact_relationships",
                        "artifact_backbone_contract",
                        "asset_coverage",
                        "hash_integrity",
                        "type_A_usability",
                        "runtime_artifact_readiness",
                    ],

                    "impact_domain":
                        "artifact_backbone",
                },

                #
                # Notes
                #

                "policy_note": (
                    "This check acts as a root artifact-backbone contract. "
                    "Missing, unreadable, or empty artifact databases may "
                    "cause derived failures in downstream artifact audit "
                    "domains."
                ),

                "governance_note": (
                    "Artifact database failures should be rendered as root "
                    "failures. Downstream contract failures should be marked "
                    "as derived whenever caused by missing backbone databases."
                ),

                "completed_phase_protection": {
                    "does_not_modify_phase_logic":
                        True,

                    "does_not_modify_canonical_ingestion":
                        True,

                    "does_not_mutate_artifact_databases":
                        True,
                },
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
        #
        # ----------------------------------------------------------
        # Artifact Relationships
        #
        # Verifies the artifact relationship chain:
        #
        #   file_scan_inventory.db
        #       -> chart_assets.db
        #       -> chart_patterns.db
        #
        # This is read-only relationship audit.
        # No DB rows or repository files are modified.
        # ----------------------------------------------------------
        #

        scan_records = (
            self.iter_file_scan_inventory_records()
        )

        asset_records = (
            self.iter_asset_db_records()
        )

        pattern_records = (
            self.iter_chart_pattern_records()
        )

        scan_paths = {
            normalize_path_text(
                record.get(
                    "path"
                )
            )
            for record in scan_records
            if normalize_path_text(
                record.get(
                    "path"
                )
            )
        }

        asset_paths = {
            normalize_path_text(
                record.get(
                    "path"
                )
            )
            for record in asset_records
            if normalize_path_text(
                record.get(
                    "path"
                )
            )
        }

        pattern_paths = {
            normalize_path_text(
                record.get(
                    "path"
                )
            )
            for record in pattern_records
            if normalize_path_text(
                record.get(
                    "path"
                )
            )
        }

        asset_chart_ids = {
            str(
                record.get(
                    "chart_id"
                )
                or ""
            ).strip()
            for record in asset_records
            if str(
                record.get(
                    "chart_id"
                )
                or ""
            ).strip()
        }

        pattern_chart_ids = {
            str(
                record.get(
                    "chart_id"
                )
                or ""
            ).strip()
            for record in pattern_records
            if str(
                record.get(
                    "chart_id"
                )
                or ""
            ).strip()
        }

        #
        # ----------------------------------------------------------
        # Scan -> Asset relationship by path/name
        # ----------------------------------------------------------
        #

        scan_to_asset_matches: Set[str] = set()
        orphan_scans: List[str] = []

        for scan_path in sorted(
            scan_paths
        ):
            matched = False

            for asset_path in asset_paths:
                if (
                    scan_path == asset_path
                    or scan_path.endswith(
                        asset_path
                    )
                    or asset_path.endswith(
                        Path(
                            scan_path
                        ).name
                    )
                ):
                    matched = True

                    scan_to_asset_matches.add(
                        asset_path
                    )

                    break

            if not matched:
                orphan_scans.append(
                    scan_path
                )

        orphan_assets_from_scan = sorted(
            [
                path
                for path in asset_paths
                if path not in scan_to_asset_matches
            ]
        )

        #
        # ----------------------------------------------------------
        # Asset -> Pattern relationship by path/name
        # ----------------------------------------------------------
        #

        asset_to_pattern_path_matches: Set[str] = set()
        orphan_assets_without_patterns: List[str] = []

        for asset_path in sorted(
            asset_paths
        ):
            matched = False

            for pattern_path in pattern_paths:
                if (
                    asset_path == pattern_path
                    or asset_path.endswith(
                        pattern_path
                    )
                    or pattern_path.endswith(
                        Path(
                            asset_path
                        ).name
                    )
                ):
                    matched = True

                    asset_to_pattern_path_matches.add(
                        pattern_path
                    )

                    break

            if not matched:
                orphan_assets_without_patterns.append(
                    asset_path
                )

        orphan_patterns_by_path = sorted(
            [
                path
                for path in pattern_paths
                if path not in asset_to_pattern_path_matches
            ]
        )

        #
        # ----------------------------------------------------------
        # Asset -> Pattern relationship by chart_id
        # ----------------------------------------------------------
        #

        asset_to_pattern_id_matches = (
            asset_chart_ids.intersection(
                pattern_chart_ids
            )
        )

        orphan_asset_chart_ids = sorted(
            [
                item
                for item in asset_chart_ids
                if item not in pattern_chart_ids
            ]
        )

        orphan_pattern_chart_ids = sorted(
            [
                item
                for item in pattern_chart_ids
                if item not in asset_chart_ids
            ]
        )

        #
        # ----------------------------------------------------------
        # Coverage calculations
        #
        # Important:
        #   0 / 0 is insufficient evidence, not 100%.
        # ----------------------------------------------------------
        #

        scan_count = len(
            scan_paths
        )

        if scan_count == 0:
            scan_to_asset_coverage = None
            scan_to_asset_state = (
                "insufficient_evidence"
            )

        else:
            scan_to_asset_coverage = round(
                (
                    (
                        scan_count
                        - len(
                            orphan_scans
                        )
                    )
                    / scan_count
                )
                * 100,
                2,
            )

            scan_to_asset_state = (
                "complete"
                if scan_to_asset_coverage == 100.0
                else "incomplete"
            )

        asset_path_count = len(
            asset_paths
        )

        if asset_path_count == 0:
            asset_to_pattern_coverage_by_path = None
            asset_to_pattern_path_state = (
                "insufficient_evidence"
            )

        else:
            asset_to_pattern_coverage_by_path = round(
                (
                    (
                        asset_path_count
                        - len(
                            orphan_assets_without_patterns
                        )
                    )
                    / asset_path_count
                )
                * 100,
                2,
            )

            asset_to_pattern_path_state = (
                "complete"
                if asset_to_pattern_coverage_by_path == 100.0
                else "incomplete"
            )

        asset_id_count = len(
            asset_chart_ids
        )

        id_relationship_available = bool(
            asset_chart_ids
            or pattern_chart_ids
        )

        if asset_id_count == 0:
            asset_to_pattern_coverage_by_id = None
            asset_to_pattern_id_state = (
                "insufficient_evidence"
            )

        else:
            asset_to_pattern_coverage_by_id = round(
                (
                    len(
                        asset_to_pattern_id_matches
                    )
                    / asset_id_count
                )
                * 100,
                2,
            )

            asset_to_pattern_id_state = (
                "complete"
                if asset_to_pattern_coverage_by_id == 100.0
                else "incomplete"
            )

        #
        # ----------------------------------------------------------
        # DB readiness
        # ----------------------------------------------------------
        #

        scan_db_ready = (
            self.artifact_db_has_readable_rows(
                FILE_SCAN_INVENTORY_DB_NAME
            )
        )

        asset_db_ready = (
            self.artifact_db_has_readable_rows(
                CHART_ASSETS_DB_NAME
            )
        )

        pattern_db_ready = (
            self.artifact_db_has_readable_rows(
                CHART_PATTERNS_DB_NAME
            )
        )

        path_relationship_ready = (
            scan_to_asset_state == "complete"
            and asset_to_pattern_path_state == "complete"
        )

        id_relationship_ready = (
            id_relationship_available
            and asset_to_pattern_id_state == "complete"
            and not orphan_asset_chart_ids
            and not orphan_pattern_chart_ids
        )

        pattern_relationship_ready = (
            asset_to_pattern_path_state == "complete"
            or id_relationship_ready
        )

        pass_condition = (
            scan_db_ready
            and asset_db_ready
            and pattern_db_ready
            and scan_to_asset_state == "complete"
            and pattern_relationship_ready
            and not orphan_scans
            and not orphan_assets_from_scan
        )

        relationship_state = (
            "complete"
            if pass_condition
            else (
                "insufficient_evidence"
                if (
                    scan_to_asset_state == "insufficient_evidence"
                    or asset_to_pattern_path_state == "insufficient_evidence"
                )
                else "incomplete"
            )
        )

        if pass_condition:
            status = "pass"
            summary = (
                "Artifact relationship chain is complete."
            )

        else:
            status = "fail"
            summary = (
                "Artifact relationship chain has missing links, "
                "orphan records, or insufficient evidence."
            )

        self.add(
            domain="artifact_relationships",
            check="artifact_relationship_chain",
            status=status,
            summary=summary,
            evidence={
                "relationship_chain":
                    ARTIFACT_RELATIONSHIP_CHAIN,

                "relationship_state":
                    relationship_state,

                "scan_db_ready":
                    scan_db_ready,

                "asset_db_ready":
                    asset_db_ready,

                "pattern_db_ready":
                    pattern_db_ready,

                "scan_record_count":
                    len(
                        scan_records
                    ),

                "asset_record_count":
                    len(
                        asset_records
                    ),

                "pattern_record_count":
                    len(
                        pattern_records
                    ),

                "scan_path_count":
                    len(
                        scan_paths
                    ),

                "asset_path_count":
                    len(
                        asset_paths
                    ),

                "pattern_path_count":
                    len(
                        pattern_paths
                    ),

                "scan_to_asset_coverage":
                    scan_to_asset_coverage,

                "scan_to_asset_state":
                    scan_to_asset_state,

                "asset_to_pattern_coverage_by_path":
                    asset_to_pattern_coverage_by_path,

                "asset_to_pattern_path_state":
                    asset_to_pattern_path_state,

                "asset_chart_id_count":
                    len(
                        asset_chart_ids
                    ),

                "pattern_chart_id_count":
                    len(
                        pattern_chart_ids
                    ),

                "asset_to_pattern_id_match_count":
                    len(
                        asset_to_pattern_id_matches
                    ),

                "asset_to_pattern_coverage_by_id":
                    asset_to_pattern_coverage_by_id,

                "asset_to_pattern_id_state":
                    asset_to_pattern_id_state,

                "id_relationship_available":
                    id_relationship_available,

                "path_relationship_ready":
                    path_relationship_ready,

                "id_relationship_ready":
                    id_relationship_ready,

                "pattern_relationship_ready":
                    pattern_relationship_ready,

                "orphan_scans":
                    orphan_scans,

                "orphan_assets_from_scan":
                    orphan_assets_from_scan,

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

                "matching_strategy": (
                    "path/name suffix heuristic plus chart_id "
                    "comparison where available"
                ),

                "zero_denominator_policy": (
                    "0/0 relationship coverage is reported as "
                    "insufficient_evidence, not 100%."
                ),

                "completed_phase_protection": {
                    "does_not_modify_phase_logic":
                        True,

                    "does_not_modify_canonical_ingestion":
                        True,

                    "does_not_modify_asset_pipeline":
                        True,
                },
            },
            suggested_fix=(
                None
                if pass_condition
                else (
                    "Ensure scan results persist to file_scan_inventory.db, "
                    "assets persist to chart_assets.db, and pattern extraction "
                    "persists to chart_patterns.db using stable path, hash, "
                    "or chart_id links."
                )
            ),
            governance_domain="artifact_backbone",
            contract_type="artifact_relationships",
        )


    def check_asset_pipeline(self) -> None:
        #
        # ----------------------------------------------------------
        # Asset Pipeline Inventory
        #
        # This check captures scoped asset inventory evidence.
        #
        # It is non-destructive and does not modify the Phase 3
        # canonical ingestion pipeline.
        # ----------------------------------------------------------
        #

        type_a = (
            self.discovered_assets.get(
                "type_A",
                [],
            )
        )

        type_b = (
            self.discovered_assets.get(
                "type_B",
                [],
            )
        )

        excluded_total = int(
            self.discovered_assets.get(
                "excluded_candidate_count",
                0,
            )
        )

        excluded_by_reason = (
            self.discovered_assets.get(
                "excluded_by_reason",
                {},
            )
        )

        excluded_examples = (
            self.discovered_assets.get(
                "excluded_examples",
                {},
            )
        )

        db_candidates = (
            self.resolve_asset_db_candidates()
        )

        all_db_candidates = (
            self.resolve_all_artifact_db_candidates()
        )

        max_file_examples = 50

        self.add(
            domain="asset_pipeline",
            check="asset_inventory",
            status="info",
            summary=(
                "Scoped chart asset inventory captured without modifying asset state."
            ),
            evidence={
                "type_A_count":
                    len(
                        type_a
                    ),

                "type_B_count":
                    len(
                        type_b
                    ),

                "excluded_candidate_count":
                    excluded_total,

                "type_A_files_sample":
                    type_a[
                        :max_file_examples
                    ],

                "type_A_files_truncated":
                    len(
                        type_a
                    )
                    > max_file_examples,

                "type_B_files_sample":
                    type_b[
                        :max_file_examples
                    ],

                "type_B_files_truncated":
                    len(
                        type_b
                    )
                    > max_file_examples,

                "excluded_by_reason":
                    excluded_by_reason,

                "excluded_examples":
                    excluded_examples,

                "chart_assets_db_candidates": [
                    str(
                        path
                    )
                    for path in db_candidates
                ],

                "artifact_database_candidates": {
                    db_name: [
                        str(
                            path
                        )
                        for path in paths
                    ]
                    for db_name, paths in all_db_candidates.items()
                },

                "type_A_extensions":
                    sorted(
                        TYPE_A_EXTENSIONS
                    ),

                "type_B_extensions":
                    sorted(
                        TYPE_B_EXTENSIONS
                    ),

                "scope_policy": {
                    "include_root_hints":
                        ASSET_SCOPE_INCLUDE_ROOT_HINTS,

                    "exclude_root_hints":
                        ASSET_SCOPE_EXCLUDE_ROOT_HINTS,

                    "excluded_candidate_dump":
                        "summarized",
                },

                "pipeline_role":
                    "additive_asset_pipeline",

                "completed_phase_protection": {
                    "does_not_modify_phase_3_canonical_pipeline":
                        True,

                    "does_not_modify_canonical_row":
                        True,

                    "does_not_modify_completed_phases":
                        True,
                },

                "note": (
                    "Asset inventory is summarized to keep the auditor "
                    "report readable. Full repository inventory remains "
                    "available from workflow artifacts when needed."
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
                        str(
                            self.repo_root
                        ),

                    "artifact_database_candidates": {
                        db_name: [
                            str(
                                path
                            )
                            for path in paths
                        ]
                        for db_name, paths in all_db_candidates.items()
                    },

                    "dependency_note": (
                        "Missing chart_assets.db may cause downstream asset "
                        "coverage, hash audit, Type A usability, and "
                        "runtime DB readiness checks to fail as derived issues."
                    ),

                    "upstream_root_contract":
                        "artifact_database_policy",
                },
                suggested_fix=(
                    "Create or provide chart_assets.db after asset pipeline "
                    "persistence is available."
                ),
                governance_domain="artifact_backbone",
                contract_type="asset_pipeline_persistence",
            )
            return

        db_evidence = (
            self.get_asset_db_snapshots()
        )

        sqlite_errors = [
            item
            for item in db_evidence
            if item.get(
                "error"
            )
        ]

        nonempty_tables = [
            item
            for item in db_evidence
            if any(
                (
                    count
                    or 0
                )
                > 0
                for count in item.get(
                    "table_row_counts",
                    {},
                ).values()
                if isinstance(
                    count,
                    int,
                )
            )
        ]

        self.add(
            domain="asset_pipeline",
            check="chart_assets_db_readable",
            status=(
                "fail"
                if sqlite_errors
                else "pass"
            ),
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

                "sqlite_error_count":
                    len(
                        sqlite_errors
                    ),

                "audit_layer":
                    "asset_pipeline_persistence",
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
            status=(
                "pass"
                if nonempty_tables
                else "warning"
            ),
            summary=(
                "At least one discovered chart_assets.db table contains rows."
                if nonempty_tables
                else "No non-empty chart_assets.db table was confirmed."
            ),
            evidence={
                "nonempty_database_count":
                    len(
                        nonempty_tables
                    ),

                "database_count":
                    len(
                        db_evidence
                    ),

                "population_state": (
                    "populated"
                    if nonempty_tables
                    else "empty_or_unconfirmed"
                ),

                "dependency_note": (
                    "Empty chart asset databases may cause downstream "
                    "coverage and runtime readiness checks to remain blocked "
                    "or review-needed."
                ),

                "audit_layer":
                    "asset_pipeline_population",
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
        #
        # ----------------------------------------------------------
        # Asset Coverage
        #
        # Coverage compares scoped repository assets against
        # chart_assets.db records.
        #
        # No repository mutation occurs here.
        # ----------------------------------------------------------
        #

        repository_assets = [
            str(
                Path(
                    item
                ).resolve()
            )
            for item in self.discovered_assets.get(
                "type_A",
                [],
            )
        ]

        repository_assets += [
            str(
                Path(
                    item
                ).resolve()
            )
            for item in self.discovered_assets.get(
                "type_B",
                [],
            )
        ]

        repository_assets_set = set(
            repository_assets
        )

        records = self.iter_asset_db_records()

        db_paths = {
            normalize_path_text(
                record.get(
                    "path"
                )
            )
            for record in records
            if normalize_path_text(
                record.get(
                    "path"
                )
            )
        }

        db_path_matches: Set[str] = set()
        orphan_files: List[str] = []

        for asset in sorted(
            repository_assets_set
        ):
            normalized_asset = normalize_path_text(
                asset
            )

            matched = False

            for db_path in db_paths:
                if db_path and (
                    db_path == normalized_asset
                    or normalized_asset.endswith(
                        db_path
                    )
                    or db_path.endswith(
                        Path(
                            asset
                        ).name
                    )
                ):
                    matched = True

                    db_path_matches.add(
                        db_path
                    )

                    break

            if not matched:
                orphan_files.append(
                    asset
                )

        orphan_db_entries = sorted(
            [
                path
                for path in db_paths
                if path not in db_path_matches
            ]
        )

        repository_asset_count = len(
            repository_assets_set
        )

        db_asset_path_count = len(
            db_paths
        )

        if repository_asset_count == 0:
            coverage_percentage = None

            coverage_state = (
                "insufficient_evidence"
            )

        else:
            coverage_percentage = round(
                (
                    (
                        repository_asset_count
                        - len(
                            orphan_files
                        )
                    )
                    / repository_asset_count
                )
                * 100,
                2,
            )

            coverage_state = (
                "complete"
                if (
                    coverage_percentage == 100.0
                    and not orphan_db_entries
                )
                else "incomplete"
            )

        pass_condition = (
            repository_asset_count > 0
            and coverage_percentage == 100.0
            and not orphan_db_entries
        )

        self.add(
            domain="asset_coverage",
            check="repository_db_asset_coverage",
            status=(
                "pass"
                if pass_condition
                else "fail"
            ),
            summary=(
                "Scoped repository asset coverage matches chart_assets.db records."
                if pass_condition
                else (
                    "Scoped repository asset coverage has gaps, unmatched DB entries, "
                    "or insufficient repository asset evidence."
                )
            ),
            evidence={
                "repository_asset_count":
                    repository_asset_count,

                "db_asset_path_count":
                    db_asset_path_count,

                "coverage_percentage":
                    coverage_percentage,

                "coverage_state":
                    coverage_state,

                "orphan_file_count":
                    len(
                        orphan_files
                    ),

                "orphan_db_entry_count":
                    len(
                        orphan_db_entries
                    ),

                "orphan_files":
                    orphan_files,

                "orphan_db_entries":
                    orphan_db_entries,

                "audit_layer":
                    "coverage",

                "matching_strategy":
                    "path/name suffix heuristic",

                "scope_note": (
                    "Coverage operates on scoped assets only. "
                    "If no scoped repository assets are discovered, "
                    "coverage is insufficient evidence rather than 100%."
                ),

                "completed_phase_protection": {
                    "does_not_modify_phase_logic":
                        True,

                    "does_not_modify_canonical_ingestion":
                        True,

                    "does_not_modify_asset_pipeline":
                        True,
                },
            },
            suggested_fix=(
                None
                if pass_condition
                else (
                    "Persist all scoped assets to chart_assets.db, "
                    "verify asset scope discovery, and resolve orphan DB records."
                )
            ),
            governance_domain="artifact_backbone",
            contract_type="asset_coverage",
        )


    def check_artifact_backbone_contract(self) -> None:
        #
        # ----------------------------------------------------------
        # Artifact Backbone Contract
        #
        # This is a governance-relevant root contract.
        #
        # file_scan_inventory.db
        #   -> chart_assets.db
        #   -> chart_patterns.db
        #
        # The contract is read-only and does not mutate artifact DBs.
        # ----------------------------------------------------------
        #

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
            status=(
                "pass"
                if pass_condition
                else "fail"
            ),
            summary=(
                "Artifact backbone contract satisfied."
                if pass_condition
                else "Artifact backbone contract not satisfied."
            ),
            evidence={
                "required_databases":
                    ARTIFACT_DATABASE_NAMES,

                "required_relationships": [
                    "scan_to_asset",
                    "asset_to_pattern",
                ],

                "required_capabilities": [
                    "runtime_asset_resolution",
                    "runtime_pattern_resolution",
                    "runtime_recommendation_support",
                ],

                "readiness":
                    readiness,

                "root_contract":
                    True,

                "derived_contracts_when_missing": [
                    "artifact_relationships",
                    "asset_coverage",
                    "hash_integrity",
                    "type_A_usability",
                    "runtime_artifact_readiness",
                ],

                "audit_layer":
                    "artifact_backbone_contract",

                "read_mode":
                    "read_only",

                "governance_note": (
                    "Artifact backbone failure should be treated as a root "
                    "governance failure. Downstream artifact checks should be "
                    "revalidated after this contract is restored."
                ),
            },
            suggested_fix=(
                None
                if pass_condition
                else (
                    "Restore missing database, relationship, or runtime "
                    "artifact capability before treating downstream artifact "
                    "audit failures as independently actionable."
                )
            ),
            governance_domain="artifact_backbone",
            contract_type="artifact_backbone_contract",
        )


    def check_hash_audit(self) -> None:
        #
        # ----------------------------------------------------------
        # Hash audit
        #
        # Hash audit compares scoped repository asset hashes
        # against persisted chart_assets.db hash evidence.
        #
        # No repository or DB mutation occurs here.
        # ----------------------------------------------------------
        #

        repository_hashes = (
            self.compute_repository_asset_hashes()
        )

        records = self.iter_asset_db_records()

        db_hashes: Dict[str, List[Dict[str, Any]]] = {}

        for record in records:
            hash_value = str(
                record.get(
                    "hash"
                )
                or ""
            ).strip()

            if not hash_value:
                continue

            db_hashes.setdefault(
                hash_value,
                [],
            ).append(
                record
            )

        duplicate_hashes = {
            hash_value:
                len(
                    rows
                )
            for hash_value, rows in db_hashes.items()
            if len(
                rows
            )
            > 1
        }

        file_hash_set = set(
            repository_hashes.values()
        )

        db_hash_set = set(
            db_hashes.keys()
        )

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
            file_hash_set.intersection(
                db_hash_set
            )
        )

        repository_hash_count = len(
            repository_hashes
        )

        db_hash_count = len(
            db_hash_set
        )

        if repository_hash_count == 0:
            hash_state = (
                "insufficient_evidence"
            )

        elif (
            not missing_hash_files
            and not orphan_db_hashes
            and not duplicate_hashes
        ):
            hash_state = (
                "consistent"
            )

        else:
            hash_state = (
                "inconsistent"
            )

        pass_condition = (
            repository_hash_count > 0
            and hash_state == "consistent"
        )

        self.add(
            domain="hash_audit",
            check="repository_db_hash_consistency",
            status=(
                "pass"
                if pass_condition
                else "fail"
            ),
            summary=(
                "Scoped repository asset hashes are consistent with chart_assets.db."
                if pass_condition
                else (
                    "Hash audit found missing, orphan, duplicate, "
                    "or insufficient hash evidence."
                )
            ),
            evidence={
                "repository_hash_count":
                    repository_hash_count,

                "db_hash_count":
                    db_hash_count,

                "matched_hash_count":
                    matched_hash_count,

                "missing_hash_file_count":
                    len(
                        missing_hash_files
                    ),

                "orphan_db_hash_count":
                    len(
                        orphan_db_hashes
                    ),

                "duplicate_hash_count":
                    len(
                        duplicate_hashes
                    ),

                "missing_hash_files":
                    missing_hash_files,

                "orphan_db_hashes":
                    orphan_db_hashes,

                "duplicate_hashes":
                    duplicate_hashes,

                "hash_state":
                    hash_state,

                "audit_layer":
                    "hash_integrity",

                "scope_note": (
                    "v1.0 hashes scoped asset candidates rather than all "
                    "repository files. Zero scoped hashes is insufficient "
                    "evidence, not a successful hash audit."
                ),

                "completed_phase_protection": {
                    "does_not_modify_phase_logic":
                        True,

                    "does_not_modify_canonical_ingestion":
                        True,

                    "does_not_modify_asset_pipeline":
                        True,
                },
            },
            suggested_fix=(
                None
                if pass_condition
                else (
                    "Store SHA-256 hashes for persisted scoped assets and "
                    "resolve missing, orphan, or duplicate hash records."
                )
            ),
            governance_domain="artifact_backbone",
            contract_type="hash_integrity",
        )


    def check_type_A_usability(self) -> None:
        #
        # ----------------------------------------------------------
        # Type A Usability
        #
        # Type A assets are deterministic assets expected to have
        # usable text representations.
        #
        # This check verifies text readiness only.
        # It does not validate gameplay interpretation quality.
        # ----------------------------------------------------------
        #

        records = self.iter_asset_db_records()

        type_a_records: List[Dict[str, Any]] = []

        for record in records:
            explicit_type = str(
                record.get(
                    "asset_type"
                )
                or ""
            ).lower()

            path_text = normalize_path_text(
                record.get(
                    "path"
                )
            )

            suffix_type = (
                classify_asset_path(
                    Path(
                        path_text
                    )
                )
                if path_text
                else "unknown"
            )

            if (
                explicit_type
                in {
                    "type_a",
                    "type-a",
                    "a",
                    "deterministic",
                }
                or suffix_type == "type_A"
            ):
                type_a_records.append(
                    record
                )

        unusable: List[Dict[str, Any]] = []
        usable_count = 0

        for record in type_a_records:
            text = record.get(
                "text"
            )

            text_value = str(
                text
                or ""
            )

            stripped_text = text_value.strip()

            usable = (
                bool(
                    stripped_text
                )
                and len(
                    stripped_text
                )
                >= MIN_TYPE_A_TEXT_LENGTH
            )

            if usable:
                usable_count += 1

            else:
                unusable.append(
                    {
                        "db_path":
                            record.get(
                                "db_path"
                            ),

                        "table":
                            record.get(
                                "table"
                            ),

                        "path":
                            record.get(
                                "path"
                            ),

                        "text_length":
                            len(
                                stripped_text
                            ),
                    }
                )

        type_a_record_count = len(
            type_a_records
        )

        unusable_count = len(
            unusable
        )

        if type_a_record_count == 0:
            usability_state = (
                "insufficient_evidence"
            )

        elif unusable_count == 0:
            usability_state = (
                "usable"
            )

        else:
            usability_state = (
                "incomplete"
            )

        pass_condition = (
            type_a_record_count > 0
            and usability_state == "usable"
        )

        self.add(
            domain="type_A_usability",
            check="text_representation_usability",
            status=(
                "pass"
                if pass_condition
                else "fail"
            ),
            summary=(
                "Type A assets have usable text representations."
                if pass_condition
                else (
                    "One or more Type A assets lack usable text representations, "
                    "or no Type A DB records were available."
                )
            ),
            evidence={
                "type_A_record_count":
                    type_a_record_count,

                "usable_count":
                    usable_count,

                "unusable_count":
                    unusable_count,

                "minimum_text_length":
                    MIN_TYPE_A_TEXT_LENGTH,

                "unusable_records":
                    unusable,

                "usability_state":
                    usability_state,

                "audit_layer":
                    "type_A_runtime_usability",

                "type_A_contract": {
                    "expected": [
                        "text_representation",
                        "converter_success",
                        "usable_content",
                        "usability_verified",
                    ],
                },

                "scope_note": (
                    "Type A usability verifies deterministic text readiness "
                    "only. It does not evaluate semantic interpretation or "
                    "gameplay coaching quality."
                ),

                "completed_phase_protection": {
                    "does_not_modify_phase_logic":
                        True,

                    "does_not_modify_canonical_ingestion":
                        True,

                    "does_not_modify_tips_generation":
                        True,

                    "does_not_modify_personalization_or_localization":
                        True,
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
        #
        # ----------------------------------------------------------
        # Type B Intelligence
        #
        # Type B assets are reference-only assets.
        #
        # This check verifies whether Type B records contain usable
        # reference evidence. It does not attempt semantic
        # interpretation of the reference content.
        # ----------------------------------------------------------
        #

        type_b_files = (
            self.discovered_assets.get(
                "type_B",
                [],
            )
        )

        records = self.iter_asset_db_records()

        type_b_records: List[Dict[str, Any]] = []

        for record in records:
            explicit_type = str(
                record.get(
                    "asset_type"
                )
                or ""
            ).lower()

            path_text = normalize_path_text(
                record.get(
                    "path"
                )
            )

            suffix_type = (
                classify_asset_path(
                    Path(
                        path_text
                    )
                )
                if path_text
                else "unknown"
            )

            if (
                explicit_type
                in {
                    "type_b",
                    "type-b",
                    "b",
                    "reference",
                    "reference_only",
                }
                or suffix_type == "type_B"
            ):
                type_b_records.append(
                    record
                )

        if (
            not type_b_files
            and not type_b_records
        ):
            self.add(
                domain="type_B_intelligence",
                check="reference_intelligence_readiness",
                status="skipped",
                summary=(
                    "No Type B assets were discovered; Type B "
                    "intelligence audit was skipped."
                ),
                evidence={
                    "type_B_file_count":
                        0,

                    "type_B_record_count":
                        0,

                    "evidence_state":
                        "insufficient_evidence",

                    "expected": [
                        "reference_url",
                        "reference_metadata",
                        "source_classification",
                        "runtime_reference_visibility",
                    ],

                    "skip_reason":
                        (
                            "No Type B file or DB record candidates "
                            "were discovered."
                        ),

                    "audit_layer":
                        "type_B_reference_intelligence",

                    "note": (
                        "Skipped Type B audit does not imply "
                        "Type B readiness. It only means no Type B "
                        "evidence was available."
                    ),
                },
                governance_domain="artifact_backbone",
                contract_type="type_B_reference_intelligence",
            )
            return

        missing_reference_url: List[Dict[str, Any]] = []
        reference_url_count = 0

        for record in type_b_records:
            reference_url = str(
                record.get(
                    "reference_url"
                )
                or ""
            ).strip()

            if reference_url:
                reference_url_count += 1

            else:
                missing_reference_url.append(
                    {
                        "db_path":
                            record.get(
                                "db_path"
                            ),

                        "table":
                            record.get(
                                "table"
                            ),

                        "path":
                            record.get(
                                "path"
                            ),
                    }
                )

        pass_condition = (
            bool(
                type_b_records
            )
            and not missing_reference_url
        )

        intelligence_state = (
            "ready"
            if pass_condition
            else "incomplete"
        )

        self.add(
            domain="type_B_intelligence",
            check="reference_intelligence_readiness",
            status=(
                "pass"
                if pass_condition
                else "fail"
            ),
            summary=(
                "Type B reference intelligence is usable."
                if pass_condition
                else (
                    "One or more Type B records lack reference_url "
                    "evidence."
                )
            ),
            evidence={
                "type_B_file_count":
                    len(
                        type_b_files
                    ),

                "type_B_record_count":
                    len(
                        type_b_records
                    ),

                "reference_url_count":
                    reference_url_count,

                "missing_reference_url_count":
                    len(
                        missing_reference_url
                    ),

                "missing_reference_url":
                    missing_reference_url,

                "intelligence_state":
                    intelligence_state,

                "audit_layer":
                    "type_B_reference_intelligence",

                "expected": [
                    "reference_url",
                    "reference_metadata",
                    "source_classification",
                    "runtime_reference_visibility",
                ],

                "note": (
                    "This check verifies reference evidence only. "
                    "It does not perform semantic analysis of Type B "
                    "reference content."
                ),
            },
            suggested_fix=(
                None
                if pass_condition
                else (
                    "Persist a usable reference_url for every Type B "
                    "asset before treating it as runtime-ready."
                )
            ),
            governance_domain="artifact_backbone",
            contract_type="type_B_reference_intelligence",
        )


    def check_runtime_db_read(self) -> None:
        #
        # ----------------------------------------------------------
        # Runtime DB Readiness
        #
        # Runtime DB readiness requires:
        #
        #   - readable artifact DB evidence
        #   - usable asset rows
        #   - usable pattern rows
        #   - at least one importable runtime reader module
        #
        # This check is read-only.
        # ----------------------------------------------------------
        #

        snapshots_by_db = (
            self.get_all_artifact_db_snapshots()
        )

        records_by_db = (
            self.iter_all_artifact_db_records()
        )

        chart_asset_candidates = (
            self.resolve_asset_db_candidates()
        )

        chart_asset_snapshots = (
            self.get_asset_db_snapshots()
        )

        chart_asset_records = (
            self.iter_asset_db_records()
        )

        chart_pattern_candidates = (
            self.resolve_artifact_db_candidates(
                CHART_PATTERNS_DB_NAME
            )
        )

        chart_pattern_snapshots = (
            self.get_artifact_db_snapshots(
                CHART_PATTERNS_DB_NAME
            )
        )

        chart_pattern_records = (
            self.iter_chart_pattern_records()
        )

        readable_artifact_db_count = (
            self.readable_artifact_db_count()
        )

        asset_readable_db_count = len(
            [
                snapshot
                for snapshot in chart_asset_snapshots
                if snapshot.get(
                    "exists"
                )
                and snapshot.get(
                    "readable"
                )
                and not snapshot.get(
                    "error"
                )
            ]
        )

        pattern_readable_db_count = len(
            [
                snapshot
                for snapshot in chart_pattern_snapshots
                if snapshot.get(
                    "exists"
                )
                and snapshot.get(
                    "readable"
                )
                and not snapshot.get(
                    "error"
                )
            ]
        )

        path_resolvable_count = len(
            [
                record
                for record in chart_asset_records
                if normalize_path_text(
                    record.get(
                        "path"
                    )
                )
            ]
        )

        text_readable_count = len(
            [
                record
                for record in chart_asset_records
                if str(
                    record.get(
                        "text"
                    )
                    or ""
                ).strip()
            ]
        )

        reference_readable_count = len(
            [
                record
                for record in chart_asset_records
                if str(
                    record.get(
                        "reference_url"
                    )
                    or ""
                ).strip()
            ]
        )

        pattern_readable_count = len(
            [
                record
                for record in chart_pattern_records
                if (
                    str(
                        record.get(
                            "pattern"
                        )
                        or ""
                    ).strip()
                    or str(
                        record.get(
                            "chart_id"
                        )
                        or ""
                    ).strip()
                )
            ]
        )

        #
        # ----------------------------------------------------------
        # Runtime reader probes
        #
        # These are compatibility probes. Repository-driven discovery
        # should remain the preferred source of reader topology, but
        # import probes provide runtime evidence when known readers
        # exist.
        # ----------------------------------------------------------
        #

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
            result = import_module_probe(
                module_name
            )

            import_results[
                module_name
            ] = result

            if result.get(
                "status"
            ) == "pass":
                any_reader_imported = True

        asset_pass_condition = (
            bool(
                chart_asset_candidates
            )
            and asset_readable_db_count > 0
            and bool(
                chart_asset_records
            )
            and path_resolvable_count > 0
            and (
                text_readable_count > 0
                or reference_readable_count > 0
            )
        )

        pattern_pass_condition = (
            bool(
                chart_pattern_candidates
            )
            and pattern_readable_db_count > 0
            and bool(
                chart_pattern_records
            )
            and pattern_readable_count > 0
        )

        pass_condition = (
            readable_artifact_db_count > 0
            and asset_pass_condition
            and pattern_pass_condition
            and any_reader_imported
        )

        readiness_state = (
            "ready"
            if pass_condition
            else "incomplete"
        )

        self.add(
            domain="runtime_db_read",
            check="runtime_db_asset_pattern_readiness",
            status=(
                "pass"
                if pass_condition
                else "fail"
            ),
            summary=(
                "Runtime DB read readiness evidence is sufficient for assets and patterns."
                if pass_condition
                else (
                    "Runtime DB read readiness is incomplete for assets, "
                    "patterns, or readers."
                )
            ),
            evidence={
                "artifact_database_names":
                    ARTIFACT_DATABASE_NAMES,

                "readiness_state":
                    readiness_state,

                "readable_artifact_db_count":
                    readable_artifact_db_count,

                "records_by_db_count": {
                    db_name:
                        len(
                            records
                        )
                    for db_name, records in records_by_db.items()
                },

                "snapshots_by_db_count": {
                    db_name:
                        len(
                            snapshots
                        )
                    for db_name, snapshots in snapshots_by_db.items()
                },

                "chart_asset_db_candidate_count":
                    len(
                        chart_asset_candidates
                    ),

                "chart_asset_readable_db_count":
                    asset_readable_db_count,

                "chart_asset_record_count":
                    len(
                        chart_asset_records
                    ),

                "path_resolvable_count":
                    path_resolvable_count,

                "text_readable_count":
                    text_readable_count,

                "reference_readable_count":
                    reference_readable_count,

                "chart_pattern_db_candidate_count":
                    len(
                        chart_pattern_candidates
                    ),

                "chart_pattern_readable_db_count":
                    pattern_readable_db_count,

                "chart_pattern_record_count":
                    len(
                        chart_pattern_records
                    ),

                "pattern_readable_count":
                    pattern_readable_count,

                "asset_pass_condition":
                    asset_pass_condition,

                "pattern_pass_condition":
                    pattern_pass_condition,

                "reader_import_results":
                    import_results,

                "any_reader_imported":
                    any_reader_imported,

                "runtime_operability_layer":
                    "artifact_db_readiness",

                "read_mode":
                    "read_only",

                "repository_driven_note": (
                    "Known reader import probes are compatibility evidence. "
                    "Repository-driven reader discovery remains preferred "
                    "for topology analysis."
                ),

                "note": (
                    "Runtime DB readiness requires read-only DB evidence, "
                    "usable asset rows, usable pattern rows, and at least "
                    "one importable reader module."
                ),
            },
            suggested_fix=(
                None
                if pass_condition
                else (
                    "Verify artifact DB readers and ensure chart_assets.db "
                    "and chart_patterns.db contain readable runtime rows."
                )
            ),
            governance_domain="artifact_backbone",
            contract_type="runtime_artifact_readiness",
        )


    def check_deletion_readiness(self) -> None:
        #
        # ----------------------------------------------------------
        # Deletion Readiness
        #
        # Deletion is conservative.
        #
        # Source chart files must be retained until artifact coverage,
        # hash audit, Type A usability, relationship audit,
        # and runtime DB readiness pass.
        # ----------------------------------------------------------
        #

        scan_records = (
            self.iter_file_scan_inventory_records()
        )

        asset_records = (
            self.iter_asset_db_records()
        )

        pattern_records = (
            self.iter_chart_pattern_records()
        )

        repository_assets = (
            self.discovered_assets.get(
                "type_A",
                [],
            )
            + self.discovered_assets.get(
                "type_B",
                [],
            )
        )

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
                if result.domain == "hash_audit"
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

        relationship_verified = (
            artifact_relationship_result is not None
            and artifact_relationship_result.status == "pass"
        )

        runtime_db_ready = (
            runtime_db_result is not None
            and runtime_db_result.status == "pass"
        )

        required = {
            "file_scan_inventory_complete":
                bool(
                    scan_records
                ),

            "chart_assets_db_complete":
                bool(
                    asset_records
                ),

            "chart_patterns_db_complete":
                bool(
                    pattern_records
                ),

            "repository_coverage_complete":
                bool(
                    repository_assets
                ),

            "artifact_databases_verified":
                (
                    artifact_db_result is not None
                    and artifact_db_result.status == "pass"
                ),

            "scan_to_asset_verified":
                relationship_verified,

            "asset_to_pattern_verified":
                relationship_verified,

            "asset_coverage_verified":
                (
                    asset_coverage_result is not None
                    and asset_coverage_result.status == "pass"
                ),

            "hash_consistency_verified":
                (
                    hash_result is not None
                    and hash_result.status == "pass"
                ),

            "type_A_text_usable":
                (
                    type_a_result is not None
                    and type_a_result.status == "pass"
                ),

            "runtime_can_use_db_assets":
                runtime_db_ready,

            "runtime_can_use_db_patterns":
                runtime_db_ready,
        }

        passed = all(
            required.values()
        )

        missing_requirements = [
            requirement
            for requirement, value in required.items()
            if not value
        ]

        self.add(
            domain="governance",
            check="deletion_readiness",
            status=(
                "pass"
                if passed
                else "fail"
            ),
            summary=(
                "Deletion readiness gate passed."
                if passed
                else (
                    "Deletion readiness gate failed. Source chart files "
                    "must be retained."
                )
            ),
            evidence={
                "required":
                    required,

                "missing_requirements":
                    missing_requirements,

                "repository_asset_count":
                    len(
                        repository_assets
                    ),

                "file_scan_inventory_record_count":
                    len(
                        scan_records
                    ),

                "chart_asset_record_count":
                    len(
                        asset_records
                    ),

                "chart_pattern_record_count":
                    len(
                        pattern_records
                    ),

                "failure_action": (
                    "block_deletion_recommendation"
                    if not passed
                    else None
                ),

                "audit_layer":
                    "deletion_governance",

                "governance_principle": (
                    "Deletion is permitted only after global audit "
                    "passes. Validation alone is not sufficient."
                ),

                "completed_phase_protection": {
                    "does_not_modify_phase_logic":
                        True,

                    "does_not_modify_canonical_ingestion":
                        True,

                    "does_not_modify_asset_pipeline":
                        True,
                },
            },
            suggested_fix=(
                None
                if passed
                else (
                    "Keep source chart files until artifact coverage, "
                    "hash consistency, Type A usability, relationship "
                    "audit, and runtime DB readiness pass."
                )
            ),
            governance_domain="artifact_backbone",
            contract_type="deletion_readiness",
        )

    def check_flow_audit(self) -> None:
        #
        # ----------------------------------------------------------
        # Flow audit
        #
        # Flow audit checks static runtime flow presence and
        # wiring evidence only.
        #
        # It does not validate recommendation quality, gameplay
        # inference correctness, personalization, localization, or
        # completed phase logic.
        # ----------------------------------------------------------
        #

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

        dependency_ready = (
            dependency_result is not None
            and dependency_result.status == "pass"
        )

        runtime_import_ready = (
            runtime_import_result is not None
            and runtime_import_result.status == "pass"
        )

        if (
            not dependency_ready
            or not runtime_import_ready
        ):
            self.add(
                domain="flow_audit",
                check="runtime_flow_entrypoints",
                status="skipped",
                summary=(
                    "Flow audit was skipped because dependency "
                    "or runtime import readiness is incomplete."
                ),
                evidence={
                    "dependency_ready":
                        dependency_ready,

                    "runtime_import_ready":
                        runtime_import_ready,

                    "reason": (
                        "Flow audit requires dependency reality "
                        "and runtime import reality to pass first."
                    ),

                    "flows":
                        sorted(
                            FLOW_KEYWORDS.keys()
                        ),

                    "runtime_limited_possible":
                        True,

                    "governance_interpretation": (
                        "Skipped flow audit caused by dependency "
                        "or import constraints should be interpreted as "
                        "runtime-limited, not as an automatic governance "
                        "blocker."
                    ),
                },
                governance_domain="flow_contracts",
                contract_type="flow_existence",
            )
            return

        python_files: List[Path] = []

        try:
            for path in self.backend_root.rglob(
                "*.py"
            ):
                if path.is_file():
                    python_files.append(
                        path
                    )
        except Exception:
            pass

        flow_evidence: Dict[str, Dict[str, Any]] = {}

        for flow_name, keywords in FLOW_KEYWORDS.items():
            matched_files: List[str] = []

            keyword_hits: Dict[str, List[str]] = {
                keyword: []
                for keyword in keywords
            }

            for path in python_files:
                normalized_path = normalize_path_text(
                    path
                )

                text = read_text_safely(
                    path
                )

                combined = (
                    f"{normalized_path}\n{text}"
                    .lower()
                )

                file_matched = False

                for keyword in keywords:
                    if keyword.lower() in combined:
                        keyword_hits[
                            keyword
                        ].append(
                            str(
                                path.resolve()
                            )
                        )

                        file_matched = True

                if file_matched:
                    matched_files.append(
                        str(
                            path.resolve()
                        )
                    )

            missing_keywords = [
                keyword
                for keyword, hits in keyword_hits.items()
                if not hits
            ]

            flow_evidence[
                flow_name
            ] = {
                "expected_keywords":
                    keywords,

                "matched_files":
                    sorted(
                        set(
                            matched_files
                        )
                    ),

                "keyword_hits": {
                    keyword:
                        sorted(
                            set(
                                hits
                            )
                        )
                    for keyword, hits in keyword_hits.items()
                },

                "missing_keywords":
                    missing_keywords,

                "ready":
                    not missing_keywords,
            }

        failed_flows = [
            flow_name
            for flow_name, evidence in flow_evidence.items()
            if not evidence.get(
                "ready"
            )
        ]

        pass_condition = (
            not failed_flows
        )

        self.add(
            domain="flow_audit",
            check="runtime_flow_entrypoints",
            status=(
                "pass"
                if pass_condition
                else "warning"
            ),
            summary=(
                "Runtime flow entrypoint evidence was found for chart-first, player-first, and progression flows."
                if pass_condition
                else "Some runtime flow evidence is incomplete."
            ),
            evidence={
                "flow_evidence":
                    flow_evidence,

                "failed_flows":
                    failed_flows,

                "audit_style":
                    "static_keyword_entrypoint_check",

                "audit_scope":
                    "flow_existence",

                "required_flows":
                    sorted(
                        FLOW_KEYWORDS.keys()
                    ),

                "runtime_limited_possible":
                    False,

                "note": (
                    "Flow audit checks flow presence and wiring "
                    "evidence only. It does not validate recommendation "
                    "quality, gameplay inference correctness, "
                    "personalization, or localization."
                ),

                "completed_phase_protection": {
                    "does_not_modify_phase_logic":
                        True,

                    "does_not_modify_recommendation_logic":
                        True,

                    "does_not_modify_personalization_logic":
                        True,

                    "does_not_modify_localization_logic":
                        True,
                },
            },
            suggested_fix=(
                None
                if pass_condition
                else (
                    "Expose clearer entrypoints and stopping points "
                    "for chart-first, player-first, and progression-driven "
                    "flows without modifying completed phase logic."
                )
            ),
            governance_domain="flow_contracts",
            contract_type="flow_existence",
        )


    def check_layer_separation(self) -> None:
        #
        # ----------------------------------------------------------
        # Layer Separation
        #
        # This audit separates:
        #
        #   hint       -> textual signal only
        #   suspicion  -> import-like / structural reference
        #   evidence   -> executable side-effect / persistence signal
        #
        # Only evidence-level findings may block governance.
        # ----------------------------------------------------------
        #

        python_files: List[Path] = []

        try:
            for path in self.backend_root.rglob(
                "*.py"
            ):
                if path.is_file():
                    python_files.append(
                        path
                    )
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
            # Ignore comments / empty lines to reduce false positives.
            #

            if (
                not stripped
                or stripped.startswith(
                    "#"
                )
            ):
                return (
                    "ignored",
                    "Comment or empty line; not treated as boundary evidence.",
                )

            #
            # Tier 3 — evidence.
            #
            # These indicate likely executable side-effect or
            # responsibility crossing.
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

            if any(
                token in lowered
                for token in evidence_tokens
            ):
                return (
                    "evidence",
                    "Executable side-effect or persistence-like operation detected.",
                )

            #
            # Tier 2 — suspicion.
            #
            # Imports from prohibited layers are stronger than plain
            # text hits, but still not proof of mutation.
            #

            import_like = (
                lowered.startswith(
                    "import "
                )
                or lowered.startswith(
                    "from "
                )
            )

            if (
                import_like
                and hint_lower in lowered
            ):
                return (
                    "suspicion",
                    "Import-like reference to prohibited layer detected.",
                )

            #
            # Tier 1 — hint.
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
            normalized_path = normalize_path_text(
                path
            ).lower()

            text = read_text_safely(
                path
            )

            matched_layers: Set[str] = set()

            for layer, keywords in LAYER_KEYWORDS.items():
                if any(
                    keyword.lower() in normalized_path
                    for keyword in keywords
                ):
                    matched_layers.add(
                        layer
                    )

                    layer_files[
                        layer
                    ].append(
                        str(
                            path.resolve()
                        )
                    )

            if not matched_layers:
                continue

            lines = text.splitlines()

            for layer in matched_layers:
                prohibited_hints = (
                    PROHIBITED_LAYER_IMPORT_HINTS.get(
                        layer,
                        [],
                    )
                )

                for line_number, line_text in enumerate(
                    lines,
                    start=1,
                ):
                    for hint in prohibited_hints:
                        if hint not in line_text:
                            continue

                        confidence, justification = (
                            classify_boundary_signal(
                                layer=layer,
                                hint=hint,
                                line_text=line_text,
                            )
                        )

                        if confidence == "ignored":
                            continue

                        finding = {
                            "layer":
                                layer,

                            "file":
                                str(
                                    path.resolve()
                                ),

                            "line":
                                line_number,

                            "matched_hint":
                                hint,

                            "confidence":
                                confidence,

                            "snippet":
                                line_text.strip()[:300],

                            "justification":
                                justification,
                        }

                        if confidence == "evidence":
                            evidence_findings.append(
                                finding
                            )

                        elif confidence == "suspicion":
                            suspicion_findings.append(
                                finding
                            )

                        else:
                            hint_findings.append(
                                finding
                            )

        evidence_count = len(
            evidence_findings
        )

        suspicion_count = len(
            suspicion_findings
        )

        hint_count = len(
            hint_findings
        )

        highest_confidence = (
            "evidence"
            if evidence_count > 0
            else (
                "suspicion"
                if suspicion_count > 0
                else (
                    "hint"
                    if hint_count > 0
                    else "none"
                )
            )
        )

        if evidence_count > 0:
            status = "critical"
            summary = (
                "Layer boundary audit found evidence-level prohibited boundary violations."
            )

        elif suspicion_count > 0:
            status = "warning"
            summary = (
                "Layer boundary audit found suspicious boundary references, "
                "but no evidence-level violations."
            )

        elif hint_count > 0:
            status = "info"
            summary = (
                "Layer boundary audit found textual boundary hints only; "
                "no actionable violations confirmed."
            )

        else:
            status = "pass"
            summary = (
                "Layer boundary audit found no prohibited boundary signals."
            )

        self.add(
            domain="layer_separation",
            check="layer_boundary_audit",
            status=status,
            summary=summary,
            evidence={
                "layer_files": {
                    layer:
                        sorted(
                            set(
                                files
                            )
                        )
                    for layer, files in layer_files.items()
                },

                "risk_summary": {
                    "evidence_count":
                        evidence_count,

                    "suspicion_count":
                        suspicion_count,

                    "hint_count":
                        hint_count,

                    "highest_confidence":
                        highest_confidence,

                    "governance_blocking":
                        evidence_count > 0,
                },

                "confidence_summary": {
                    "evidence":
                        evidence_count,

                    "suspicion":
                        suspicion_count,

                    "hint":
                        hint_count,
                },

                "evidence_findings":
                    evidence_findings,

                "suspicion_findings":
                    suspicion_findings,

                "hint_findings":
                    hint_findings,

                "prohibited_layer_import_hints":
                    PROHIBITED_LAYER_IMPORT_HINTS,

                "audit_style":
                    "tiered_static_boundary_governance",

                "audit_scope":
                    "layer_responsibility",

                "layer_model":
                    list(
                        LAYER_KEYWORDS.keys()
                    ),

                "confidence_model": {
                    "hint": {
                        "meaning":
                            "Textual keyword match only.",

                        "severity":
                            "info",

                        "governance_blocking":
                            False,
                    },

                    "suspicion": {
                        "meaning":
                            "Import-like or structural reference to prohibited responsibility.",

                        "severity":
                            "warning",

                        "governance_blocking":
                            False,
                    },

                    "evidence": {
                        "meaning":
                            "Executable side-effect or persistence-like operation detected in wrong layer.",

                        "severity":
                            "critical",

                        "governance_blocking":
                            True,
                    },
                },

                "governance_interpretation": {
                    "ready":
                        "No evidence-level violations detected.",

                    "review_needed":
                        "Suspicion-level references require review but do not block governance.",

                    "blocked":
                        "Evidence-level findings block governance.",
                },

                "false_positive_controls": [
                    "Comments and empty lines are ignored.",
                    "Plain keyword hits are classified as hint, not violation.",
                    "Import-like references are classified as suspicion, not critical violation.",
                    "Only executable side-effect evidence escalates to critical.",
                ],

                "note": (
                    "This audit separates hints, suspicions, and "
                    "evidence-level violations. Only evidence-level "
                    "findings should block governance."
                ),
            },
            suggested_fix=(
                None
                if evidence_count == 0
                else (
                    "Move executable side effects or persistence ownership "
                    "into the correct layer. Converters, validators, readers, "
                    "models, normalizers, and classifiers must remain "
                    "responsibility-separated."
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
        #
        # ----------------------------------------------------------
        # MCP Config Presence
        #
        # MCP readiness is evaluated independently from REST/runtime
        # dependency readiness.
        # ----------------------------------------------------------
        #

        if not self.mcp_config:
            self.add(
                domain="mcp",
                check="config_present",
                status="skipped",
                summary="No MCP config path was provided.",
                evidence={
                    "reason":
                        "mcp_config_not_provided",

                    "required_server":
                        "rhythm-game-assistant",

                    "required_adapter":
                        "mcp_server.py",

                    "transport":
                        "stdio",
                },
                governance_domain="mcp_contracts",
                contract_type="mcp_config_presence",
            )
            return

        if not self.mcp_config.exists():
            self.add(
                domain="mcp",
                check="config_present",
                status="warning",
                summary="Provided MCP config path does not exist.",
                evidence={
                    "path":
                        str(
                            self.mcp_config
                        ),

                    "required_server":
                        "rhythm-game-assistant",

                    "required_adapter":
                        "mcp_server.py",

                    "transport":
                        "stdio",
                },
                suggested_fix=(
                    "Provide a readable MCP config path or omit "
                    "--mcp-config when MCP audit is not required."
                ),
                governance_domain="mcp_contracts",
                contract_type="mcp_config_presence",
            )
            return

        data = self.read_json_file(
            self.mcp_config
        )

        if data is None:
            self.add(
                domain="mcp",
                check="config_parse",
                status="fail",
                summary="MCP config could not be parsed as JSON.",
                evidence={
                    "path":
                        str(
                            self.mcp_config
                        ),
                },
                suggested_fix=(
                    "Ensure the MCP config file is valid JSON."
                ),
                governance_domain="mcp_contracts",
                contract_type="mcp_config_parse",
            )
            return

        servers = (
            data.get(
                "servers",
                {},
            )
            if isinstance(
                data,
                dict,
            )
            else {}
        )

        server = (
            servers.get(
                "rhythm-game-assistant"
            )
            if isinstance(
                servers,
                dict,
            )
            else None
        )

        if not server:
            self.add(
                domain="mcp_contract",
                check="rga_server_defined",
                status="fail",
                summary="rhythm-game-assistant MCP server is not defined.",
                evidence={
                    "path":
                        str(
                            self.mcp_config
                        ),

                    "server_keys":
                        sorted(
                            list(
                                servers.keys()
                            )
                        )
                        if isinstance(
                            servers,
                            dict,
                        )
                        else [],

                    "required_server":
                        "rhythm-game-assistant",
                },
                suggested_fix=(
                    "Define a rhythm-game-assistant server entry "
                    "in the MCP config."
                ),
                governance_domain="mcp_contracts",
                contract_type="mcp_server_contract",
            )
            return

        server_type = (
            server.get(
                "type"
            )
            if isinstance(
                server,
                dict,
            )
            else None
        )

        env = (
            server.get(
                "env"
            )
            or {}
            if isinstance(
                server,
                dict,
            )
            else {}
        )

        args = (
            server.get(
                "args",
                [],
            )
            if isinstance(
                server,
                dict,
            )
            else []
        )

        command = (
            server.get(
                "command"
            )
            if isinstance(
                server,
                dict,
            )
            else None
        )

        command_text = str(
            command
            or ""
        )

        args_text = " ".join(
            str(
                item
            )
            for item in args
        )

        references_mcp_server = (
            "mcp_server.py" in command_text
            or "mcp_server.py" in args_text
        )

        env_keys = (
            sorted(
                list(
                    env.keys()
                )
            )
            if isinstance(
                env,
                dict,
            )
            else []
        )

        has_rest_url = (
            "RGA_REST_URL" in env_keys
            or any(
                "RGA_REST_URL" in str(
                    item
                )
                for item in args
            )
        )

        self.add(
            domain="mcp_contract",
            check="mcp_server_contract",
            status=(
                "pass"
                if server_type == "stdio"
                else "fail"
            ),
            summary=(
                "MCP contract satisfied."
                if server_type == "stdio"
                else "RGA MCP server does not satisfy stdio contract."
            ),
            evidence={
                "type":
                    server_type,

                "command":
                    command,

                "args":
                    args,

                "env_keys":
                    env_keys,

                "references_mcp_server":
                    references_mcp_server,

                "has_rest_url_evidence":
                    has_rest_url,

                "required_server": {
                    "id":
                        "rhythm-game-assistant",

                    "type":
                        "stdio",
                },

                "contract_interpretation": (
                    "MCP server transport is evaluated independently "
                    "from REST dependency readiness."
                ),
            },
            suggested_fix=(
                None
                if server_type == "stdio"
                else (
                    "Use stdio transport for the rhythm-game-assistant "
                    "MCP server."
                )
            ),
            governance_domain="mcp_contracts",
            contract_type="mcp_server_contract",
        )

        self.add(
            domain="mcp_contract",
            check="mcp_adapter_contract",
            status=(
                "pass"
                if references_mcp_server
                else "warning"
            ),
            summary=(
                "MCP config references mcp_server.py."
                if references_mcp_server
                else "MCP config does not clearly reference mcp_server.py."
            ),
            evidence={
                "command":
                    command,

                "args":
                    args,

                "references_mcp_server":
                    references_mcp_server,

                "server_keys":
                    sorted(
                        list(
                            server.keys()
                        )
                    )
                    if isinstance(
                        server,
                        dict,
                    )
                    else [],

                "adapter_contract_note": (
                    "Adapter visibility is reviewable evidence. "
                    "Absence of a visible adapter reference is a warning, "
                    "not an automatic governance blocker."
                ),
            },
            suggested_fix=(
                None
                if references_mcp_server
                else (
                    "Point the rhythm-game-assistant MCP server "
                    "command or args to the local mcp_server.py adapter."
                )
            ),
            governance_domain="mcp_contracts",
            contract_type="mcp_adapter_contract",
        )

        tool_like_keys: List[str] = []

        if isinstance(
            server,
            dict,
        ):
            for key in [
                "tools",
                "toolsets",
                "capabilities",
            ]:
                if key in server:
                    tool_like_keys.append(
                        key
                    )

        self.add(
            domain="mcp_contract",
            check="tool_surface_evidence",
            status="info",
            summary="MCP tool registration visibility evidence captured from config.",
            evidence={
                "tool_like_keys_present":
                    tool_like_keys,

                "server_keys":
                    sorted(
                        list(
                            server.keys()
                        )
                    )
                    if isinstance(
                        server,
                        dict,
                    )
                    else [],

                "note": (
                    "Some MCP adapters register tools dynamically at runtime, "
                    "so absence of tool keys in config is not automatically "
                    "a failure."
                ),

                "visibility_only":
                    True,
            },
            governance_domain="mcp_contracts",
            contract_type="mcp_tool_surface",
        )


    def check_rest_contract(self) -> None:
        #
        # ----------------------------------------------------------
        # REST Contract
        #
        # REST audit is optional and only runs when --rest is
        # explicitly enabled.
        # ----------------------------------------------------------
        #

        if not self.run_rest:
            self.add(
                domain="rest_api",
                check="rest_audit_enabled",
                status="skipped",
                summary="REST checks were skipped. Use --rest to enable REST audit.",
                evidence={
                    "api_url":
                        self.api_url,

                    "rest_checks_enabled":
                        False,

                    "runtime_limited_possible":
                        True,
                },
                governance_domain="architecture_contracts",
                contract_type="rest_contract",
            )
            return

        payloads = {
            "song_mode_post": {
                "mode":
                    "song",

                "game_id":
                    "proseka",

                "locale":
                    "en-US",

                "max_items":
                    1,

                "song_ids": [
                    "local-test-song",
                ],

                "player_signals":
                    {},

                "player_profile":
                    {},

                "player_history":
                    {},

                "preferences":
                    {},

                "evidence":
                    {},
            },

            "game_mode_post": {
                "mode":
                    "game",

                "game_id":
                    "proseka",

                "locale":
                    "en-US",

                "max_items":
                    3,

                "player_signals": {
                    "expert_fc_count":
                        "120",

                    "master_fc_count":
                        "20",

                    "highest_confirmed_difficulty":
                        "32",
                },

                "player_profile":
                    {},

                "player_history":
                    {},

                "preferences":
                    {},

                "evidence":
                    {},
            },
        }

        for check, payload in payloads.items():

            try:
                result = self.post_json(
                    payload
                )

                self.add(
                    domain="rest_api",
                    check=check,
                    status="pass",
                    summary=f"{check} completed.",
                    evidence={
                        "response_keys": (
                            sorted(
                                list(
                                    result.keys()
                                )
                            )
                            if isinstance(
                                result,
                                dict,
                            )
                            else []
                        ),

                        "contract_type":
                            "rest_response_contract",

                        "api_url":
                            self.api_url,
                    },
                    governance_domain="architecture_contracts",
                    contract_type="rest_contract",
                )

            except urllib.error.HTTPError as exc:
                body = exc.read().decode(
                    "utf-8",
                    errors="replace",
                )

                summary = (
                    f"{check} returned HTTP {exc.code}."
                )

                expected_runtime_gap = (
                    check == "game_mode_post"
                    and exc.code == 501
                    and "Games recommender not configured" in body
                )

                if expected_runtime_gap:
                    summary = (
                        "Game mode confirms games_recommender is not configured."
                    )

                self.add(
                    domain="rest_api",
                    check=check,
                    status="fail",
                    summary=summary,
                    evidence={
                        "status":
                            exc.code,

                        "body":
                            body,

                        "contract_type":
                            "rest_response_contract",

                        "expected_runtime_gap":
                            expected_runtime_gap,
                    },
                    suggested_fix=(
                        (
                            "Provide games_recommender wiring when game-mode "
                            "REST audit is intended."
                        )
                        if expected_runtime_gap
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
                        "error":
                            str(
                                exc
                            ),

                        "contract_type":
                            "rest_response_contract",

                        "api_url":
                            self.api_url,
                    },
                    suggested_fix=(
                        "Verify REST runtime availability, dependency reality, "
                        "and API endpoint reachability before treating this as "
                        "a governance failure."
                    ),
                    governance_domain="architecture_contracts",
                    contract_type="rest_contract",
                )


    def check_flow_contract_audit(self) -> None:
        #
        # ----------------------------------------------------------
        # Flow Contract audit
        #
        # This verifies flow boundary evidence only.
        # It does not validate recommendation quality, gameplay
        # inference correctness, personalization, or localization.
        # ----------------------------------------------------------
        #

        flow_result = next(
            (
                result
                for result in self.results
                if result.domain == "flow_audit"
                and result.check == "runtime_flow_entrypoints"
            ),
            None,
        )

        if flow_result is None:
            self.add(
                domain="flow_contract_audit",
                check="flow_contract_compliance",
                status="skipped",
                summary=(
                    "Flow contract audit was skipped because flow "
                    "audit has not produced evidence."
                ),
                evidence={
                    "reason":
                        "runtime_flow_entrypoints result not found",

                    "required_flows":
                        sorted(
                            FLOW_KEYWORDS.keys()
                        ),

                    "runtime_limited_possible":
                        True,
                },
                governance_domain="flow_contracts",
                contract_type="flow_contract",
            )
            return

        if flow_result.status == "skipped":
            self.add(
                domain="flow_contract_audit",
                check="flow_contract_compliance",
                status="skipped",
                summary=(
                    "Flow contract audit was skipped because flow "
                    "audit preconditions were not met."
                ),
                evidence={
                    "source_status":
                        flow_result.status,

                    "source_summary":
                        flow_result.summary,

                    "required_flows":
                        sorted(
                            FLOW_KEYWORDS.keys()
                        ),

                    "runtime_limited_possible":
                        True,

                    "governance_interpretation": (
                        "Skipped flow audit caused by runtime or "
                        "dependency constraints should be treated as "
                        "runtime_limited, not as an automatic governance block."
                    ),
                },
                governance_domain="flow_contracts",
                contract_type="flow_contract",
            )
            return

        flow_evidence = (
            flow_result.evidence.get(
                "flow_evidence",
                {},
            )
            if isinstance(
                flow_result.evidence,
                dict,
            )
            else {}
        )

        failed_flows = (
            flow_result.evidence.get(
                "failed_flows",
                [],
            )
            if isinstance(
                flow_result.evidence,
                dict,
            )
            else []
        )

        contract_expectations = {
            "chart_first": {
                "entry_artifact":
                    "chart",

                "required": [
                    "chart_resolution",
                    "pattern_detection",
                    "tips",
                    "personalization",
                    "localization",
                ],
            },

            "player_first": {
                "entry_artifact":
                    "player",

                "required": [
                    "player_signals",
                    "song_recommendation",
                ],

                "optional": [
                    "tips",
                ],
            },

            "progression": {
                "entry_artifact":
                    "progression",

                "required": [
                    "game_recommendation",
                    "song_recommendation",
                ],

                "optional": [
                    "tips",
                ],
            },
        }

        pass_condition = (
            flow_result.status == "pass"
            and not failed_flows
        )

        self.add(
            domain="flow_contract_audit",
            check="flow_contract_compliance",
            status=(
                "pass"
                if pass_condition
                else "fail"
            ),
            summary=(
                "Flow contracts are supported by runtime flow evidence."
                if pass_condition
                else (
                    "One or more flow contracts lack supporting runtime "
                    "flow evidence."
                )
            ),
            evidence={
                "contract_expectations":
                    contract_expectations,

                "flow_evidence":
                    flow_evidence,

                "failed_flows":
                    failed_flows,

                "audit_scope":
                    "flow_contract_compliance",

                "note": (
                    "This check verifies flow boundary evidence only. "
                    "It does not validate recommendation quality or gameplay "
                    "inference correctness."
                ),

                "completed_phase_protection": {
                    "does_not_modify_phase_logic":
                        True,

                    "does_not_modify_recommendation_logic":
                        True,

                    "does_not_modify_personalization_or_localization":
                        True,
                },
            },
            suggested_fix=(
                None
                if pass_condition
                else (
                    "Expose clearer entrypoints, main artifacts, and stopping "
                    "points for chart-first, player-first, and progression-driven "
                    "flows without modifying completed phase logic."
                )
            ),
            governance_domain="flow_contracts",
            contract_type="flow_contract",
        )


    def classify_governance_failure_lineage(
        self,
        *,
        governance_failures: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        #
        # ----------------------------------------------------------
        # Root vs Derived Failure Classification
        #
        # Root failures are independently actionable blockers.
        #
        # Derived failures are downstream consequences of an upstream
        # root failure and should be re-evaluated after the root
        # contract passes.
        # ----------------------------------------------------------
        #

        root_failures: List[Dict[str, Any]] = []
        derived_failures: List[Dict[str, Any]] = []

        failed_contract_types: Set[str] = {
            item.get(
                "contract_type"
            )
            for item in governance_failures
            if item.get(
                "contract_type"
            )
        }

        for item in governance_failures:
            contract_type = item.get(
                "contract_type"
            )

            if not contract_type:
                continue

            if contract_type in GOVERNANCE_META_CONTRACT_TYPES:
                continue

            dependency_of = DERIVED_FAILURE_POLICY.get(
                contract_type
            )

            if (
                dependency_of
                and dependency_of in failed_contract_types
            ):
                derived_item = dict(
                    item
                )

                derived_item[
                    "failure_class"
                ] = "derived"

                derived_item[
                    "dependency_of"
                ] = dependency_of

                derived_failures.append(
                    derived_item
                )

                continue

            root_item = dict(
                item
            )

            root_item[
                "failure_class"
            ] = "root"

            if dependency_of:
                root_item[
                    "expected_dependency_of"
                ] = dependency_of

                root_item[
                    "lineage_note"
                ] = (
                    "This contract is normally derived, but its upstream "
                    "root contract was not present in the current failure set."
                )

            root_failures.append(
                root_item
            )

        return root_failures, derived_failures

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
        # Separate dependency failures from governance failures.
        #
        # Dependency failures may constrain runtime readiness, but
        # they should not automatically become architecture or
        # governance blockers.
        #
        # Meta-contracts such as governance_verdict should also not
        # become root causes.
        # ----------------------------------------------------------
        #

        dependency_failures: List[Dict[str, Any]] = []
        governance_failures: List[Dict[str, Any]] = []

        relevant_failure_results: List[Any] = []

        for result in self.results:
            if result.severity in {
                "critical",
                "fail",
            }:
                relevant_failure_results.append(
                    result
                )

        dependency_contracts = {
            "dependency_reality",
            "import_reality",
            "runtime_import_reality",
        }

        for result in relevant_failure_results:
            contract_type = getattr(
                result,
                "contract_type",
                None,
            )

            #
            # Meta-contracts are verdicts, not root causes.
            #
            if contract_type in GOVERNANCE_META_CONTRACT_TYPES:
                continue

            item = {
                "domain":
                    result.domain,

                "check":
                    result.check,

                "severity":
                    result.severity,

                "status":
                    result.status,

                "summary":
                    result.summary,

                "governance_domain":
                    getattr(
                        result,
                        "governance_domain",
                        None,
                    ),

                "contract_type":
                    contract_type,
            }

            if contract_type in dependency_contracts:
                dependency_failures.append(
                    item
                )

            else:
                governance_failures.append(
                    item
                )

        #
        # ----------------------------------------------------------
        # Root / Derived Failure Classification
        # ----------------------------------------------------------
        #

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
        #
        # Runtime readiness is treated separately from governance.
        #
        # Missing runtime dependencies may constrain runtime and flow
        # audit, but should not automatically block architecture
        # governance.
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

        runtime_dependency_ready = (
            runtime_dependency_result is not None
            and runtime_dependency_result.status == "pass"
        )

        runtime_import_ready = (
            runtime_import_result is not None
            and runtime_import_result.status == "pass"
        )

        runtime_verdict = (
            "ready"
            if (
                runtime_dependency_ready
                and runtime_import_ready
            )
            else "blocked_by_dependency"
        )

        #
        # ----------------------------------------------------------
        # Deletion readiness
        #
        # Deletion is a governance gate.
        # It remains blocked until artifact coverage, hash integrity,
        # Type A usability, relationship audit, and runtime DB
        # readiness pass.
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
            if (
                deletion_result is not None
                and deletion_result.status == "pass"
            )
            else "blocked"
        )

        #
        # ----------------------------------------------------------
        # Artifact backbone
        #
        # The artifact backbone is a governance-relevant root domain.
        # Missing or unreadable artifact DBs should block downstream
        # artifact audit and deletion readiness.
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
            if (
                artifact_backbone_result is not None
                and artifact_backbone_result.status == "pass"
            )
            else "blocked"
        )

        #
        # ----------------------------------------------------------
        # Layer boundary audit
        #
        # Hint:
        #   not governance-blocking
        #
        # Suspicion:
        #   review-needed, but not governance-blocking
        #
        # Evidence:
        #   governance-blocking
        # ----------------------------------------------------------
        #

        layer_risk = self.governance_state.get(
            "layer_boundary_risk",
            {},
        )

        layer_evidence_count = int(
            layer_risk.get(
                "evidence_count",
                0,
            )
            or 0
        )

        layer_suspicion_count = int(
            layer_risk.get(
                "suspicion_count",
                0,
            )
            or 0
        )

        layer_boundary_verdict = (
            "blocked"
            if layer_evidence_count > 0
            else (
                "review_needed"
                if layer_suspicion_count > 0
                else "ready"
            )
        )

        #
        # ----------------------------------------------------------
        # MCP contract
        #
        # MCP readiness is evaluated separately from FastAPI/runtime
        # dependency readiness.
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
            if (
                mcp_result is not None
                and mcp_result.status == "pass"
            )
            else "partial_or_blocked"
        )

        #
        # ----------------------------------------------------------
        # Flow contracts
        #
        # Flow contracts may be skipped or partial when runtime
        # dependency/import readiness is incomplete.
        #
        # A skipped flow contract is not automatically a governance
        # blocker. It becomes runtime_limited because the auditor
        # could not complete flow checks due to runtime constraints.
        # ----------------------------------------------------------
        #

        flow_contract_result = next(
            (
                result
                for result in self.results
                if result.domain == "flow_contract_audit"
                and result.check == "flow_contract_compliance"
            ),
            None,
        )

        if (
            flow_contract_result is not None
            and flow_contract_result.status == "pass"
        ):
            flow_contract_verdict = "ready"

        elif (
            flow_contract_result is not None
            and flow_contract_result.status == "skipped"
        ):
            flow_contract_verdict = "runtime_limited"

        else:
            flow_contract_verdict = "partial_or_blocked"

        #
        # ----------------------------------------------------------
        # Architecture verdict
        #
        # IMPORTANT:
        #
        # Dependency failures do NOT automatically block architecture
        # governance.
        #
        # Architecture is blocked only by architecture-level contract
        # failures or evidence-level layer boundary violations.
        # ----------------------------------------------------------
        #

        architecture_failure_contracts = {
            "repository_discovery",
            "repository_runtime_alignment",
            "repository_import_runtime_separation",
            "package_layout",
            "package_identity",
            "package_root_resolution",
            "repository_shape",
            "runtime_metadata_contract",
            "flow_contract",
        }

        architecture_blockers = [
            item
            for item in governance_failures
            if item.get(
                "contract_type"
            )
            in architecture_failure_contracts
        ]

        #
        # Layer boundary only blocks architecture when evidence-level
        # violations exist.
        #

        if layer_boundary_verdict == "blocked":
            architecture_blockers.append(
                {
                    "domain":
                        "layer_separation",

                    "check":
                        "layer_boundary_audit",

                    "severity":
                        "critical",

                    "status":
                        "fail",

                    "summary": (
                        "Layer boundary audit found evidence-level "
                        "governance violations."
                    ),

                    "governance_domain":
                        "layer_boundaries",

                    "contract_type":
                        "layer_boundary",
                }
            )

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

        has_governance_blocker = any(
            verdict == "blocked"
            for verdict in [
                architecture_verdict,
                artifact_backbone_verdict,
                deletion_verdict,
            ]
        )

        requires_review = any(
            verdict == "review_needed"
            for verdict in [
                layer_boundary_verdict,
                flow_contract_verdict,
            ]
        )

        runtime_constrained = (
            runtime_verdict
            == "blocked_by_dependency"
        )

        if has_governance_blocker:
            governance_verdict = "blocked"

        elif requires_review:
            governance_verdict = "review_needed"

        elif runtime_constrained:
            governance_verdict = "runtime_limited"

        else:
            governance_verdict = "ready"

        #
        # ----------------------------------------------------------
        # Dynamic Impact Scope
        #
        # Impact scope is derived from the actual root/derived
        # lineage discovered during audit.
        # ----------------------------------------------------------
        #

        impact_scope: Dict[str, Any] = {}

        for root_failure in root_failures:

            root_contract = root_failure.get(
                "contract_type"
            )

            if not root_contract:
                continue

            impact_scope[root_contract] = {
                "directly_blocks": sorted(
                    [
                        item.get("contract_type")
                        for item in derived_failures
                        if item.get(
                            "dependency_of"
                        )
                        == root_contract
                    ]
                )
            }

        #
        # Governance-domain hints
        #

        if (
            "artifact_database_policy"
            in impact_scope
        ):
            impact_scope[
                "artifact_database_policy"
            ][
                "impact_domain"
            ] = (
                "artifact_backbone"
            )

        if (
            "deletion_readiness"
            in impact_scope
        ):
            impact_scope[
                "deletion_readiness"
            ][
                "impact_domain"
            ] = (
                "deletion_governance"
            )

        self.governance_state.update(
            {
                #
                # --------------------------------------------------
                # Top-Level Governance Verdicts
                # --------------------------------------------------
                #

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

                #
                # --------------------------------------------------
                # Failure Inventories
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
                # Failure Counts
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
                # Root Cause Summary
                # --------------------------------------------------
                #

                "root_cause_summary": {

                    "primary_root_contracts": [
                        item.get(
                            "contract_type"
                        )
                        for item in root_failures
                    ],

                    "derived_contracts": [
                        item.get(
                            "contract_type"
                        )
                        for item in derived_failures
                    ],

                    "derived_dependency_map": {
                        item.get(
                            "contract_type"
                        ):
                            item.get(
                                "dependency_of"
                            )
                        for item in derived_failures
                    },

                    "recommendation": (
                        "Resolve root failures first, "
                        "then re-run all derived "
                        "audit contracts."
                    ),
                },

                #
                # --------------------------------------------------
                # Impact Scope
                # --------------------------------------------------
                #

                "impact_scope": {

                    "root_contract_impacts":
                        impact_scope,

                    "impact_principle": (
                        "Impact scope describes governance domains "
                        "affected by a root contract failure. "
                        "It does not imply remediation."
                    ),

                    "generation_mode":
                        "runtime_lineage_driven",
                },

                #
                # --------------------------------------------------
                # Failure Lineage Policy
                # --------------------------------------------------
                #

                "lineage": {

                    "policy": {

                        "root_failure_contract_types":
                            sorted(
                                ROOT_FAILURE_CONTRACT_TYPES
                            ),

                        "derived_failure_policy":
                            DERIVED_FAILURE_POLICY,

                        "governance_meta_contract_types":
                            sorted(
                                GOVERNANCE_META_CONTRACT_TYPES
                            ),

                        "lineage_principle": (
                            "Root failures are independently actionable blockers. "
                            "Derived failures are downstream consequences and "
                            "should be re-evaluated after root resolution."
                        ),
                    },

                    "runtime_lineage": {

                        "root_contracts": [
                            item.get(
                                "contract_type"
                            )
                            for item in root_failures
                        ],

                        "derived_contracts": {
                            item.get(
                                "contract_type"
                            ):
                                item.get(
                                    "dependency_of"
                                )
                            for item in derived_failures
                        },
                    },
                },

                #
                # --------------------------------------------------
                # Governance Accounting
                # --------------------------------------------------
                #

                "blocking_reasons":
                    blocking_reasons,

                "warnings":
                    warnings,

                #
                # --------------------------------------------------
                # Governance Policy
                # --------------------------------------------------
                #

                "policy": {

                    "default_deletion":
                        "blocked",

                    "completed_phases":
                        "immutable",

                    "auditor_mode":
                        "read_only",

                    "dependency_failures_are_not_governance_failures":
                        True,

                    "root_failures_should_be_resolved_first":
                        True,

                    "derived_failures_should_be_revalidated_after_root_resolution":
                        True,

                    "false_positive_isolation":
                        True,

                    "maintenance_mode":
                        "advisor_only",
                },
            }
        )

        #
        # ----------------------------------------------------------
        # Governance Evidence Snapshot
        #
        # Keep meta-contracts such as governance_verdict out of
        # canonical blocking reasons to avoid circular explanations:
        #
        #   governance_verdict is blocked
        #   because governance_verdict is blocked
        #
        # Meta results remain available through Detailed Results.
        # ----------------------------------------------------------
        #

        filtered_blocking_reasons = [
            item
            for item in blocking_reasons
            if item.get("contract_type")
            not in GOVERNANCE_META_CONTRACT_TYPES
        ]

        impact_scope_evidence = (
            self.governance_state.get(
                "impact_scope",
                {},
            )
        )

        lineage_evidence = (
            self.governance_state.get(
                "lineage",
                {},
            )
        )

        policy_evidence = (
            self.governance_state.get(
                "policy",
                {},
            )
        )

        self.add(
            domain="governance",

            check="governance_verdict",

            status=(
                "pass"
                if governance_verdict == "ready"
                else (
                    "warning"
                    if governance_verdict in (
                        "review_needed",
                        "runtime_limited",
                    )
                    else "fail"
                )
            ),

            summary=(
                "RGA governance verdict is ready."
                if governance_verdict == "ready"
                else (
                    "RGA governance verdict requires review."
                    if governance_verdict == "review_needed"
                    else (
                        "RGA runtime readiness is limited by dependency or import reality."
                        if governance_verdict == "runtime_limited"
                        else "RGA governance verdict is blocked."
                    )
                )
            ),

            evidence={
                #
                # --------------------------------------------------
                # Top-Level Verdicts
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
                # Failure Classes
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
                # Failure Counts
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
                # Root Cause Summary
                #
                # Compact advisor / maintainer planning view.
                # --------------------------------------------------
                #

                "root_cause_summary": {
                    "primary_root_contracts": [
                        item.get(
                            "contract_type"
                        )
                        for item in root_failures
                    ],

                    "derived_contracts": [
                        item.get(
                            "contract_type"
                        )
                        for item in derived_failures
                    ],

                    "derived_dependency_map": {
                        item.get(
                            "contract_type"
                        ):
                            item.get(
                                "dependency_of"
                            )
                        for item in derived_failures
                    },
                },

                #
                # --------------------------------------------------
                # Recommended Action Order
                #
                # Advisory only.
                # This does not grant remediation or mutation authority.
                # --------------------------------------------------
                #

                "action_order": [
                    "resolve_root_failures",
                    "revalidate_derived_failures",
                    "recompute_governance_verdict",
                ],

                #
                # --------------------------------------------------
                # Governance Accounting
                # --------------------------------------------------
                #

                "blocking_reasons":
                    filtered_blocking_reasons,

                "blocking_reason_count":
                    len(
                        filtered_blocking_reasons
                    ),

                "raw_blocking_reasons":
                    blocking_reasons,

                "warnings":
                    warnings,

                "warning_count":
                    len(
                        warnings
                    ),

                #
                # --------------------------------------------------
                # Runtime / Governance Interpretation
                # --------------------------------------------------
                #

                "verdict_semantics": {
                    "ready": (
                        "No governance blockers or review-needed "
                        "conditions were detected."
                    ),

                    "runtime_limited": (
                        "Governance is not independently blocked, but "
                        "runtime readiness is constrained by dependency "
                        "or import reality."
                    ),

                    "review_needed": (
                        "No hard governance blocker was detected, but "
                        "one or more governance domains require review."
                    ),

                    "blocked": (
                        "One or more governance root contracts or hard "
                        "governance gates are blocked."
                    ),
                },

                #
                # --------------------------------------------------
                # Impact Scope
                #
                # Copied from governance_state so this result remains
                # self-contained.
                #
                # Advisory only. Does not imply remediation authority.
                # --------------------------------------------------
                #

                "impact_scope":
                    impact_scope_evidence,

                #
                # --------------------------------------------------
                # Failure Lineage
                #
                # Same shape as governance_state["lineage"].
                # Avoids maintaining a second lineage schema here.
                # --------------------------------------------------
                #

                "lineage":
                    lineage_evidence,

                #
                # --------------------------------------------------
                # Governance Policy
                # --------------------------------------------------
                #

                "policy":
                    policy_evidence,
            },

            suggested_fix=(
                None
                if governance_verdict == "ready"
                else (
                    "Resolve runtime dependency or import constraints, "
                    "then re-run runtime and flow audit. Governance "
                    "is not independently blocked by runtime-limited status."
                    if governance_verdict == "runtime_limited"
                    else (
                        "Review non-blocking governance warnings, especially "
                        "layer-boundary suspicions and partial flow contracts. "
                        "Do not mutate completed phases based on review-needed "
                        "signals alone."
                        if governance_verdict == "review_needed"
                        else (
                            "Resolve root governance blockers first. "
                            "Derived failures should be re-evaluated after "
                            "their upstream root contracts pass. Dependency "
                            "failures should remain separated from architecture "
                            "governance violations."
                        )
                    )
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
        self.check_hash_audit()
        self.check_type_A_usability()
        self.check_type_B_intelligence()
        self.check_runtime_db_read()
        self.check_deletion_readiness()

        self.check_flow_audit()
        self.check_flow_contract_audit()
        self.check_layer_separation()

        self.check_mcp_config()
        self.check_rest_contract()

        self.check_governance_verdict()

        counts: Dict[str, int] = {}
        severities: Dict[str, int] = {}

        for result in self.results:

            counts[result.status] = (
                counts.get(
                    result.status,
                    0,
                )
                + 1
            )

            severities[result.severity] = (
                severities.get(
                    result.severity,
                    0,
                )
                + 1
            )

        artifact_db_candidates = {
            db_name: [
                str(path)
                for path in paths
            ]
            for db_name, paths
            in self.resolve_all_artifact_db_candidates().items()
        }

        artifact_db_record_counts = {
            db_name:
                len(records)
            for db_name, records
            in self.iter_all_artifact_db_records().items()
        }

        report: Dict[str, Any] = {
            "schema":
                "rga.runtime_auditor.report.v1.0",

            "generated_at":
                datetime.now(
                    timezone.utc
                )
                .replace(
                    microsecond=0,
                )
                .isoformat(),

            "repo_root":
                str(
                    self.repo_root
                ),

            "backend_root":
                str(
                    self.backend_root
                ),

            "backend_root_mode":
                self.backend_root_mode,

            "backend_root_candidates": [
                asdict(candidate)
                for candidate in self.backend_candidates
            ],

            "discovered_files":
                self.discovered_files,

            "discovered_packages":
                self.discovered_packages,

            "discovered_assets":
                self.discovered_assets,

            "artifact_databases": {
                "required":
                    ARTIFACT_DATABASE_NAMES,

                "relationship_chain":
                    ARTIFACT_RELATIONSHIP_CHAIN,

                "candidates":
                    artifact_db_candidates,

                "record_counts":
                    artifact_db_record_counts,
            },

            "governance":
                self.governance_state,

            "api_url":
                self.api_url,

            "summary":
                counts,

            "severity_summary":
                severities,

            "result_count":
                len(
                    self.results
                ),

            "results": [
                asdict(result)
                for result in self.results
            ],
        }

        return report

def write_markdown(
    report: Dict[str, Any],
    out_path: Path,
) -> None:

    #
    # ----------------------------------------------------------
    # Defensive helpers
    #
    # Markdown rendering should never fail because a report
    # contains unexpected types.
    #
    # Keep rendering best-effort and preserve evidence.
    # ----------------------------------------------------------
    #

    def safe_str(
        value: Any,
    ) -> str:

        try:
            return str(value)

        except Exception as exc:
            return (
                f"<string_conversion_error:{exc}>"
            )

    def safe_dict(
        value: Any,
    ) -> Dict[str, Any]:

        if isinstance(
            value,
            dict,
        ):
            return value

        return {}

    def safe_json(
        value: Any,
    ) -> str:

        try:
            return json.dumps(
                value,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        except Exception as exc:

            return json.dumps(
                {
                    "markdown_render_error":
                        safe_str(exc)
                },
                indent=2,
                ensure_ascii=False,
            )

    lines: List[str] = []

    #
    # ----------------------------------------------------------
    # Report Header
    # ----------------------------------------------------------
    #

    lines.append(
        "# RGA Runtime Auditor Report"
    )

    lines.append("")

    audit_context = safe_dict(
        report.get(
            "audit_context",
            {},
        )
    )

    audit_mode = audit_context.get(
        "audit_mode",
        "pre_audit",
    )

    lines.append(
        f"Audit Mode: `{safe_str(audit_mode)}`"
    )

    lines.append(
        f"Schema: `{safe_str(report.get('schema'))}`"
    )

    lines.append(
        f"Generated: `{safe_str(report.get('generated_at'))}`"
    )

    lines.append(
        f"Repo root: `{safe_str(report.get('repo_root'))}`"
    )

    lines.append(
        f"Backend root: `{safe_str(report.get('backend_root'))}`"
    )

    lines.append(
        f"Backend root mode: "
        f"`{safe_str(report.get('backend_root_mode'))}`"
    )

    lines.append(
        f"API URL: `{safe_str(report.get('api_url'))}`"
    )

    lines.append("")

    #
    # ----------------------------------------------------------
    # Audit Context
    # ----------------------------------------------------------
    #

    lines.append(
        "## Audit Context"
    )

    lines.append("")

    lines.append(
        f"- Audit Mode: `{safe_str(audit_mode)}`"
    )

    execution_plan_path = (
        audit_context.get(
            "execution_plan_path"
        )
    )

    if execution_plan_path:

        lines.append(
            f"- Execution Plan: "
            f"`{safe_str(execution_plan_path)}`"
        )

    pre_audit_report_path = (
        audit_context.get(
            "pre_audit_report_path"
        )
    )

    if pre_audit_report_path:

        lines.append(
            f"- Pre-Audit Report: "
            f"`{safe_str(pre_audit_report_path)}`"
        )

    approval_authority = (
        audit_context.get(
            "approval_authority"
        )
    )

    if approval_authority:

        lines.append(
            f"- Approval Authority: "
            f"`{safe_str(approval_authority)}`"
        )

    lines.append("")

    bot_authority = safe_dict(
        report.get(
            "bot_authority",
            {},
        )
    )

    if bot_authority:

        lines.append(
            "### Bot #1 Authority Model"
        )

        lines.append("")

        authority_pairs = [
            ("Checker", "checker"),
            ("Validator", "validator"),
            ("Verifier", "verifier"),
            ("Auditor", "auditor"),
            ("Advisor", "advisor"),
            (
                "Maintainer Support",
                "maintainer_support",
            ),
            ("Governor", "governor"),
            ("Maintainer", "maintainer"),
            (
                "Execution Authority",
                "execution_authority",
            ),
        ]

        for label, key in authority_pairs:

            enabled = bool(
                bot_authority.get(
                    key,
                    False,
                )
            )

            lines.append(
                f"- {label}: "
                f"`{'enabled' if enabled else 'disabled'}`"
            )

        lines.append("")

    #
    # ----------------------------------------------------------
    # Report Generation
    # ----------------------------------------------------------
    #

    report_generation = safe_dict(
        report.get(
            "report_generation",
            {},
        )
    )

    if report_generation:

        lines.append(
            "## Report Generation"
        )

        lines.append("")

        generation_fields = [
            (
                "JSON generated",
                report_generation.get(
                    "json_generated"
                ),
            ),
            (
                "Markdown generated",
                report_generation.get(
                    "markdown_generated"
                ),
            ),
            (
                "Markdown fallback",
                report_generation.get(
                    "markdown_fallback_generated"
                ),
            ),
            (
                "JSON error",
                report_generation.get(
                    "json_error"
                ),
            ),
            (
                "Markdown error",
                report_generation.get(
                    "markdown_error"
                ),
            ),
            (
                "Auditor error",
                report_generation.get(
                    "auditor_error"
                ),
            ),
        ]

        for label, value in generation_fields:

            lines.append(
                f"- {label}: "
                f"`{safe_str(value)}`"
            )

        lines.append("")

    #
    # ----------------------------------------------------------
    # Audit Mode Details
    # ----------------------------------------------------------
    #

    if audit_mode == "plan_audit":

        plan_audit = safe_dict(
            report.get(
                "plan_audit",
                {},
            )
        )

        lines.append(
            "## Execution Plan Audit"
        )

        lines.append("")

        lines.append(
            safe_json(
                plan_audit
            )
        )

        lines.append("")

    elif audit_mode == "post_audit":

        post_audit = safe_dict(
            report.get(
                "post_audit",
                {},
            )
        )

        lines.append(
            "## Post Audit"
        )

        lines.append("")

        lines.append(
            safe_json(
                post_audit
            )
        )

        lines.append("")

    elif audit_mode == "pre_audit":

        pre_audit = safe_dict(
            report.get(
                "pre_audit",
                {},
            )
        )

        description = (
            pre_audit.get(
                "description"
            )
            or
            "Current repository, runtime, artifact, and governance state was audited."
        )

        lines.append(
            "## Pre-Audit"
        )

        lines.append("")

        lines.append(
            safe_str(
                description
            )
        )

        lines.append("")

    #
    # ----------------------------------------------------------
    # Governance Snapshot
    # ----------------------------------------------------------
    #

    governance = safe_dict(
        report.get(
            "governance",
            {},
        )
    )

    dependency_failures = governance.get(
        "dependency_failures",
        [],
    )

    governance_failures = governance.get(
        "governance_failures",
        [],
    )

    root_failures = governance.get(
        "root_failures",
        [],
    )

    derived_failures = governance.get(
        "derived_failures",
        [],
    )

    lines.append(
        "## Governance Overview"
    )

    lines.append("")

    governance_overview = [
        (
            "Governance verdict",
            governance.get(
                "governance_verdict"
            ),
        ),
        (
            "Architecture verdict",
            governance.get(
                "architecture_verdict"
            ),
        ),
        (
            "Runtime verdict",
            governance.get(
                "runtime_verdict"
            ),
        ),
        (
            "Artifact backbone verdict",
            governance.get(
                "artifact_backbone_verdict"
            ),
        ),
        (
            "Flow contract verdict",
            governance.get(
                "flow_contract_verdict"
            ),
        ),
        (
            "Layer boundary verdict",
            governance.get(
                "layer_boundary_verdict"
            ),
        ),
        (
            "MCP contract verdict",
            governance.get(
                "mcp_contract_verdict"
            ),
        ),
        (
            "Deletion verdict",
            governance.get(
                "deletion_verdict"
            ),
        ),
    ]

    if (
        governance.get(
            "governance_verdict"
        )
        == "runtime_limited"
    ):
        lines.append(
            "> Runtime readiness is constrained by "
            "dependency or import reality. "
            "This is not automatically a governance blocker."
        )
        lines.append("")

    for label, value in governance_overview:

        lines.append(
            f"- {label}: `{value}`"
        )

    lines.append("")

    #
    # ----------------------------------------------------------
    # Verdict Semantics
    # ----------------------------------------------------------
    #

    verdict_semantics = safe_dict(
        governance.get(
            "verdict_semantics",
            {},
        )
    )

    if verdict_semantics:

        lines.append(
            "### Verdict Semantics"
        )

        lines.append("")

        for verdict, description in (
            verdict_semantics.items()
        ):
            lines.append(
                f"- **{safe_str(verdict)}**: "
                f"{safe_str(description)}"
            )

        lines.append("")
        
    #
    # ----------------------------------------------------------
    # Audit Context
    # ----------------------------------------------------------
    #

    audit_context = report.get(
        "audit_context",
        {},
    )

    audit_mode = audit_context.get(
        "audit_mode",
        "pre_audit",
    )

    lines.append(
        "## Audit Context"
    )

    lines.append("")

    lines.append(
        f"- Audit Mode: `{audit_mode}`"
    )

    execution_plan_path = audit_context.get(
        "execution_plan_path",
    )

    if execution_plan_path:

        lines.append(
            f"- Execution Plan: "
            f"`{execution_plan_path}`"
        )

    pre_audit_report_path = audit_context.get(
        "pre_audit_report_path",
    )

    if pre_audit_report_path:

        lines.append(
            f"- Pre-Audit Report: "
            f"`{pre_audit_report_path}`"
        )

    approval_authority = audit_context.get(
        "approval_authority",
    )

    if approval_authority:

        lines.append(
            f"- Approval Authority: "
            f"`{approval_authority}`"
        )

    lines.append("")

    bot_authority = report.get(
        "bot_authority",
        {},
    )

    if bot_authority:

        lines.append(
            "### Bot #1 Authority Model"
        )

        lines.append("")

        authority_pairs = [
            ("Checker", "checker"),
            ("Validator", "validator"),
            ("Verifier", "verifier"),
            ("Auditor", "auditor"),
            ("Advisor", "advisor"),
            (
                "Maintainer Support",
                "maintainer_support",
            ),
            ("Governor", "governor"),
            ("Maintainer", "maintainer"),
        ]

        for label, key in authority_pairs:

            enabled = bool(
                bot_authority.get(
                    key,
                    False,
                )
            )

            lines.append(
                f"- {label}: "
                f"`{'enabled' if enabled else 'disabled'}`"
            )

        lines.append("")
        
    if audit_mode == "plan_audit":

        plan_audit = report.get(
            "plan_audit",
            {},
        )

        lines.append(
            "### Execution Plan Audit"
        )

        lines.append("")

        lines.append(
            f"- Verdict: "
            f"`{plan_audit.get('verdict')}`"
        )

        lines.append(
            f"- Plan Loaded: "
            f"`{plan_audit.get('plan_loaded')}`"
        )

        lines.append(
            f"- Rollback Declared: "
            f"`{plan_audit.get('rollback_declared')}`"
        )

        lines.append(
            f"- Proposed Changes: "
            f"`{plan_audit.get('proposed_change_count')}`"
        )

        lines.append("")

        issues = plan_audit.get(
            "issues",
            [],
        )

        if issues:

            lines.append(
                "#### Issues"
            )

            lines.append("")

            for item in issues:

                lines.append(
                    f"- {item}"
                )

            lines.append("")

        violations = plan_audit.get(
            "forbidden_scope_violations",
            [],
        )

        if violations:

            lines.append(
                "#### Policy Violations"
            )

            lines.append("")

            for item in violations:

                lines.append(
                    f"- {item}"
                )

            lines.append("")
            
    elif audit_mode == "post_audit":

        post_audit = report.get(
            "post_audit",
            {},
        )

        lines.append(
            "### Post Audit"
        )

        lines.append("")

        lines.append(
            f"- Verdict: "
            f"`{post_audit.get('verdict')}`"
        )

        lines.append(
            f"- Pre-Audit Loaded: "
            f"`{post_audit.get('pre_audit_report_loaded')}`"
        )

        lines.append(
            f"- Execution Plan Loaded: "
            f"`{post_audit.get('execution_plan_loaded')}`"
        )

        lines.append(
            f"- Deletion Policy OK: "
            f"`{post_audit.get('deletion_policy_ok')}`"
        )

        lines.append("")

        changed_verdicts = post_audit.get(
            "changed_verdicts",
            {},
        )

        if changed_verdicts:

            lines.append(
                "#### Verdict Changes"
            )

            lines.append("")

            for (
                verdict_name,
                change,
            ) in changed_verdicts.items():

                lines.append(
                    "- "
                    f"**{verdict_name}**: "
                    f"`{change.get('before')}` "
                    f"→ "
                    f"`{change.get('after')}`"
                )

            lines.append("")

        issues = post_audit.get(
            "issues",
            [],
        )

        if issues:

            lines.append(
                "#### Post-Audit Notes"
            )

            lines.append("")

            for item in issues:

                lines.append(
                    f"- {item}"
                )

            lines.append("")
            
    elif audit_mode == "pre_audit":

        pre_audit = report.get(
            "pre_audit",
            {},
        )

        description = pre_audit.get(
            "description",
        )

        if description:

            lines.append(
                "### Pre-Audit"
            )

            lines.append("")

            lines.append(
                description
            )

            lines.append("")

    #
    # ----------------------------------------------------------
    # Failure Accounting
    # ----------------------------------------------------------
    #

    dependency_fail_count = governance.get(
        "dependency_fail_count",
        0,
    )

    governance_fail_count = governance.get(
        "governance_fail_count",
        0,
    )

    root_failure_count = governance.get(
        "root_failure_count",
        0,
    )

    derived_failure_count = governance.get(
        "derived_failure_count",
        0,
    )

    blocking_reason_count = governance.get(
        "blocking_reason_count",
        0,
    )

    warning_count = governance.get(
        "warning_count",
        0,
    )

    lines.append(
        "## Failure Accounting"
    )

    lines.append("")

    lines.append(
        f"- Dependency failures: `{dependency_fail_count}`"
    )

    lines.append(
        f"- Governance failures: `{governance_fail_count}`"
    )

    lines.append(
        f"- Root failures: `{root_failure_count}`"
    )

    lines.append(
        f"- Derived failures: `{derived_failure_count}`"
    )

    lines.append(
        f"- Blocking reasons: `{blocking_reason_count}`"
    )

    lines.append(
        f"- Warnings: `{warning_count}`"
    )

    lines.append("")

    #
    # ----------------------------------------------------------
    # Root Cause Summary
    # ----------------------------------------------------------
    #

    root_cause_summary = governance.get(
        "root_cause_summary",
        {},
    )

    if root_cause_summary:

        lines.append(
            "## Root Cause Summary"
        )

        lines.append("")

        primary_root_contracts = (
            root_cause_summary.get(
                "primary_root_contracts",
                [],
            )
        )

        if primary_root_contracts:

            lines.append(
                "### Primary Root Contracts"
            )

            lines.append("")

            for item in (
                primary_root_contracts
            ):
                lines.append(
                    f"- `{item}`"
                )

            lines.append("")

        derived_contracts = (
            root_cause_summary.get(
                "derived_contracts",
                [],
            )
        )

        if derived_contracts:

            lines.append(
                "### Derived Contracts"
            )

            lines.append("")

            for item in (
                derived_contracts
            ):
                lines.append(
                    f"- `{item}`"
                )

            lines.append("")

        recommendation = (
            root_cause_summary.get(
                "recommendation"
            )
        )

        if recommendation:

            lines.append(
                "### Recommendation"
            )

            lines.append("")

            lines.append(
                recommendation
            )

            lines.append("")

    #
    # --------------------------------------------------
    # Layer Boundary Risk
    # --------------------------------------------------
    #

    risk = governance.get(
        "layer_boundary_risk",
        {},
    )

    if risk:

        lines.append(
            "## Layer Boundary Risk"
        )

        lines.append("")

        lines.append(
            f"- Highest confidence: "
            f"`{risk.get('highest_confidence')}`"
        )

        lines.append(
            f"- Hints: "
            f"`{risk.get('hint_count', 0)}`"
        )

        lines.append(
            f"- Suspicions: "
            f"`{risk.get('suspicion_count', 0)}`"
        )

        lines.append(
            f"- Evidence: "
            f"`{risk.get('evidence_count', 0)}`"
        )

        lines.append("")

        governance_interpretation = (
            risk.get(
                "governance_interpretation",
                {},
            )
        )

        if governance_interpretation:

            lines.append(
                "### Governance Interpretation"
            )

            lines.append("")

            for verdict, text in (
                governance_interpretation.items()
            ):

                lines.append(
                    f"- **{verdict}**: {text}"
                )

            lines.append("")

    #
    # --------------------------------------------------
    # Governance Policy
    # --------------------------------------------------
    #

    policy = governance.get(
        "policy",
        {},
    )

    if policy:

        lines.append(
            "## Governance Policy"
        )

        lines.append("")

        for key in sorted(
            policy.keys()
        ):

            lines.append(
                f"- **{key}**: "
                f"{policy[key]}"
            )

        lines.append("")

    #
    # --------------------------------------------------
    # Summary
    # --------------------------------------------------
    #

    lines.append(
        "## Summary"
    )

    lines.append("")

    for key, value in sorted(
        report.get(
            "summary",
            {},
        ).items()
    ):

        lines.append(
            f"- **{key}**: {value}"
        )

    lines.append("")

    #
    # --------------------------------------------------
    # Severity Summary
    # --------------------------------------------------
    #

    lines.append(
        "## Severity Summary"
    )

    lines.append("")

    for key, value in sorted(
        report.get(
            "severity_summary",
            {},
        ).items()
    ):

        lines.append(
            f"- **{key}**: {value}"
        )

    lines.append("")

    #
    # --------------------------------------------------
    # Artifact Backbone
    # --------------------------------------------------
    #

    artifact_databases = report.get(
        "artifact_databases",
        {},
    )

    record_counts = (
        artifact_databases.get(
            "record_counts",
            {},
        )
    )

    total_records = sum(
        value
        for value in record_counts.values()
        if isinstance(
            value,
            (int, float),
        )
    )

    artifact_snapshot = {

        "required_database_count":
            len(
                artifact_databases.get(
                    "required",
                    [],
                )
            ),

        "relationship_chain_count":
            len(
                artifact_databases.get(
                    "relationship_chain",
                    [],
                )
            ),

        "record_counts":
            record_counts,

        "total_records":
            total_records,
    }

    lines.append(
        "## Artifact Backbone Snapshot"
    )

    lines.append("")

    lines.append(
        f"- Required databases: "
        f"`{artifact_snapshot['required_database_count']}`"
    )

    lines.append(
        f"- Relationship chain entries: "
        f"`{artifact_snapshot['relationship_chain_count']}`"
    )

    lines.append(
        f"- Total records: "
        f"`{artifact_snapshot['total_records']}`"
    )

    lines.append("")

    lines.append("```json")

    lines.append(
        json.dumps(
            artifact_snapshot,
            indent=2,
            ensure_ascii=False,
        )
    )

    lines.append("```")
    lines.append("")

    #
    # --------------------------------------------------
    # Repository Discovery
    # --------------------------------------------------
    #

    lines.append(
        "## Repository Discovery"
    )

    lines.append("")

    backend_candidates = report.get(
        "backend_root_candidates",
        [],
    )

    discovered_files = report.get(
        "discovered_files",
        {},
    )

    discovered_packages = report.get(
        "discovered_packages",
        {},
    )

    lines.append(
        f"- Backend candidates: "
        f"`{len(backend_candidates)}`"
    )

    lines.append(
        f"- File groups discovered: "
        f"`{len(discovered_files)}`"
    )

    lines.append(
        f"- Package groups discovered: "
        f"`{len(discovered_packages)}`"
    )

    lines.append("")

    #
    # --------------------------------------------------
    # Backend Candidates
    # --------------------------------------------------
    #

    if backend_candidates:

        lines.append(
            "### Backend Candidates"
        )

        lines.append("")
        lines.append("```json")

        lines.append(
            json.dumps(
                backend_candidates,
                indent=2,
                ensure_ascii=False,
            )
        )

        lines.append("```")
        lines.append("")

    #
    # --------------------------------------------------
    # File Group Summary
    # --------------------------------------------------
    #

    file_group_summary = {}

    for group_name, value in (
        discovered_files.items()
    ):

        if isinstance(
            value,
            list,
        ):
            file_group_summary[group_name] = len(
                value
            )

        else:
            file_group_summary[group_name] = 0

    lines.append(
        "### Discovered File Groups"
    )

    lines.append("")

    if file_group_summary:

        for (
            group_name,
            count,
        ) in sorted(
            file_group_summary.items()
        ):

            lines.append(
                f"- **{group_name}**: "
                f"`{count}`"
            )

    else:

        lines.append(
            "- No repository file groups discovered."
        )

    lines.append("")
    lines.append("```json")

    lines.append(
        json.dumps(
            file_group_summary,
            indent=2,
            ensure_ascii=False,
        )
    )

    lines.append("```")
    lines.append("")

    #
    # --------------------------------------------------
    # Package Discovery
    # --------------------------------------------------
    #

    package_summary = {}

    for package_group, value in (
        discovered_packages.items()
    ):

        if isinstance(
            value,
            list,
        ):
            package_summary[
                package_group
            ] = len(value)

        elif isinstance(
            value,
            dict,
        ):
            package_summary[
                package_group
            ] = len(value)

        else:
            package_summary[
                package_group
            ] = 0

    lines.append(
        "### Package Discovery"
    )

    lines.append("")

    if package_summary:

        for (
            package_group,
            count,
        ) in sorted(
            package_summary.items()
        ):

            lines.append(
                f"- **{package_group}**: "
                f"`{count}`"
            )

    else:

        lines.append(
            "- No package groups discovered."
        )

    lines.append("")
    lines.append("```json")

    lines.append(
        json.dumps(
            package_summary,
            indent=2,
            ensure_ascii=False,
        )
    )

    lines.append("```")
    lines.append("")

    #
    # --------------------------------------------------
    # Repository Discovery Snapshot
    # --------------------------------------------------
    #

    repository_snapshot = {

        "backend_candidate_count":
            len(
                backend_candidates
            ),

        "file_group_count":
            len(
                discovered_files
            ),

        "package_group_count":
            len(
                discovered_packages
            ),

        "file_group_summary":
            file_group_summary,

        "package_group_summary":
            package_summary,
    }

    lines.append(
        "### Repository Discovery Snapshot"
    )

    lines.append("")

    lines.append("```json")

    lines.append(
        json.dumps(
            repository_snapshot,
            indent=2,
            ensure_ascii=False,
        )
    )

    lines.append("```")
    lines.append("")

    #
    # --------------------------------------------------
    # Asset Discovery
    # --------------------------------------------------
    #

    discovered_assets = report.get(
        "discovered_assets",
        {},
    )

    excluded_by_reason = (
        discovered_assets.get(
            "excluded_by_reason",
            {},
        )
    )

    asset_snapshot = {

        "type_A":
            len(
                discovered_assets.get(
                    "type_A",
                    [],
                )
            ),

        "type_B":
            len(
                discovered_assets.get(
                    "type_B",
                    [],
                )
            ),

        "excluded_candidate_count":
            discovered_assets.get(
                "excluded_candidate_count",
                0,
            ),

        "excluded_by_reason":
            excluded_by_reason,
    }

    lines.append(
        "## Asset Discovery"
    )

    lines.append("")

    if excluded_by_reason:

        lines.append(
            "### Excluded Asset Candidates"
        )

        lines.append("")

        for reason, count in sorted(
            excluded_by_reason.items()
        ):

            lines.append(
                f"- **{reason}**: {count}"
            )

        lines.append("")

    lines.append("```json")

    lines.append(
        json.dumps(
            asset_snapshot,
            indent=2,
            ensure_ascii=False,
        )
    )

    lines.append("```")
    lines.append("")
    
    #
    # --------------------------------------------------
    # Write Markdown Output
    # --------------------------------------------------
    #

    out_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    markdown_text = "\n".join(
        str(line)
        for line in lines
    )

    #
    # Safety guard
    #

    if not markdown_text.strip():

        markdown_text = "\n".join(
            [
                "# RGA Runtime Auditor Report",
                "",
                "## Empty Markdown Guard",
                "",
                (
                    "Markdown renderer produced no output. "
                    "Fallback content was generated."
                ),
                "",
            ]
        )

    out_path.write_text(
        markdown_text,
        encoding="utf-8",
    )

    #
    # Verify artifact exists
    #

    if (
        not out_path.exists()
        or out_path.stat().st_size == 0
    ):
        raise RuntimeError(
            (
                "Markdown report was not written "
                f"successfully: {out_path}"
            )
        )    

# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main() -> int:

    parser = argparse.ArgumentParser(
        "RGA Runtime Auditor"
    )

    parser.add_argument(
        "--repo-root",
        default=".",
        help=(
            "Repository root or backend root."
        ),
    )

    parser.add_argument(
        "--backend-root",
        default=None,
        help=(
            "Explicit backend root. "
            "Overrides repository discovery."
        ),
    )

    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8000/api/v1/recommend",
        help=(
            "RGA REST recommend endpoint."
        ),
    )

    parser.add_argument(
        "--token",
        default=None,
        help=(
            "Bearer token. Defaults to "
            "SOFTR_API_TOKEN environment variable."
        ),
    )

    parser.add_argument(
        "--mcp-config",
        default=None,
        help=(
            "Optional path to VS Code mcp.json."
        ),
    )

    #
    # ----------------------------------------------------------
    # Audit modes
    # ----------------------------------------------------------
    #

    parser.add_argument(
        "--audit-mode",
        choices=[
            "pre_audit",
            "plan_audit",
            "post_audit",
        ],
        default="pre_audit",
        help=(
            "Bot #1 audit mode."
        ),
    )

    parser.add_argument(
        "--execution-plan",
        default=None,
        help=(
            "Optional path to Bot #2 execution plan JSON."
        ),
    )

    parser.add_argument(
        "--pre-audit-report",
        default=None,
        help=(
            "Optional path to previous Bot #1 "
            "pre-audit report JSON."
        ),
    )

    #
    # ----------------------------------------------------------
    # Explicit artifact DB overrides
    # ----------------------------------------------------------
    #

    parser.add_argument(
        "--asset-db",
        default=None,
        help=(
            "Optional explicit path to chart_assets.db."
        ),
    )

    parser.add_argument(
        "--file-scan-inventory-db",
        default=None,
        help=(
            "Optional explicit path to "
            "file_scan_inventory.db."
        ),
    )

    parser.add_argument(
        "--chart-assets-db",
        default=None,
        help=(
            "Optional explicit path to "
            "chart_assets.db."
        ),
    )

    parser.add_argument(
        "--chart-patterns-db",
        default=None,
        help=(
            "Optional explicit path to "
            "chart_patterns.db."
        ),
    )

    #
    # ----------------------------------------------------------
    # Runtime checks
    # ----------------------------------------------------------
    #

    parser.add_argument(
        "--rest",
        action="store_true",
        help=(
            "Run REST endpoint audit."
        ),
    )

    #
    # ----------------------------------------------------------
    # Report outputs
    # ----------------------------------------------------------
    #

    parser.add_argument(
        "--json-out",
        default="artifacts/runtime_auditor_report.json",
        help=(
            "JSON report output path."
        ),
    )

    parser.add_argument(
        "--md-out",
        default="artifacts/runtime_auditor_report.md",
        help=(
            "Markdown report output path."
        ),
    )

    #
    # ----------------------------------------------------------
    # Strict modes
    # ----------------------------------------------------------
    #

    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Exit non-zero based on strict mode."
        ),
    )

    parser.add_argument(
        "--strict-severity",
        choices=[
            "fail",
            "critical",
        ],
        default="fail",
        help=(
            "Severity threshold used by --strict."
        ),
    )

    parser.add_argument(
        "--strict-governance",
        action="store_true",
        help=(
            "Exit non-zero only when governance "
            "verdict is blocked."
        ),
    )

    #
    # ----------------------------------------------------------
    # Parse args
    # ----------------------------------------------------------
    #

    args = parser.parse_args()

    #
    # ----------------------------------------------------------
    # Ensure artifacts directory exists
    # ----------------------------------------------------------
    #

    Path(
        "artifacts"
    ).mkdir(
        parents=True,
        exist_ok=True,
    )

    #
    # ----------------------------------------------------------
    # Optional path helper
    # ----------------------------------------------------------
    #

    def optional_path(
        value: Optional[str]
    ) -> Optional[Path]:

        if value is None:
            return None

        value_text = str(
            value
        ).strip()

        if not value_text:
            return None

        return Path(
            value_text
        ).expanduser()

    #
    # ----------------------------------------------------------
    # Output paths
    # ----------------------------------------------------------
    #

    json_out: Path = (
        optional_path(
            args.json_out
        )
        or Path(
            "artifacts/runtime_auditor_report.json"
        )
    )

    md_out: Path = (
        optional_path(
            args.md_out
        )
        or Path(
            "artifacts/runtime_auditor_report.md"
        )
    )

    json_out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    md_out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    execution_plan_path = optional_path(
        args.execution_plan
    )

    pre_audit_report_path = optional_path(
        args.pre_audit_report
    )

    #
    # ----------------------------------------------------------
    # Diagnostics
    # ----------------------------------------------------------
    #

    print(
        f"[Auditor] audit_mode={args.audit_mode}"
    )

    print(
        f"[Auditor] json_out={json_out}"
    )

    print(
        f"[Auditor] md_out={md_out}"
    )

    print(
        f"[Auditor] execution_plan={execution_plan_path}"
    )

    print(
        f"[Auditor] pre_audit_report={pre_audit_report_path}"
    )

    #
    # ----------------------------------------------------------
    # Local helpers
    # ----------------------------------------------------------
    #

    def safe_dict(
        value: Any,
    ) -> Dict[str, Any]:

        if isinstance(
            value,
            dict,
        ):
            return value

        return {}


    def read_json_optional(
        path: Optional[Path],
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:

        if path is None:
            return None, None

        try:

            if not path.exists():
                return (
                    None,
                    f"JSON file does not exist: {path}",
                )

            if not path.is_file():
                return (
                    None,
                    f"JSON path is not a file: {path}",
                )

            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )

            if not text.strip():
                return (
                    None,
                    f"JSON file is empty: {path}",
                )

            data = json.loads(
                text
            )

            if isinstance(
                data,
                dict,
            ):
                return data, None

            return (
                None,
                f"JSON file does not contain an object: {path}",
            )

        except Exception as exc:

            return (
                None,
                str(
                    exc
                ),
            )


    def unwrap_execution_plan(
        value: Optional[Dict[str, Any]],
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:

        metadata: Dict[str, Any] = {
            "input_loaded":
                value is not None,

            "input_shape":
                None,

            "unwrapped_from_executor_report":
                False,
        }

        if value is None:
            return None, metadata

        if not isinstance(
            value,
            dict,
        ):
            metadata[
                "input_shape"
            ] = str(
                type(
                    value
                )
            )

            return None, metadata

        metadata[
            "input_shape"
        ] = "dict"

        #
        # runtime_executor.py emits:
        #
        # {
        #   "schema": "rga.runtime_executor.report.v1.x",
        #   "plan": { ... execution plan ... },
        #   ...
        # }
        #
        # Bot #1 plan_audit should evaluate the nested plan.
        #

        nested_plan = value.get(
            "plan"
        )

        if isinstance(
            nested_plan,
            dict,
        ):
            metadata[
                "unwrapped_from_executor_report"
            ] = True

            metadata[
                "executor_report_schema"
            ] = value.get(
                "schema"
            )

            metadata[
                "executor_mode"
            ] = value.get(
                "mode"
            )

            metadata[
                "executor_policy_result"
            ] = (
                value.get(
                    "diagnostics",
                    {},
                )
                .get(
                    "policy_result",
                    {}
                )
                if isinstance(
                    value.get(
                        "diagnostics",
                        {},
                    ),
                    dict,
                )
                else {}
            )

            return nested_plan, metadata

        #
        # Otherwise assume the file itself is the execution plan.
        #

        return value, metadata


    def append_cli_result(
        report: Dict[str, Any],
        *,
        domain: str,
        check: str,
        status: str,
        severity: str,
        summary: str,
        evidence: Dict[str, Any],
        suggested_fix: Optional[str] = None,
        governance_domain: Optional[str] = None,
        contract_type: Optional[str] = None,
    ) -> None:

        results = report.setdefault(
            "results",
            [],
        )

        if not isinstance(
            results,
            list,
        ):
            report[
                "results"
            ] = []

            results = report[
                "results"
            ]

        results.append(
            {
                "domain":
                    domain,

                "check":
                    check,

                "status":
                    status,

                "severity":
                    severity,

                "summary":
                    summary,

                "evidence":
                    evidence,

                "suggested_fix":
                    suggested_fix,

                "governance_domain":
                    governance_domain,

                "contract_type":
                    contract_type,
            }
        )


    def recalculate_report_counts(
        report: Dict[str, Any],
    ) -> None:

        counts: Dict[str, int] = {}
        severities: Dict[str, int] = {}

        results = report.get(
            "results",
            [],
        )

        if not isinstance(
            results,
            list,
        ):
            results = []

        for result in results:

            if not isinstance(
                result,
                dict,
            ):
                continue

            status = result.get(
                "status",
                "unknown",
            )

            severity = result.get(
                "severity",
                "unknown",
            )

            counts[
                status
            ] = (
                counts.get(
                    status,
                    0,
                )
                + 1
            )

            severities[
                severity
            ] = (
                severities.get(
                    severity,
                    0,
                )
                + 1
            )

        report[
            "summary"
        ] = counts

        report[
            "severity_summary"
        ] = severities

        report[
            "result_count"
        ] = len(
            results
        )


    def evaluate_execution_plan(
        plan: Optional[Dict[str, Any]],
        plan_error: Optional[str],
    ) -> Dict[str, Any]:

        unwrapped_plan, unwrap_metadata = unwrap_execution_plan(
            plan
        )

        forbidden_tokens = [
            "canonical_row",
            "tips generation",
            "tips_generation",
            "pattern_logic",
            "personalization",
            "localization",
            "recommendation logic",
            "recommendation_logic",
            "source_asset_deletion",
            "delete source",
            "database mutation",
            "db mutation",
            "override_governance",
            "approve_execution",
        ]

        issues: List[str] = []
        policy_violations: List[str] = []

        if plan_error:
            issues.append(
                f"Execution plan could not be loaded: {plan_error}"
            )

        if unwrapped_plan is None:

            return {
                "audit_mode":
                    "plan_audit",

                "plan_loaded":
                    False,

                "plan_unwrap_metadata":
                    unwrap_metadata,

                "verdict":
                    "needs_revision",

                "status":
                    "warning",

                "severity":
                    "warning",

                "issues":
                    issues
                    or [
                        "No execution plan was provided."
                    ],

                "forbidden_scope_violations":
                    policy_violations,

                "authority_note":
                    (
                        "Bot #1 may evaluate plans but must not "
                        "approve, execute, merge, or mutate."
                    ),
            }

        proposed_changes = unwrapped_plan.get(
            "proposed_changes",
            [],
        )

        target_root_failures = unwrapped_plan.get(
            "target_root_failures",
            [],
        )

        forbidden_declared_absent = unwrapped_plan.get(
            "forbidden_changes_declared_absent",
            {},
        )

        rollback = unwrapped_plan.get(
            "rollback",
            {},
        )

        audit_steps = unwrapped_plan.get(
            "audit_steps",
            [],
        )

        human_approval_required = unwrapped_plan.get(
            "human_approval_required",
            None,
        )

        plan_schema = unwrapped_plan.get(
            "schema"
        )

        plan_mode = unwrapped_plan.get(
            "mode"
        )

        try:

            plan_text = json.dumps(
                unwrapped_plan,
                ensure_ascii=False,
                default=str,
            ).lower()

        except Exception:

            plan_text = str(
                unwrapped_plan
            ).lower()

        #
        # Forbidden scope detection.
        #
        # If the token appears only inside
        # forbidden_changes_declared_absent with value True,
        # this is expected and should not be treated as a violation.
        #

        for token in forbidden_tokens:

            if token.lower() not in plan_text:
                continue

            declared_safe = False

            if isinstance(
                forbidden_declared_absent,
                dict,
            ):

                normalized_token = token.replace(
                    " ",
                    "_",
                ).lower()

                for key, value in forbidden_declared_absent.items():

                    if (
                        normalized_token
                        in str(
                            key
                        ).lower()
                        and value is True
                    ):
                        declared_safe = True
                        break

            if not declared_safe:

                policy_violations.append(
                    f"Potential forbidden scope reference: {token}"
                )

        #
        # Required contract checks.
        #

        if not target_root_failures:

            issues.append(
                "Execution plan does not declare target_root_failures."
            )

        if not isinstance(
            proposed_changes,
            list,
        ):

            issues.append(
                "Execution plan proposed_changes must be a list."
            )

        elif not proposed_changes:

            issues.append(
                "Execution plan does not declare proposed_changes."
            )

        if not rollback or not isinstance(
            rollback,
            dict,
        ):

            issues.append(
                "Execution plan does not declare rollback."
            )

        elif rollback.get(
            "available",
            False,
        ) is not True:

            issues.append(
                "Execution plan does not declare an available rollback path."
            )

        if not isinstance(
            audit_steps,
            list,
        ):

            issues.append(
                "Execution plan audit_steps must be a list."
            )

        elif not audit_steps:

            issues.append(
                "Execution plan does not declare audit_steps."
            )

        if human_approval_required is not True:

            issues.append(
                "Execution plan must require human approval."
            )

        #
        # Change-level inspection.
        #

        executable_change_count = 0
        disallowed_mutation_levels: List[str] = []

        if isinstance(
            proposed_changes,
            list,
        ):

            for change in proposed_changes:

                if not isinstance(
                    change,
                    dict,
                ):
                    issues.append(
                        "Execution plan contains a non-object proposed change."
                    )
                    continue

                mutation_level = change.get(
                    "mutation_level"
                )

                if mutation_level in {
                    "execute_allowed",
                    "dry_run_only",
                    "proposal_only",
                }:

                    if mutation_level == "execute_allowed":
                        executable_change_count += 1

                else:

                    disallowed_mutation_levels.append(
                        str(
                            mutation_level
                        )
                    )

                if change.get(
                    "requires_human_approval"
                ) is not True:

                    issues.append(
                        (
                            f"Change {change.get('change_id')} "
                            "does not require human approval."
                        )
                    )

        if disallowed_mutation_levels:

            policy_violations.append(
                (
                    "Execution plan contains disallowed mutation levels: "
                    + ", ".join(
                        sorted(
                            set(
                                disallowed_mutation_levels
                            )
                        )
                    )
                )
            )

        #
        # Verdict.
        #

        if policy_violations:

            verdict = "rejected_by_policy"
            severity = "critical"
            status = "fail"

        elif issues:

            verdict = "needs_revision"
            severity = "warning"
            status = "warning"

        else:

            verdict = "approved_for_human_review"
            severity = "info"
            status = "pass"

        return {
            "audit_mode":
                "plan_audit",

            "plan_loaded":
                True,

            "plan_unwrap_metadata":
                unwrap_metadata,

            "schema":
                plan_schema,

            "mode":
                plan_mode,

            "target_root_failures":
                target_root_failures,

            "proposed_change_count":
                (
                    len(
                        proposed_changes
                    )
                    if isinstance(
                        proposed_changes,
                        list,
                    )
                    else 0
                ),

            "executable_change_count":
                executable_change_count,

            "forbidden_scope_violations":
                policy_violations,

            "issues":
                issues,

            "rollback_declared":
                bool(
                    rollback
                    and isinstance(
                        rollback,
                        dict,
                    )
                    and rollback.get(
                        "available",
                        False,
                    )
                ),

            "audit_step_count":
                (
                    len(
                        audit_steps
                    )
                    if isinstance(
                        audit_steps,
                        list,
                    )
                    else 0
                ),

            "human_approval_required":
                human_approval_required,

            "verdict":
                verdict,

            "status":
                status,

            "severity":
                severity,

            "authority_note":
                (
                    "Bot #1 may evaluate plans but must not "
                    "approve, execute, merge, or mutate."
                ),
        }


    def evaluate_post_audit(
        report: Dict[str, Any],
        pre_report: Optional[Dict[str, Any]],
        pre_report_error: Optional[str],
        plan: Optional[Dict[str, Any]],
        plan_error: Optional[str],
    ) -> Dict[str, Any]:

        unwrapped_plan, unwrap_metadata = unwrap_execution_plan(
            plan
        )

        current_governance = safe_dict(
            report.get(
                "governance",
                {},
            )
        )

        previous_governance = (
            safe_dict(
                pre_report.get(
                    "governance",
                    {},
                )
            )
            if isinstance(
                pre_report,
                dict,
            )
            else {}
        )

        verdict_keys = [
            "governance_verdict",
            "architecture_verdict",
            "runtime_verdict",
            "artifact_backbone_verdict",
            "flow_contract_verdict",
            "layer_boundary_verdict",
            "mcp_contract_verdict",
            "deletion_verdict",
        ]

        current_verdicts = {
            key:
                current_governance.get(
                    key
                )
            for key in verdict_keys
        }

        previous_verdicts = {
            key:
                previous_governance.get(
                    key
                )
            for key in verdict_keys
        }

        changed_verdicts = {
            key: {
                "before":
                    previous_verdicts.get(
                        key
                    ),

                "after":
                    current_verdicts.get(
                        key
                    ),
            }
            for key in verdict_keys
            if previous_verdicts.get(
                key
            )
            != current_verdicts.get(
                key
            )
        }

        issues: List[str] = []

        if pre_report_error:

            issues.append(
                f"Pre-audit report could not be loaded: {pre_report_error}"
            )

        if pre_report is None:

            issues.append(
                "No pre-audit report was provided for comparison."
            )

        if plan_error:

            issues.append(
                f"Execution plan could not be loaded: {plan_error}"
            )

        if unwrapped_plan is None:

            issues.append(
                "No execution plan was available for post-audit comparison."
            )

        #
        # Deletion safety:
        #
        # deletion_verdict may only be ready when overall governance is ready.
        #

        deletion_verdict = current_governance.get(
            "deletion_verdict"
        )

        governance_verdict = current_governance.get(
            "governance_verdict"
        )

        deletion_policy_ok = (
            deletion_verdict != "ready"
            or governance_verdict == "ready"
        )

        if not deletion_policy_ok:

            issues.append(
                "Deletion verdict is ready while overall governance is not ready."
            )

        #
        # Plan outcome summary.
        #

        target_root_failures = []

        if isinstance(
            unwrapped_plan,
            dict,
        ):

            target_root_failures = unwrapped_plan.get(
                "target_root_failures",
                [],
            )

        #
        # Verdict.
        #

        if not deletion_policy_ok:

            verdict = "rejected_by_policy"
            status = "fail"
            severity = "critical"

        elif issues:

            verdict = "post_audit_complete_with_limitations"
            status = "warning"
            severity = "warning"

        else:

            verdict = "post_audit_complete"
            status = "pass"
            severity = "info"

        return {
            "audit_mode":
                "post_audit",

            "pre_audit_report_loaded":
                pre_report is not None,

            "execution_plan_loaded":
                unwrapped_plan is not None,

            "plan_unwrap_metadata":
                unwrap_metadata,

            "target_root_failures":
                target_root_failures,

            "current_verdicts":
                current_verdicts,

            "previous_verdicts":
                previous_verdicts,

            "changed_verdicts":
                changed_verdicts,

            "issues":
                issues,

            "deletion_policy_ok":
                deletion_policy_ok,

            "verdict":
                verdict,

            "status":
                status,

            "severity":
                severity,

            "authority_note":
                (
                    "Bot #1 post-audit verifies outcome only and "
                    "does not approve, execute, merge, or mutate."
                ),
        }

    #
    # ----------------------------------------------------------
    # Report generation state
    #
    # This is initialized before auditor execution so fallback
    # reports can still be generated if RuntimeAuditor or run_all
    # fails before normal report creation completes.
    # ----------------------------------------------------------
    #

    generated_reports: Dict[str, Any] = {
        "json_report":
            str(
                json_out
            )
            if json_out
            else None,

        "markdown_report":
            str(
                md_out
            )
            if md_out
            else None,

        "json_requested":
            json_out is not None,

        "markdown_requested":
            md_out is not None,

        "json_generated":
            False,

        "markdown_generated":
            False,

        "markdown_fallback_generated":
            False,

        "json_error":
            None,

        "markdown_error":
            None,

        "auditor_error":
            None,

        "auditor_exception_traceback":
            None,
    }

    auditor_execution_failed = False

    #
    # ----------------------------------------------------------
    # Run auditor
    #
    # If auditor execution crashes, still generate a structured
    # fallback report so workflow artifacts are not missing.
    # ----------------------------------------------------------
    #

    try:
        auditor = RuntimeAuditor(
            repo_root=Path(
                args.repo_root
            ),

            backend_root=(
                Path(
                    args.backend_root
                )
                if args.backend_root
                else None
            ),

            api_url=args.api_url,

            token=args.token,

            mcp_config=(
                Path(
                    args.mcp_config
                ).expanduser()
                if args.mcp_config
                else None
            ),

            asset_db=(
                Path(
                    args.asset_db
                ).expanduser()
                if args.asset_db
                else None
            ),

            file_scan_inventory_db=(
                Path(
                    args.file_scan_inventory_db
                ).expanduser()
                if args.file_scan_inventory_db
                else None
            ),

            chart_assets_db=(
                Path(
                    args.chart_assets_db
                ).expanduser()
                if args.chart_assets_db
                else None
            ),

            chart_patterns_db=(
                Path(
                    args.chart_patterns_db
                ).expanduser()
                if args.chart_patterns_db
                else None
            ),

            run_rest=args.rest,
        )

        report: Dict[str, Any] = auditor.run_all()

    except Exception as exc:
        import traceback

        auditor_execution_failed = True

        generated_reports["auditor_error"] = str(
            exc
        )

        generated_reports["auditor_exception_traceback"] = (
            traceback.format_exc()
        )

        report = {
            "schema":
                "rga.runtime_auditor.report.v1.0",

            "generated_at":
                datetime.now(
                    timezone.utc
                )
                .replace(
                    microsecond=0,
                )
                .isoformat(),

            "execution_state":
                "auditor_exception",

            "repo_root":
                str(
                    Path(
                        args.repo_root
                    )
                ),

            "backend_root":
                (
                    str(
                        Path(
                            args.backend_root
                        )
                    )
                    if args.backend_root
                    else None
                ),

            "backend_root_mode":
                "unavailable",

            "api_url":
                args.api_url,

            "summary": {
                "fail":
                    1,
            },

            "severity_summary": {
                "critical":
                    1,
            },

            "governance": {
                "governance_verdict":
                    "blocked",

                "runtime_verdict":
                    "blocked_by_exception",

                "policy": {
                    "auditor_mode":
                        "read_only",

                    "completed_phases":
                        "immutable",

                    "dependency_failures_are_not_governance_failures":
                        True,

                    "fallback_report_does_not_modify_logic":
                        True,
                },
            },

            "results": [
                {
                    "domain":
                        "runtime_auditor",

                    "check":
                        "auditor_execution",

                    "status":
                        "fail",

                    "severity":
                        "critical",

                    "summary": (
                        "Runtime auditor raised an unhandled "
                        "exception before normal report generation "
                        "completed."
                    ),

                    "evidence": {
                        "exception":
                            str(
                                exc
                            ),

                        "traceback":
                            generated_reports[
                                "auditor_exception_traceback"
                            ],
                    },

                    "suggested_fix": (
                        "Inspect runtime_auditor_stderr.txt and "
                        "runtime_auditor_stdout.txt to locate the "
                        "exception or early termination before normal "
                        "report generation."
                    ),

                    "governance_domain":
                        "auditor_runtime",

                    "contract_type":
                        "auditor_execution",
                }
            ],
        }

    #
    # ----------------------------------------------------------
    # Attach audit context
    # ----------------------------------------------------------
    #

    report.setdefault(
        "bot_authority",
        {}
    )

    report["bot_authority"].update(
        {
            "bot":
                "rga_backend_bot_1",

            "role":
                "pre_audit_plan_audit_post_audit",

            "checker":
                True,

            "validator":
                True,

            "verifier":
                True,

            "auditor":
                True,

            "advisor":
                True,

            "maintainer_support":
                True,

            "governor":
                False,

            "maintainer":
                False,

            "execution_authority":
                False,
        }
    )

    report.setdefault(
        "audit_context",
        {}
    )

    report["audit_context"].update(
        {
            "audit_mode":
                args.audit_mode,

            "execution_plan_path":
                str(
                    execution_plan_path
                )
                if execution_plan_path
                else None,

            "pre_audit_report_path":
                str(
                    pre_audit_report_path
                )
                if pre_audit_report_path
                else None,

            "approval_authority":
                "human",

            "bot_1_may_execute":
                False,

            "bot_1_may_approve":
                False,
        }
    )

    execution_plan, execution_plan_error = read_json_optional(
        execution_plan_path
    )

    pre_audit_report, pre_audit_report_error = read_json_optional(
        pre_audit_report_path
    )

    #
    # ----------------------------------------------------------
    # Audit mode evaluation
    # ----------------------------------------------------------
    #

    if args.audit_mode == "plan_audit":
        plan_audit = evaluate_execution_plan(
            execution_plan,
            execution_plan_error,
        )

        report["plan_audit"] = plan_audit

        append_cli_result(
            report,
            domain="bot_1_plan_audit",
            check="execution_plan_policy_review",
            status=plan_audit["status"],
            severity=plan_audit["severity"],
            summary=(
                "Bot #1 evaluated the Bot #2 execution plan."
            ),
            evidence=plan_audit,
            suggested_fix=(
                "Revise the execution plan before requesting human approval."
                if plan_audit["verdict"]
                in {
                    "needs_revision",
                    "rejected_by_policy",
                }
                else None
            ),
            governance_domain="execution_plan_governance",
            contract_type="execution_plan_audit",
        )

    elif args.audit_mode == "post_audit":
        post_audit = evaluate_post_audit(
            report,
            pre_audit_report,
            pre_audit_report_error,
            execution_plan,
            execution_plan_error,
        )

        report["post_audit"] = post_audit

        append_cli_result(
            report,
            domain="bot_1_post_audit",
            check="post_execution_audit",
            status=post_audit["status"],
            severity=post_audit["severity"],
            summary=(
                "Bot #1 evaluated the current state after proposed or applied execution."
            ),
            evidence=post_audit,
            suggested_fix=(
                "Review post-audit limitations before approving or continuing execution."
                if post_audit["status"] != "pass"
                else None
            ),
            governance_domain="post_execution_governance",
            contract_type="post_audit",
        )

    else:
        report["pre_audit"] = {
            "audit_mode":
                "pre_audit",

            "description":
                "Current repository, runtime, artifact, and governance state was audited.",

            "bot_1_may_execute":
                False,

            "bot_1_may_approve":
                False,
        }

    recalculate_report_counts(
        report
    )

    #
    # ----------------------------------------------------------
    # Report Generation Bootstrap
    # ----------------------------------------------------------
    #

    if not isinstance(
        report,
        dict,
    ):
        report = {
            "schema":
                "rga.runtime_auditor_report.v1.3",

            "report_error":
                "Auditor generated a non-dictionary report.",

            "report_type":
                str(
                    type(
                        report
                    )
                ),
        }

    generated_reports: Dict[
        str,
        Any,
    ] = {
        "markdown_generated":
            False,

        "markdown_fallback_generated":
            False,

        "json_generated":
            False,
    }

    report.setdefault(
        "report_generation",
        {},
    )

    report[
        "report_generation"
    ].update(
        generated_reports
    )

    #
    # ----------------------------------------------------------
    # Markdown Report
    # ----------------------------------------------------------
    #

    if md_out is not None:

        try:

            md_out.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            write_markdown(
                report,
                md_out,
            )
            
            if (
                not md_out.exists()
                or md_out.stat().st_size == 0
            ):
                raise RuntimeError(
                    (
                        "Markdown renderer returned successfully "
                        "but produced no non-empty markdown file."
                    )
                )            

            generated_reports[
                "markdown_generated"
            ] = True

        except Exception as exc:

            import traceback

            generated_reports[
                "markdown_error"
            ] = str(
                exc
            )

            try:

                md_out.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                fallback_lines = [

                    "# RGA Runtime Auditor Report",

                    "",

                    "## Fallback Report Generated",

                    "",

                    (
                        "The primary Markdown renderer failed. "
                        "A diagnostic fallback report was generated."
                    ),

                    "",

                    "## Error",

                    "",

                    "```text",

                    str(
                        exc
                    ),

                    "```",

                    "",

                    "## Traceback",

                    "",

                    "```text",

                    traceback.format_exc(),

                    "```",

                    "",

                    "## Governance Note",

                    "",

                    (
                        "- Fallback generation preserves evidence only."
                    ),

                    (
                        "- No auditor logic was modified."
                    ),

                    (
                        "- Completed phases remain immutable."
                    ),
                ]

                md_out.write_text(
                    "\n".join(
                        fallback_lines
                    ),
                    encoding="utf-8",
                )

                generated_reports[
                    "markdown_generated"
                ] = True

                generated_reports[
                    "markdown_fallback_generated"
                ] = True

            except Exception as fallback_exc:

                generated_reports[
                    "markdown_generated"
                ] = False

                generated_reports[
                    "markdown_error"
                ] = (
                    f"{exc}; "
                    f"fallback_failed={fallback_exc}"
                )

    #
    # ----------------------------------------------------------
    # Finalize metadata before JSON serialization
    # ----------------------------------------------------------
    #

    report[
        "report_generation"
    ].update(
        generated_reports
    )

    #
    # ----------------------------------------------------------
    # JSON Report
    # ----------------------------------------------------------
    #

    if json_out is not None:

        try:

            json_out.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            generated_reports[
                "json_generated"
            ] = True

            report[
                "report_generation"
            ].update(
                generated_reports
            )

            json_text = json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
            )

            json_out.write_text(
                json_text,
                encoding="utf-8",
            )

        except Exception as exc:

            generated_reports[
                "json_generated"
            ] = False

            generated_reports[
                "json_error"
            ] = str(
                exc
            )

            report[
                "report_generation"
            ].update(
                generated_reports
            )

            print(
                "\n[Auditor] JSON artifact generation failed:\n"
            )

            print(
                str(
                    exc
                )
            )

            print(
                json.dumps(
                    report,
                    indent=2,
                    ensure_ascii=False,
                )
            )

            return 1

    #
    # ----------------------------------------------------------
    # Emit final auditor report
    # ----------------------------------------------------------
    #

    report[
        "report_generation"
    ].update(
        generated_reports
    )

    print(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
    )

    #
    # ----------------------------------------------------------
    # Governance-aware strict mode
    # ----------------------------------------------------------
    #

    if args.strict_governance:

        governance_verdict = (
            report.get(
                "governance",
                {},
            ).get(
                "governance_verdict"
            )
        )

        if governance_verdict == "blocked":
            return 1

    #
    # ----------------------------------------------------------
    # Severity strict mode
    # ----------------------------------------------------------
    #

    if args.strict:

        severity_summary = (
            report.get(
                "severity_summary",
                {},
            )
        )

        if (
            args.strict_severity
            == "critical"
        ):

            if (
                severity_summary.get(
                    "critical",
                    0,
                )
                > 0
            ):
                return 1

        elif (
            args.strict_severity
            == "fail"
        ):

            if (
                severity_summary.get(
                    "fail",
                    0,
                )
                > 0
                or
                severity_summary.get(
                    "critical",
                    0,
                )
                > 0
            ):
                return 1

    #
    # ----------------------------------------------------------
    # Auditor runtime failure
    # ----------------------------------------------------------
    #

    if auditor_execution_failed:

        print(
            "[Auditor] execution completed with runtime failures."
        )

        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )