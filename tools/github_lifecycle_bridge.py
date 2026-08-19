from __future__ import annotations

"""
GitHub Lifecycle Bridge for RGA.

Purpose
-------
Bridge the local Path A maintenance result into the online lifecycle:

    Run_UpdateRuntimeDbs.ps1
        -> artifacts/runtime_baseline.json
        -> GitHub Contents API commit / PR / workflow_dispatch
        -> RGA Lifecycle Runner

This script is intentionally additive and non-destructive:
- It does not modify Completed Phases 1-7.
- It does not mutate runtime databases.
- It commits only governance evidence by default.
- It targets a branch, not main, by default.
- It can optionally create a PR.
- It can optionally dispatch the lifecycle workflow.
- It can optionally poll lifecycle completion state.

Supported actions
-----------------
--dry-run
    Validate baseline and write request/report only.

--dispatch
    Trigger RGA Lifecycle Runner only.

--commit-baseline
    Commit artifacts/runtime_baseline.json to a GitHub branch.

--commit-and-dispatch
    Commit artifacts/runtime_baseline.json to runtime-baseline/update-*,
    then dispatch RGA Lifecycle Runner with:

        operator_action = start_lifecycle
        audit_session_id = <generated session>
        ref = runtime-baseline/update-*

--create-pr
    Create PR after committing baseline branch.

--poll-completion
    Write/receive local lifecycle completion signal.

Authentication Model
--------------------

Primary model:

    Local PowerShell
        ↓
    github_lifecycle_bridge.py
        ↓
    GitHub App credentials
        ↓
    GitHub App JWT
        ↓
    Installation token
        ↓
    GitHub REST API

Required local environment variables for GitHub App mode:

    RGA_APP_ID
    RGA_APP_INSTALLATION_ID
    RGA_APP_PRIVATE_KEY

RGA_APP_PRIVATE_KEY may be supplied as:
- raw PEM text
- PEM text with literal \\n escapes
- base64-encoded PEM text

Legacy fallback token environments remain supported only when
--auth-mode token or --auth-mode auto is used:

    RGA_ACCESS
    GITHUB_APP_TOKEN
    PAT_TOKEN
    GH_TOKEN
    GITHUB_TOKEN

Recommended local usage
-----------------------

Dry-run first:

    python .\\tools\\github_lifecycle_bridge.py `
        --owner YoshiHK `
        --repo Rhythm-Game-Assistant `
        --workflow "RGA Lifecycle Runner.yml" `
        --ref main `
        --baseline .\\artifacts\\runtime_baseline.json `
        --audit-mode pre_audit `
        --dry-run

Commit baseline to a branch:

    python .\\tools\\github_lifecycle_bridge.py `
        --owner YoshiHK `
        --repo Rhythm-Game-Assistant `
        --baseline .\\artifacts\\runtime_baseline.json `
        --commit-baseline

Commit baseline, open PR, and dispatch lifecycle:

    python .\\tools\\github_lifecycle_bridge.py `
        --owner YoshiHK `
        --repo Rhythm-Game-Assistant `
        --workflow "RGA Lifecycle Runner.yml" `
        --baseline .\\artifacts\\runtime_baseline.json `
        --commit-and-dispatch `
        --create-pr

Receive lifecycle completion signal:

    python .\\tools\\github_lifecycle_bridge.py `
        --owner YoshiHK `
        --repo Rhythm-Game-Assistant `
        --poll-completion `
        --session-id <AUDIT_SESSION_ID>
"""

import argparse
import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
except ImportError:  # pragma: no cover
    hashes = None
    serialization = None
    padding = None


# ------------------------------------------------------------
# Repository Paths
#
# If this file lives under tools/, repo root is parent.parent.
# If this file lives at repo root, repo root is parent.
# ------------------------------------------------------------

_THIS_FILE = Path(__file__).resolve()
ROOT = (
    _THIS_FILE.parent.parent
    if _THIS_FILE.parent.name == "tools"
    else _THIS_FILE.parent
)
ARTIFACTS = ROOT / "artifacts"

# ------------------------------------------------------------
# Contracts / constants (Updated for Inbound Backhaul Loop)
# ------------------------------------------------------------

RUNTIME_BASELINE_SCHEMA = "rga.runtime_baseline.v1.0"
BRIDGE_SCHEMA = "rga.github_lifecycle_bridge.v1.2"

############################################################
# Completion Signal Contract
#
# v1.0:
#   Local completion signal only.
#
# v1.1:
#   Adds optional remote_validation block for
#   --require-remote-completion.
############################################################

COMPLETION_SIGNAL_SCHEMA = "rga.lifecycle_completion_signal.v1.1"

DEFAULT_COMPLETION_SIGNAL = (
    ARTIFACTS / "lifecycle_completion_signal.json"
)


# Polling defaults for backhaul
DEFAULT_POLL_TIMEOUT_SEC = 600
DEFAULT_POLL_INTERVAL_SEC = 15
GOVERNANCE_GATE_ARTIFACT_NAME = "deployment-governance-gate-report"

DEFAULT_WORKFLOW = "RGA Lifecycle Runner.yml"
DEFAULT_REF = "main"
DEFAULT_REMOTE_PATH = "artifacts/runtime_baseline.json"

ALLOWED_COMMIT_PATHS = {
    "artifacts/runtime_baseline.json",
    "artifacts/github_lifecycle_bridge_request.json",
    "artifacts/github_lifecycle_bridge_report.json",
}

PROHIBITED_REMOTE_PATH_FRAGMENTS = (
    "runtime/",
    "Phase 1",
    "Phase 2",
    "Phase 3",
    "Phase 4",
    "Phase 4.5",
    "Phase 5",
    "Phase 6",
    "Phase 7",
    "canonical_row",
    "pattern_logic",
    "tips_generation",
    "personalization",
    "localization",
    "recommendation_logic",
)

@dataclass(frozen=True)
class BridgeConfig:
    owner: str
    repo: str

    workflow: str
    ref: str
    baseline_path: Path
    audit_mode: str
    audit_session_id: str

    auth_mode: str
    token_env: str
    github_app_id_env: str
    github_app_installation_id_env: str
    github_app_private_key_env: str

    dry_run: bool
    dispatch: bool
    commit_baseline: bool
    commit_and_dispatch: bool
    create_pr: bool

    wait_and_backhaul: bool
    poll_timeout_sec: int
    poll_interval_sec: int

    poll_completion: bool
    require_remote_completion: bool
    session_id: str

    base_branch: str
    target_branch: str
    remote_path: str
    commit_message: str
    pr_title: str
    pr_body: str

def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def safe_timestamp() -> str:
    return datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def ensure_artifacts_dir() -> None:
    ARTIFACTS.mkdir(
        parents=True,
        exist_ok=True,
    )


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )


def write_json(
    path: Path,
    payload: Dict[str, Any],
) -> None:
    ensure_artifacts_dir()

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    
def b64url_encode(
    raw: bytes,
) -> str:

    return (
        base64.urlsafe_b64encode(raw)
        .decode("utf-8")
        .rstrip("=")
    )


def normalize_private_key(
    raw: str,
) -> str:

    value = raw.strip()

    if not value:
        return value

    if "\\n" in value and "BEGIN" in value:
        value = value.replace("\\n", "\n")

    if "BEGIN" in value and "PRIVATE KEY" in value:
        return value

    try:
        decoded = base64.b64decode(value).decode("utf-8")
        if "BEGIN" in decoded and "PRIVATE KEY" in decoded:
            return decoded
    except Exception:
        pass

    return value


def build_github_app_jwt(
    *,
    app_id: str,
    private_key_pem: str,
) -> str:

    if serialization is None or padding is None or hashes is None:
        raise RuntimeError(
            "cryptography package is required for GitHub App "
            "authentication. Install with: python -m pip install cryptography"
        )

    now = int(time.time())

    header = {
        "alg": "RS256",
        "typ": "JWT",
    }

    payload = {
        "iat": now - 60,
        "exp": now + 540,
        "iss": app_id,
    }

    signing_input = (
        b64url_encode(
            json.dumps(
                header,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        + "."
        + b64url_encode(
            json.dumps(
                payload,
                separators=(",", ":"),
            ).encode("utf-8")
        )
    )

    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=None,
    )

    signature = private_key.sign(
        signing_input.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )

    return signing_input + "." + b64url_encode(signature)


def github_request_raw(
    *,
    method: str,
    url: str,
    token: Optional[str],
    payload: Optional[Dict[str, Any]] = None,
    accept: str = "application/vnd.github+json",
) -> Dict[str, Any]:

    data = None

    headers = {
        "Accept": accept,
        "User-Agent": "RGA-GitHub-Lifecycle-Bridge",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers=headers,
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            return {
                "ok": True,
                "status": resp.status,
                "body": json.loads(body) if body else {},
            }

    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            body = json.loads(raw)
        except Exception:
            body = {
                "raw": raw,
            }

        return {
            "ok": False,
            "status": exc.code,
            "reason": exc.reason,
            "body": body,
        }

    except Exception as exc:
        return {
            "ok": False,
            "status": None,
            "reason": str(exc),
            "body": {},
        }


def generate_github_app_installation_token(
    *,
    app_id: str,
    installation_id: str,
    private_key: str,
) -> Dict[str, Any]:

    private_key_pem = normalize_private_key(private_key)

    jwt_token = build_github_app_jwt(
        app_id=app_id,
        private_key_pem=private_key_pem,
    )

    url = (
        "https://api.github.com/app/installations/"
        f"{installation_id}/access_tokens"
    )

    result = github_request_raw(
        method="POST",
        url=url,
        token=jwt_token,
        payload={},
    )

    if not result.get("ok"):
        return {
            "ok": False,
            "stage": "generate_installation_token",
            "result": result,
        }

    token = (
        result.get("body", {})
        .get("token", "")
    )

    if not token:
        return {
            "ok": False,
            "stage": "extract_installation_token",
            "result": result,
        }

    return {
        "ok": True,
        "stage": "generate_installation_token",
        "token": token,
        "expires_at": result.get("body", {}).get("expires_at"),
    }

def build_completion_signal(
    *,
    session_id: str,
    lifecycle_status: str,
    governance_gate_passed: bool,
    remote_validation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build the local lifecycle completion signal.

    v1.1 adds an optional remote_validation block so the same
    signal can represent either:

      - local-only completion signal
      - remote-certified completion signal

    This function is bridge-layer only:
      - it does not mutate runtime DBs
      - it does not rewrite lifecycle chronology
      - it does not modify Completed Phases
    """

    payload: Dict[str, Any] = {
        "schema": COMPLETION_SIGNAL_SCHEMA,
        "audit_session_id": session_id,
        "lifecycle_status": lifecycle_status,
        "governance_gate_passed": governance_gate_passed,
        "signal_source": "github_lifecycle_bridge",
        "received_at": utc_now_iso(),
    }

    if remote_validation is not None:
        payload["remote_validation"] = remote_validation

    return payload

def resolve_token(
    token_env: str,
) -> Optional[str]:

    candidates = [
        token_env,

        # Directly usable installation token / API token
        "GITHUB_APP_TOKEN",
        "RGA_ACCESS",

        # Legacy fallback
        "PAT_TOKEN",
        "GH_TOKEN",
        "GITHUB_TOKEN",
    ]

    seen = set()

    for candidate in candidates:

        if not candidate:
            continue

        if candidate in seen:
            continue

        seen.add(candidate)

        value = os.environ.get(candidate, "").strip()

        if value:
            return value

    return None
    
def resolve_github_api_token(
    config: BridgeConfig,
) -> Dict[str, Any]:

    auth_mode = (
        getattr(config, "auth_mode", "app") or "app"
    ).strip().lower()

    if auth_mode not in {
        "app",
        "token",
        "auto",
    }:
        return {
            "ok": False,
            "reason": "unsupported_auth_mode",
            "auth_mode": auth_mode,
        }

    ############################################################
    # GitHub App authentication
    ############################################################

    if auth_mode in {
        "app",
        "auto",
    }:

        app_id_env = getattr(
            config,
            "github_app_id_env",
            "RGA_APP_ID",
        )

        installation_id_env = getattr(
            config,
            "github_app_installation_id_env",
            "RGA_APP_INSTALLATION_ID",
        )

        private_key_env = getattr(
            config,
            "github_app_private_key_env",
            "RGA_APP_PRIVATE_KEY",
        )

        app_id = os.environ.get(
            app_id_env,
            "",
        ).strip()

        installation_id = os.environ.get(
            installation_id_env,
            "",
        ).strip()

        private_key = os.environ.get(
            private_key_env,
            "",
        ).strip()

        if app_id and installation_id and private_key:

            app_result = generate_github_app_installation_token(
                app_id=app_id,
                installation_id=installation_id,
                private_key=private_key,
            )

            if app_result.get("ok"):
                return {
                    "ok": True,
                    "source": "github_app",
                    "auth_mode": auth_mode,
                    "token": app_result["token"],
                    "expires_at": app_result.get("expires_at"),
                    "app_id_env": app_id_env,
                    "installation_id_env": installation_id_env,
                    "private_key_env": private_key_env,
                }

            if auth_mode == "app":
                return {
                    "ok": False,
                    "reason": "github_app_token_generation_failed",
                    "auth_mode": auth_mode,
                    "result": app_result,
                    "checked_env": [
                        app_id_env,
                        installation_id_env,
                        private_key_env,
                    ],
                }

        elif auth_mode == "app":
            return {
                "ok": False,
                "reason": "github_app_credentials_missing",
                "auth_mode": auth_mode,
                "checked_env": [
                    app_id_env,
                    installation_id_env,
                    private_key_env,
                ],
            }

    ############################################################
    # Direct token fallback
    ############################################################

    if auth_mode in {
        "token",
        "auto",
    }:

        token_env = getattr(
            config,
            "token_env",
            "RGA_ACCESS",
        )

        token = resolve_token(
            token_env,
        )

        if token:
            return {
                "ok": True,
                "source": "direct_token",
                "auth_mode": auth_mode,
                "token": token,
                "token_env": token_env,
            }

    return {
        "ok": False,
        "reason": "github_credentials_missing",
        "auth_mode": auth_mode,
        "checked_env": [
            getattr(config, "github_app_id_env", "RGA_APP_ID"),
            getattr(config, "github_app_installation_id_env", "RGA_APP_INSTALLATION_ID"),
            getattr(config, "github_app_private_key_env", "RGA_APP_PRIVATE_KEY"),
            getattr(config, "token_env", "RGA_ACCESS"),
            "GITHUB_APP_TOKEN",
            "RGA_ACCESS",
            "PAT_TOKEN",
            "GH_TOKEN",
            "GITHUB_TOKEN",
        ],
    }    

def repo_api_root(config: BridgeConfig) -> str:
    return (
        "https://api.github.com/repos/"
        f"{config.owner}/{config.repo}"
    )
    
class NoRedirectHandler(
    urllib.request.HTTPRedirectHandler
):
    """
    Prevent urllib from automatically following redirects.

    GitHub artifact archive_download_url usually returns a
    redirect to a time-limited artifact storage URL.

    The GitHub Authorization header is valid for the GitHub API
    endpoint, but should not be forwarded to the redirected
    artifact storage URL.
    """

    def redirect_request(
        self,
        req,
        fp,
        code,
        msg,
        headers,
        newurl,
    ):
        return None
        
def download_github_actions_artifact_zip(
    *,
    download_url: str,
    token: str,
) -> Dict[str, Any]:
    """
    Download a GitHub Actions artifact ZIP.

    Step 1:
      Request GitHub archive_download_url using GitHub token.

    Step 2:
      If GitHub returns redirect, follow the redirected URL
      without the GitHub Authorization header.

    This avoids sending:
        Authorization: Bearer <GitHub installation token>

    to the redirected artifact storage URL.
    """

    github_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "RGA-GitHub-Lifecycle-Bridge",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    opener = urllib.request.build_opener(
        NoRedirectHandler
    )

    req = urllib.request.Request(
        download_url,
        headers=github_headers,
        method="GET",
    )

    try:
        response = opener.open(
            req,
            timeout=60,
        )

        content = response.read()

        return {
            "ok": True,
            "status": getattr(response, "status", None),
            "redirected": False,
            "content": content,
        }

    except urllib.error.HTTPError as exc:

        ####################################################
        # Expected successful artifact-download path:
        #
        # GitHub returns 302 with Location header.
        ####################################################

        if exc.code in {
            301,
            302,
            303,
            307,
            308,
        }:

            location = exc.headers.get("Location")

            if not location:
                return {
                    "ok": False,
                    "status": exc.code,
                    "reason": "redirect_without_location",
                }

            storage_headers = {
                "User-Agent": "RGA-GitHub-Lifecycle-Bridge",
            }

            storage_req = urllib.request.Request(
                location,
                headers=storage_headers,
                method="GET",
            )

            try:
                with urllib.request.urlopen(
                    storage_req,
                    timeout=60,
                ) as storage_resp:

                    content = storage_resp.read()

                    return {
                        "ok": True,
                        "status": getattr(
                            storage_resp,
                            "status",
                            None,
                        ),
                        "redirected": True,
                        "redirect_status": exc.code,
                        "content": content,
                    }

            except urllib.error.HTTPError as storage_exc:

                raw = storage_exc.read().decode(
                    "utf-8",
                    errors="replace",
                )

                return {
                    "ok": False,
                    "status": storage_exc.code,
                    "reason": storage_exc.reason,
                    "redirected": True,
                    "body": raw[:1000],
                }

            except Exception as storage_exc:

                return {
                    "ok": False,
                    "status": None,
                    "reason": str(storage_exc),
                    "redirected": True,
                }

        ####################################################
        # Non-redirect GitHub API failure.
        ####################################################

        raw = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        return {
            "ok": False,
            "status": exc.code,
            "reason": exc.reason,
            "redirected": False,
            "body": raw[:1000],
        }

    except Exception as exc:

        return {
            "ok": False,
            "status": None,
            "reason": str(exc),
            "redirected": False,
        }
        
def collect_json_strings(
    value: Any,
) -> list[str]:
    """
    Recursively collect string values from a JSON-compatible object.
    """

    found: list[str] = []

    if isinstance(value, str):
        found.append( elif isinstance(value, dict):
        for item in value.values():
            found.extend(
                collect_json_strings(item)
            )

    elif isinstance(value, list):
        for item in value:
            found.extend(
                collect_json_strings(item)
            )

    return found


def collect_candidate_session_ids(
    value: Any,
) -> list"""
    Recursively collect values that look like RGA lifecycle session IDs.

    This is diagnostic only. It helps explain why
    --require-remote-completion failed.
    """

    sessions: list[str] = []

    for item in collect_json_strings(value):
        if item.startswith("rga-session-"):
            sessions.append(item)

    return sorted(set(sessions))


def json_contains_session_id(
    *,
    payload: Any,
    raw: str,
    session_id: str,
) -> bool:
    """
    Match session ID in either raw JSON text or recursive JSON values.
    """

    if session_id in raw:
        return True

    if payload is None:
        return False

    for item in collect_json_strings(payload):
        if item == session_id:
            return True

    return False        

def verify_remote_completion(
    config: BridgeConfig,
    token: str,
) -> Dict[str, Any]:
    """
    Verify lifecycle completion from remote GitHub Actions artifacts.

    This is the remote-certified path for:

        --poll-completion --require-remote-completion

    Strategy:
      1. List recent GitHub Actions artifacts.
      2. Select likely lifecycle / governance / deployment artifacts.
      3. Download artifact ZIPs.
      4. Inspect JSON files inside each ZIP.
      5. Match the requested audit_session_id.
      6. Accept the remote completion only when the evidence
         indicates completion / governance success.

    This function is intentionally bridge-layer only.

    It does not:
      - mutate runtime databases
      - alter Completed Phases
      - rewrite lifecycle chronology
      - dispatch new workflows
    """

    session_id = (
        getattr(config, "session_id", "") or ""
    ).strip()

    if not session_id:
        return {
            "ok": False,
            "required": True,
            "verified": False,
            "reason": "missing_session_id",
        }

    ############################################################
    # List recent GitHub Actions artifacts.
    ############################################################

    artifacts: list[Dict[str, Any]] = []
    artifact_pages = []

    for page in range(1, 6):

        artifacts_url = (
            f"{repo_api_root(config)}/actions/artifacts"
            f"?per_page=100&page={page}"
        )

        artifacts_result = github_request_raw(
            method="GET",
            url=artifacts_url,
            token=token,
        )

        artifact_pages.append(
            {
                "page": page,
                "ok": artifacts_result.get("ok"),
                "status": artifacts_result.get("status"),
            }
        )

        if not artifacts_result.get("ok"):
            return {
                "ok": False,
                "required": True,
                "verified": False,
                "reason": "artifact_listing_failed",
                "artifact_pages": artifact_pages,
                "artifact_listing": artifacts_result,
            }

        page_artifacts = (
            artifacts_result
            .get("body", {})
            .get("artifacts", [])
        )

        if not page_artifacts:
            break

        artifacts.extend(page_artifacts)

    if not artifacts:
        return {
            "ok": False,
            "required": True,
            "verified": False,
            "reason": "no_actions_artifacts_found",
        }

    ############################################################
    # Candidate artifact selection.
    ############################################################

    candidate_keywords = (
        "lifecycle",
        "governance",
        "deployment",
        "gate",
        "certification",
        "runtime-certification",
        "deployment-governance",
        "deployment-governance-gate",
    )

    candidates = []

    for artifact in artifacts:
        name = str(
            artifact.get("name", "")
        )

        expired = bool(
            artifact.get("expired", False)
        )

        if expired:
            continue

        lowered = name.lower()

        if any(
            keyword in lowered
            for keyword in candidate_keywords
        ):
            candidates.append(artifact)

    if not candidates:
        return {
            "ok": False,
            "required": True,
            "verified": False,
            "reason": "no_candidate_completion_artifacts_found",
            "artifact_count": len(artifacts),
        }

    ############################################################
    # Inspect candidate artifact ZIPs.
    ############################################################

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "RGA-GitHub-Lifecycle-Bridge",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    inspected = []
    matched_session = []
    observed_session_ids: set[str] = set()
    json_members_seen = []

    for artifact in candidates[:50]:

        artifact_name = str(
            artifact.get("name", "")
        )

        download_url = str(
            artifact.get("archive_download_url", "")
        )

        if not download_url:
            inspected.append(
                {
                    "artifact_name": artifact_name,
                    "ok": False,
                    "reason": "missing_archive_download_url",
                }
            )
            continue

        download_result = download_github_actions_artifact_zip(
            download_url=download_url,
            token=token,
        )

        if not download_result.get("ok"):

            inspected.append(
                {
                    "artifact_name": artifact_name,
                    "ok": False,
                    "status": download_result.get("status"),
                    "reason": download_result.get("reason"),
                    "redirected": download_result.get(
                        "redirected",
                        False,
                    ),
                    "body": download_result.get("body"),
                }
            )

            continue

        content = download_result["content"]

        inspected.append(
            {
                "artifact_name": artifact_name,
                "ok": True,
                "status": download_result.get("status"),
                "redirected": download_result.get(
                    "redirected",
                    False,
                ),
            }
        )

        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zip_file:

                for member in zip_file.namelist():

                    member_lower = member.lower()

                    if not member_lower.endswith(".json"):
                        continue

                    try:
                        raw = (
                            zip_file
                            .read(member)
                            .decode("utf-8")
                        )
                    except Exception:
                        continue

                    try:
                        payload = json.loads(raw)
                    except Exception:
                        payload = None

                    ################################################
                    # Session matching
                    ################################################

                    if isinstance(payload, (dict, list)):
                        for discovered in collect_candidate_session_ids(payload):
                            observed_session_ids.add(discovered)

                    json_members_seen.append(
                        {
                            "artifact_name": artifact_name,
                            "member": member,
                            "observed_session_ids": (
                                collect_candidate_session_ids(payload)
                                if isinstance(payload, (dict, list))
                                else []
                            ),
                        }
                    )

                    session_match = json_contains_session_id(
                        payload=payload,
                        raw=raw,
                        session_id=session_id,
                    )

                    if not session_match:
                        continue
                    matched_session.append(
                        {
                            "artifact_name": artifact_name,
                            "member": member,
                        }
                    )

                    ################################################
                    # Completion / governance acceptance
                    ################################################

                    if not isinstance(payload, dict):
                        continue

                    lifecycle_status = str(
                        payload.get("lifecycle_status", "")
                    ).lower()

                    completed_stage = str(
                        payload.get("completed_stage", "")
                    ).lower()

                    stage = str(
                        payload.get("stage", "")
                    ).lower()

                    next_stage = str(
                        payload.get("next_stage", "")
                    ).lower()

                    status = str(
                        payload.get("status", "")
                    ).lower()

                    overall_status = str(
                        payload.get("overall_status", "")
                    ).lower()

                    governance_gate_passed = payload.get(
                        "governance_gate_passed",
                        None,
                    )

                    governance_passed = payload.get(
                        "governance_passed",
                        None,
                    )

                    accepted_completion = False

                    ################################################
                    # Strong completion signal evidence.
                    ################################################

                    if (
                        lifecycle_status == "complete"
                        and governance_gate_passed is True
                    ):
                        accepted_completion = True

                    if (
                        lifecycle_status == "complete"
                        and governance_passed is True
                    ):
                        accepted_completion = True

                    ################################################
                    # Lifecycle event style evidence.
                    ################################################

                    if completed_stage == "complete":
                        accepted_completion = True

                    if stage == "complete":
                        accepted_completion = True

                    if (
                        completed_stage == "governance_gate"
                        and next_stage == "complete"
                    ):
                        accepted_completion = True

                    ################################################
                    # Governance / report style evidence.
                    ################################################

                    if status in {
                        "complete",
                        "success",
                        "succeeded",
                        "passed",
                        "pass",
                        "ok",
                    }:
                        accepted_completion = True

                    if overall_status in {
                        "complete",
                        "success",
                        "succeeded",
                        "passed",
                        "pass",
                        "ok",
                    }:
                        accepted_completion = True

                    if accepted_completion:

                        evidence = {
                            "lifecycle_status": lifecycle_status,
                            "completed_stage": completed_stage,
                            "stage": stage,
                            "next_stage": next_stage,
                            "status": status,
                            "overall_status": overall_status,
                            "governance_gate_passed": governance_gate_passed,
                            "governance_passed": governance_passed,
                        }

                        return {
                            "ok": True,
                            "required": True,
                            "verified": True,
                            "source": "github_actions_artifact",
                            "artifact_name": artifact_name,
                            "member": member,
                            "audit_session_id": session_id,
                            "matched_session_count": len(matched_session),
                            "evidence": evidence,
                        }

        except zipfile.BadZipFile:
            inspected.append(
                {
                    "artifact_name": artifact_name,
                    "ok": False,
                    "reason": "bad_zip_file",
                }
            )

        except Exception as exc:
            inspected.append(
                {
                    "artifact_name": artifact_name,
                    "ok": False,
                    "reason": str(exc),
                }
            )

    ############################################################
    # No acceptable completion evidence found.
    ############################################################

    return {
        "ok": False,
        "required": True,
        "verified": False,
        "reason": "remote_completion_not_verified",
        "audit_session_id": session_id,
        "artifact_count": len(artifacts),
        "candidate_artifact_count": len(candidates),
        "matched_session_count": len(matched_session),
        "matched_session": matched_session[:10],
        "observed_session_ids": sorted(observed_session_ids)[:25],
        "json_members_seen": json_members_seen[:25],
        "inspected": inspected[:10],
    }

def github_request(
    *,
    method: str,
    url: str,
    token: Optional[str],
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:

    body: Optional[bytes] = None

    if payload is not None:
        body = json.dumps(
            payload,
        ).encode(
            "utf-8",
        )

    headers = {
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "RGA-GitHub-Lifecycle-Bridge",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers=headers,
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=30,
        ) as response:

            text = response.read().decode(
                "utf-8",
                errors="replace",
            )

            parsed: Any = None

            if text.strip():
                try:
                    parsed = json.loads(text)
                except Exception:
                    parsed = text

            return {
                "ok": 200 <= response.status < 300,
                "status": response.status,
                "reason": response.reason,
                "body": parsed,
            }

    except urllib.error.HTTPError as exc:

        text = exc.read().decode(
            "utf-8",
            errors="replace",
        )

        parsed: Any = None

        if text.strip():
            try:
                parsed = json.loads(text)
            except Exception:
                parsed = text

        return {
            "ok": False,
            "status": exc.code,
            "reason": exc.reason,
            "body": parsed,
        }

    except Exception as exc:

        return {
            "ok": False,
            "status": None,
            "reason": type(exc).__name__,
            "body": str(exc),
        }


def validate_remote_path(
    remote_path: str,
) -> Dict[str, Any]:

    normalized = (
        remote_path
        .replace("\\", "/")
        .strip("/")
    )

    if normalized not in ALLOWED_COMMIT_PATHS:
        return {
            "valid": False,
            "reason": "remote_path_not_allowed",
            "remote_path": normalized,
            "allowed_paths": sorted(
                ALLOWED_COMMIT_PATHS
            ),
        }

    for fragment in PROHIBITED_REMOTE_PATH_FRAGMENTS:
        if fragment.lower() in normalized.lower():
            return {
                "valid": False,
                "reason": "remote_path_hits_prohibited_scope",
                "remote_path": normalized,
                "fragment": fragment,
            }

    return {
        "valid": True,
        "remote_path": normalized,
    }


def validate_runtime_baseline(
    path: Path,
) -> Dict[str, Any]:

    if not path.exists():
        return {
            "valid": False,
            "reason": "runtime_baseline_missing",
            "path": str(path),
        }

    try:
        payload = read_json(path)

    except Exception as exc:
        return {
            "valid": False,
            "reason": "runtime_baseline_parse_error",
            "path": str(path),
            "error": str(exc),
        }

    schema = payload.get("schema")

    if schema != RUNTIME_BASELINE_SCHEMA:
        return {
            "valid": False,
            "reason": "unsupported_runtime_baseline_schema",
            "path": str(path),
            "schema": schema,
        }

    databases = payload.get("databases") or {}

    required = [
        "file_scan_inventory.db",
        "chart_assets.db",
        "chart_patterns.db",
    ]

    missing_database_nodes = [
        name
        for name in required
        if name not in databases
    ]

    unreadable = []

    for name in required:
        node = databases.get(name) or {}

        if node and node.get("readable") is not True:
            unreadable.append(name)

    if missing_database_nodes:
        return {
            "valid": False,
            "reason": "runtime_baseline_database_node_missing",
            "path": str(path),
            "missing_database_nodes": missing_database_nodes,
        }

    if unreadable:
        return {
            "valid": False,
            "reason": "runtime_baseline_database_not_readable",
            "path": str(path),
            "unreadable": unreadable,
        }

    return {
        "valid": True,
        "path": str(path),
        "schema": schema,
        "baseline_ready": bool(
            payload.get("baseline_ready")
        ),
        "summary": payload.get("summary") or {},
        "generated_at": payload.get("generated_at"),
        "contract": payload.get("contract") or {},
        "governance": payload.get("governance") or {},
    }

def resolve_effective_dispatch_ref(
    config: BridgeConfig,
) -> str:
    """
    Resolve the Git ref used for workflow_dispatch.

    For --commit-and-dispatch, the runtime baseline is committed
    to config.target_branch. Lifecycle Runner must run on that
    same branch so it can see artifacts/runtime_baseline.json.

    For --dispatch only, use config.ref.
    """

    if config.commit_and_dispatch:
        return config.target_branch

    return config.ref

def build_workflow_dispatch_payload(
    config: BridgeConfig,
) -> Dict[str, Any]:

    dispatch_ref = resolve_effective_dispatch_ref(
        config
    )

    return {
        "ref": dispatch_ref,
        "inputs": {
            "operator_action": "start_lifecycle",
            "audit_session_id": config.audit_session_id,
            "ref": dispatch_ref,
        },
    }

def workflow_dispatch_url(
    config: BridgeConfig,
) -> str:

    # workflow may be a file name or numeric workflow id.
    workflow = urllib.parse.quote(
        config.workflow,
        safe="",
    )

    return (
        f"{repo_api_root(config)}"
        f"/actions/workflows/{workflow}/dispatches"
    )


def dispatch_workflow(
    *,
    config: BridgeConfig,
    token: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:

    return github_request(
        method="POST",
        url=workflow_dispatch_url(config),
        token=token,
        payload=payload,
    )


def get_branch_sha(
    *,
    config: BridgeConfig,
    token: str,
    branch: str,
) -> Dict[str, Any]:

    branch_encoded = urllib.parse.quote(
        f"heads/{branch}",
        safe="",
    )

    url = (
        f"{repo_api_root(config)}"
        f"/git/ref/{branch_encoded}"
    )

    return github_request(
        method="GET",
        url=url,
        token=token,
    )


def create_branch(
    *,
    config: BridgeConfig,
    token: str,
    target_branch: str,
    base_branch: str,
) -> Dict[str, Any]:

    base_ref = get_branch_sha(
        config=config,
        token=token,
        branch=base_branch,
    )

    if not base_ref.get("ok"):
        return {
            "ok": False,
            "stage": "get_base_branch",
            "base_branch": base_branch,
            "result": base_ref,
        }

    body = base_ref.get("body") or {}
    base_sha = (
        (body.get("object") or {})
        .get("sha")
    )

    if not base_sha:
        return {
            "ok": False,
            "stage": "extract_base_sha",
            "base_branch": base_branch,
            "result": base_ref,
        }

    payload = {
        "ref": f"refs/heads/{target_branch}",
        "sha": base_sha,
    }

    result = github_request(
        method="POST",
        url=f"{repo_api_root(config)}/git/refs",
        token=token,
        payload=payload,
    )

    if result.get("ok"):
        return {
            "ok": True,
            "created": True,
            "branch": target_branch,
            "base_branch": base_branch,
            "base_sha": base_sha,
            "result": result,
        }

    # 422 often means branch already exists.
    # Treat it as non-fatal after verifying the branch exists.
    if result.get("status") == 422:

        existing = get_branch_sha(
            config=config,
            token=token,
            branch=target_branch,
        )

        return {
            "ok": bool(existing.get("ok")),
            "created": False,
            "already_exists": bool(
                existing.get("ok")
            ),
            "branch": target_branch,
            "base_branch": base_branch,
            "base_sha": base_sha,
            "result": result,
            "existing": existing,
        }

    return {
        "ok": False,
        "created": False,
        "branch": target_branch,
        "base_branch": base_branch,
        "base_sha": base_sha,
        "result": result,
    }


def get_remote_file_sha(
    *,
    config: BridgeConfig,
    token: str,
    remote_path: str,
    branch: str,
) -> Dict[str, Any]:

    path_encoded = urllib.parse.quote(
        remote_path,
        safe="/",
    )

    branch_encoded = urllib.parse.quote(
        branch,
        safe="",
    )

    url = (
        f"{repo_api_root(config)}"
        f"/contents/{path_encoded}"
        f"?ref={branch_encoded}"
    )

    return github_request(
        method="GET",
        url=url,
        token=token,
    )


def commit_runtime_baseline_to_github(
    *,
    config: BridgeConfig,
    token: str,
) -> Dict[str, Any]:
    """
    Commit local artifacts/runtime_baseline.json to GitHub Contents API.

    Steps:
    1. Read local artifacts/runtime_baseline.json.
    2. Get existing remote file SHA if present.
    3. PUT updated content to GitHub Contents API.
    4. Target a branch, preferably not main.
    5. Return a structured response for github_lifecycle_bridge_report.json.
    """

    path_validation = validate_remote_path(
        config.remote_path
    )

    if not path_validation.get("valid"):
        return {
            "attempted": False,
            "ok": False,
            "reason": path_validation.get("reason"),
            "path_validation": path_validation,
        }

    if config.target_branch == config.base_branch:
        return {
            "attempted": False,
            "ok": False,
            "reason": "target_branch_must_not_equal_base_branch",
            "base_branch": config.base_branch,
            "target_branch": config.target_branch,
        }

    if not config.baseline_path.exists():
        return {
            "attempted": False,
            "ok": False,
            "reason": "runtime_baseline_missing",
            "baseline_path": str(config.baseline_path),
        }

    branch_result = create_branch(
        config=config,
        token=token,
        target_branch=config.target_branch,
        base_branch=config.base_branch,
    )

    if not branch_result.get("ok"):
        return {
            "attempted": True,
            "ok": False,
            "stage": "create_branch",
            "branch_result": branch_result,
        }

    file_result = get_remote_file_sha(
        config=config,
        token=token,
        remote_path=config.remote_path,
        branch=config.target_branch,
    )

    remote_sha = None

    if file_result.get("ok"):
        body = file_result.get("body") or {}
        remote_sha = body.get("sha")

    content_bytes = config.baseline_path.read_bytes()

    encoded_content = base64.b64encode(
        content_bytes,
    ).decode(
        "ascii",
    )

    payload: Dict[str, Any] = {
        "message": config.commit_message,
        "content": encoded_content,
        "branch": config.target_branch,
    }

    if remote_sha:
        payload["sha"] = remote_sha

    path_encoded = urllib.parse.quote(
        config.remote_path,
        safe="/",
    )

    put_result = github_request(
        method="PUT",
        url=(
            f"{repo_api_root(config)}"
            f"/contents/{path_encoded}"
        ),
        token=token,
        payload=payload,
    )

    return {
        "attempted": True,
        "ok": bool(put_result.get("ok")),
        "remote_path": config.remote_path,
        "baseline_path": str(config.baseline_path),
        "base_branch": config.base_branch,
        "target_branch": config.target_branch,
        "remote_sha_before": remote_sha,
        "branch_result": branch_result,
        "remote_file_lookup": file_result,
        "put_result": put_result,
    }


def create_pull_request(
    *,
    config: BridgeConfig,
    token: str,
) -> Dict[str, Any]:

    payload = {
        "title": config.pr_title,
        "head": config.target_branch,
        "base": config.base_branch,
        "body": config.pr_body,
        "maintainer_can_modify": True,
    }

    return github_request(
        method="POST",
        url=f"{repo_api_root(config)}/pulls",
        token=token,
        payload=payload,
    )

import io
import time
import zipfile


def get_latest_workflow_run_id(
    *,
    config: BridgeConfig,
    token: str,
) -> Optional[int]:
    """Fetch the most recent workflow run ID triggered by dispatch."""
    workflow = urllib.parse.quote(config.workflow, safe="")
    url = f"{repo_api_root(config)}/actions/workflows/{workflow}/runs?per_page=1"
    
    res = github_request(method="GET", url=url, token=token)
    if res.get("ok") and res.get("body", {}).get("workflow_runs"):
        return res["body"]["workflow_runs"][0]["id"]
    return None


def download_and_extract_artifact(
    *,
    download_url: str,
    token: str,
    extract_to: Path,
) -> bool:
    """Download governance report zip artifact from GitHub and extract locally."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "RGA-GitHub-Lifecycle-Bridge",
    }
    req = urllib.request.Request(download_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read()
            with zipfile.ZipFile(io.BytesIO(content)) as zip_file:
                zip_file.extractall(extract_to)
            return True
    except Exception as exc:
        print(f"[RGA-BRIDGE][BACKHAUL-ERR] Failed to extract artifact: {exc}")
        return False


def wait_and_backhaul_governance_report(
    *,
    config: BridgeConfig,
    token: str,
    run_id: int,
) -> Dict[str, Any]:
    """
    Polls the dispatched workflow run until 'completed', 
    then backhauls 'deployment-governance-gate-report' to local artifacts/.
    """
    start_time = time.time()
    url = f"{repo_api_root(config)}/actions/runs/{run_id}"

    print(f"[RGA-BRIDGE][LOOP] Waiting for workflow run {run_id} to finish...")

    while time.time() - start_time < config.poll_timeout_sec:
        res = github_request(method="GET", url=url, token=token)
        if not res.get("ok"):
            time.sleep(config.poll_interval_sec)
            continue

        body = res.get("body", {})
        status = body.get("status")
        conclusion = body.get("conclusion")

        print(f"[RGA-BRIDGE][LOOP] Run Status: '{status}' | Conclusion: '{conclusion}'")

        if status == "completed":
            artifacts_url = body.get("artifacts_url")
            art_res = github_request(method="GET", url=artifacts_url, token=token)
            
            if not art_res.get("ok"):
                return {
                    "ok": False,
                    "reason": "failed_to_list_artifacts",
                    "conclusion": conclusion,
                }

            artifacts = art_res.get("body", {}).get("artifacts", [])
            for art in artifacts:
                if art.get("name") == GOVERNANCE_GATE_ARTIFACT_NAME:
                    dl_url = art.get("archive_download_url")
                    success = download_and_extract_artifact(
                        download_url=dl_url,
                        token=token,
                        extract_to=ARTIFACTS,
                    )
                    return {
                        "ok": success and (conclusion == "success"),
                        "conclusion": conclusion,
                        "report_backhauled": success,
                        "artifact_id": art.get("id"),
                    }

            return {
                "ok": conclusion == "success",
                "conclusion": conclusion,
                "report_backhauled": False,
                "reason": "governance_artifact_not_found",
            }

        time.sleep(config.poll_interval_sec)

    return {
        "ok": False,
        "reason": "polling_timeout_exceeded",
        "elapsed_sec": time.time() - start_time,
    }



def parse_args(
    argv: Optional[list[str]] = None,
) -> BridgeConfig:

    parser = argparse.ArgumentParser(
        description=(
            "Bridge local RGA runtime baseline "
            "into GitHub lifecycle."
        )
    )

    parser.add_argument(
        "--owner",
        required=True,
        help="GitHub repository owner/org",
    )

    parser.add_argument(
        "--repo",
        required=True,
        help="GitHub repository name",
    )

    parser.add_argument(
        "--workflow",
        default=DEFAULT_WORKFLOW,
        help="Workflow file name or workflow id",
    )

    parser.add_argument(
        "--ref",
        default=DEFAULT_REF,
        help="Git ref to dispatch workflow on",
    )

    parser.add_argument(
        "--baseline",
        default="artifacts/runtime_baseline.json",
        help="Path to runtime_baseline.json",
    )

    parser.add_argument(
        "--audit-mode",
        default="pre_audit",
        help="Lifecycle audit mode input",
    )

    parser.add_argument(
        "--audit-session-id",
        default="",
        help="Optional lifecycle correlation id",
    )

    parser.add_argument(
        "--auth-mode",
        choices=[
            "app",
            "token",
            "auto",
        ],
        default="app",
        help=(
            "Authentication mode. "
            "'app' generates a GitHub App installation token. "
            "'token' uses a directly supplied bearer token. "
            "'auto' tries GitHub App first, then token fallback."
        ),
    )

    parser.add_argument(
        "--token-env",
        default="RGA_ACCESS",
        help=(
            "Legacy/direct token environment variable. "
            "Used only with --auth-mode token or --auth-mode auto."
        ),
    )

    parser.add_argument(
        "--github-app-id-env",
        default="RGA_APP_ID",
        help="Environment variable containing GitHub App ID.",
    )

    parser.add_argument(
        "--github-app-installation-id-env",
        default="RGA_APP_INSTALLATION_ID",
        help="Environment variable containing GitHub App installation ID.",
    )

    parser.add_argument(
        "--github-app-private-key-env",
        default="RGA_APP_PRIVATE_KEY",
        help="Environment variable containing GitHub App private key PEM.",
    )

    parser.add_argument(
        "--base-branch",
        default=DEFAULT_REF,
        help="Base branch for baseline commit / PR",
    )

    parser.add_argument(
        "--target-branch",
        default="",
        help="Target branch for baseline commit",
    )

    parser.add_argument(
        "--remote-path",
        default=DEFAULT_REMOTE_PATH,
        help="Remote repository path to update",
    )

    parser.add_argument(
        "--commit-message",
        default="[RGA Runtime] Update runtime baseline contract",
        help="Commit message",
    )

    parser.add_argument(
        "--pr-title",
        default="[RGA Runtime] Update runtime baseline contract",
        help="Pull request title",
    )

    parser.add_argument(
        "--pr-body",
        default=(
            "Automated runtime baseline contract update "
            "generated by RGA GitHub Lifecycle Bridge."
        ),
        help="Pull request body",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate baseline and write request/report only",
    )

    parser.add_argument(
        "--dispatch",
        action="store_true",
        help="Trigger RGA Lifecycle Runner only",
    )

    parser.add_argument(
        "--commit-baseline",
        action="store_true",
        help=(
            "Commit artifacts/runtime_baseline.json "
            "to GitHub branch"
        ),
    )

    parser.add_argument(
        "--commit-and-dispatch",
        action="store_true",
        help="Commit baseline, then trigger lifecycle",
    )

    parser.add_argument(
        "--create-pr",
        action="store_true",
        help="Create PR after committing baseline branch",
    )

    parser.add_argument(
        "--wait-and-backhaul",
        action="store_true",
        help="Wait for dispatched workflow completion and backhaul governance gate artifact.",
    )

    parser.add_argument(
        "--poll-timeout-sec",
        type=int,
        default=DEFAULT_POLL_TIMEOUT_SEC,
        help="Max polling timeout in seconds for --wait-and-backhaul",
    )

    parser.add_argument(
        "--poll-interval-sec",
        type=int,
        default=DEFAULT_POLL_INTERVAL_SEC,
        help="Polling interval in seconds for --wait-and-backhaul",
    )
    
    parser.add_argument(
        "--poll-completion",
        action="store_true",
        help="Poll lifecycle completion state."
    )
    
    parser.add_argument(
        "--require-remote-completion",
        action="store_true",
        help=(
            "Require governance-certified completion to be "
            "validated from GitHub Actions artifacts before "
            "writing lifecycle_completion_signal.json."
        ),
    )  

    parser.add_argument(
        "--session-id",
        default="",
        help="Lifecycle session identifier."
    )

    args = parser.parse_args(argv)

    selected_actions = sum(
        bool(value)
        for value in [
            args.dry_run,
            args.dispatch,
            args.commit_baseline,
            args.commit_and_dispatch,
            args.poll_completion,
        ]
    )
    
    if args.require_remote_completion and not args.poll_completion:
        parser.error(
            "--require-remote-completion requires --poll-completion."
        )
    

    if selected_actions == 0:
        args.dry_run = True

    elif selected_actions > 1:
        parser.error(
            "Choose only one of "
            "--dry-run, "
            "--dispatch, "
            "--commit-baseline, "
            "--commit-and-dispatch, "
            "or --poll-completion."
        )

    if args.create_pr and not (
        args.commit_baseline
        or args.commit_and_dispatch
    ):
        parser.error(
            "--create-pr requires "
            "--commit-baseline or "
            "--commit-and-dispatch."
        )

    baseline_path = Path(args.baseline)
    
    if args.poll_completion and not args.session_id.strip():
        parser.error(
            "--poll-completion requires --session-id."
        )   

    if not baseline_path.is_absolute():
        baseline_path = ROOT / baseline_path

    audit_session_id = args.audit_session_id.strip()

    if not audit_session_id:
        audit_session_id = (
            f"local-runtime-baseline-{safe_timestamp()}"
        )

    target_branch = args.target_branch.strip()

    if not target_branch:
        target_branch = (
            f"runtime-baseline/update-{safe_timestamp()}"
        )

    return BridgeConfig(
        owner=args.owner,
        repo=args.repo,
        workflow=args.workflow,
        ref=args.ref,
        baseline_path=baseline_path,
        audit_mode=args.audit_mode,
        audit_session_id=audit_session_id,
        auth_mode=args.auth_mode,
        token_env=args.token_env,
        github_app_id_env=args.github_app_id_env,
        github_app_installation_id_env=args.github_app_installation_id_env,
        github_app_private_key_env=args.github_app_private_key_env,
        dry_run=bool(args.dry_run),
        dispatch=bool(args.dispatch),
        commit_baseline=bool(args.commit_baseline),
        commit_and_dispatch=bool(args.commit_and_dispatch),
        create_pr=bool(args.create_pr),
        wait_and_backhaul=bool(args.wait_and_backhaul),
        poll_timeout_sec=args.poll_timeout_sec,
        poll_interval_sec=args.poll_interval_sec,
        poll_completion=bool(args.poll_completion),
        require_remote_completion=bool(args.require_remote_completion),
        session_id=args.session_id.strip(), 
        base_branch=args.base_branch,
        target_branch=target_branch,
        remote_path=(
            args.remote_path
            .replace("\\", "/")
            .strip("/")
        ),
        commit_message=args.commit_message,
        pr_title=args.pr_title,
        pr_body=args.pr_body,
    )


def main(
    argv: Optional[list[str]] = None,
) -> int:

    ensure_artifacts_dir()

    config = parse_args(argv)

    request_out = (
        ARTIFACTS
        / "github_lifecycle_bridge_request.json"
    )

    report_out = (
        ARTIFACTS
        / "github_lifecycle_bridge_report.json"
    )

    ########################################################
    # Completion Signal Polling
    #
    # Local feedback-loop integration.
    #
    # This path is intentionally isolated from:
    #
    #   runtime baseline validation
    #   remote path validation
    #   workflow dispatch
    #   commit operations
    #
    # Optional:
    #
    #   --require-remote-completion
    #
    # verifies GitHub Actions artifacts before writing the
    # local lifecycle_completion_signal.json.
    ########################################################

    if config.poll_completion:

        remote_validation: Optional[Dict[str, Any]] = None
        safe_token_result: Optional[Dict[str, Any]] = None

        ####################################################
        # Remote-grounded completion verification.
        ####################################################

        if config.require_remote_completion:

            token_result = resolve_github_api_token(
                config,
            )

            if not token_result.get("ok"):

                report: Dict[str, Any] = {
                    "schema": BRIDGE_SCHEMA,
                    "generated_at": utc_now_iso(),
                    "mode": "poll_completion",
                    "token_result": token_result,
                    "completion_result": {
                        "ok": False,
                        "reason": "github_credentials_unavailable",
                        "audit_session_id": config.session_id,
                    },
                }

                write_json(
                    report_out,
                    report,
                )

                print(
                    "[RGA-BRIDGE][FAIL] "
                    "GitHub credentials unavailable for "
                    "remote completion verification."
                )

                print(
                    f"[RGA-BRIDGE][REPORT] {report_out}"
                )

                return 3

            token = token_result["token"]

            safe_token_result = dict(token_result)
            safe_token_result.pop(
                "token",
                None,
            )

            remote_result = verify_remote_completion(
                config=config,
                token=token,
            )

            remote_validation = dict(remote_result)

            if not remote_result.get("ok"):

                report = {
                    "schema": BRIDGE_SCHEMA,
                    "generated_at": utc_now_iso(),
                    "mode": "poll_completion",
                    "token_result": safe_token_result,
                    "remote_completion": remote_result,
                    "completion_result": {
                        "ok": False,
                        "reason": "remote_completion_not_verified",
                        "audit_session_id": config.session_id,
                    },
                }

                write_json(
                    report_out,
                    report,
                )

                print(
                    "[RGA-BRIDGE][FAIL] "
                    "Remote governance-certified completion "
                    "was not verified."
                )

                print(
                    f"[RGA-BRIDGE][REPORT] {report_out}"
                )

                return 10

            print(
                "[RGA-BRIDGE][OK] "
                "Remote governance completion verified."
            )

        ####################################################
        # Local-only completion signal mode.
        ####################################################

        else:

            remote_validation = {
                "required": False,
                "verified": False,
                "source": "local_signal_only",
            }

        ####################################################
        # Write local lifecycle completion signal.
        ####################################################

        signal = build_completion_signal(
            session_id=config.session_id,
            lifecycle_status="complete",
            governance_gate_passed=True,
            remote_validation=remote_validation,
        )

        write_json(
            DEFAULT_COMPLETION_SIGNAL,
            signal,
        )

        report: Dict[str, Any] = {
            "schema": BRIDGE_SCHEMA,
            "generated_at": utc_now_iso(),
            "mode": "poll_completion",
            "completion_result": {
                "ok": True,
                "audit_session_id": config.session_id,
                "signal_path": str(DEFAULT_COMPLETION_SIGNAL),
            },
            "remote_completion": remote_validation,
        }

        if safe_token_result is not None:
            report["token_result"] = safe_token_result

        write_json(
            report_out,
            report,
        )

        print(
            "[RGA-BRIDGE][OK] "
            "Lifecycle completion signal written."
        )

        print(
            f"[RGA-BRIDGE][SIGNAL] "
            f"{DEFAULT_COMPLETION_SIGNAL}"
        )

        print(
            f"[RGA-BRIDGE][REPORT] "
            f"{report_out}"
        )

        return 0

    ########################################################
    # Standard bridge path.
    #
    # Modes:
    #   dry-run
    #   dispatch
    #   commit-baseline
    #   commit-and-dispatch
    #   create-pr
    ########################################################

    baseline_validation = validate_runtime_baseline(
        config.baseline_path
    )

    path_validation = validate_remote_path(
        config.remote_path
    )

    request_payload = build_workflow_dispatch_payload(
        config
    )

    report: Dict[str, Any] = {
        "schema": BRIDGE_SCHEMA,
        "generated_at": utc_now_iso(),
        "mode": (
            "commit_and_dispatch"
            if config.commit_and_dispatch
            else "commit_baseline"
            if config.commit_baseline
            else "dispatch"
            if config.dispatch
            else "dry_run"
        ),
        "repository": {
            "owner": config.owner,
            "repo": config.repo,
            "workflow": config.workflow,
            "dispatch_ref": resolve_effective_dispatch_ref(
                config
            ),
            "base_branch": config.base_branch,
            "target_branch": config.target_branch,
            "remote_path": config.remote_path,
        },
        "runtime_baseline": baseline_validation,
        "remote_path_validation": path_validation,
        "workflow_dispatch": {
            "url": workflow_dispatch_url(config),
            "payload": request_payload,
        },
        "governance": {
            "completed_phases_remain_immutable": True,
            "bridge_is_non_destructive": True,
            "bridge_commits_only_governance_evidence": True,
            "bridge_does_not_commit_runtime_dbs": True,
            "validation_is_not_verification": True,
            "deployment_gate_required": True,
        },
    }

    write_json(
        request_out,
        request_payload,
    )

    ########################################################
    # Runtime baseline validation.
    ########################################################

    if not baseline_validation.get("valid"):

        report["dispatch_result"] = {
            "attempted": False,
            "ok": False,
            "reason": baseline_validation.get("reason"),
        }

        write_json(
            report_out,
            report,
        )

        print(
            "[RGA-BRIDGE][FAIL] "
            f"runtime baseline invalid: "
            f"{baseline_validation.get('reason')}"
        )

        print(
            f"[RGA-BRIDGE][REPORT] {report_out}"
        )

        return 2

    ########################################################
    # Remote path validation.
    ########################################################

    if not path_validation.get("valid"):

        report["commit_result"] = {
            "attempted": False,
            "ok": False,
            "reason": path_validation.get("reason"),
        }

        write_json(
            report_out,
            report,
        )

        print(
            "[RGA-BRIDGE][FAIL] "
            f"remote path rejected: "
            f"{path_validation.get('reason')}"
        )

        print(
            f"[RGA-BRIDGE][REPORT] {report_out}"
        )

        return 5

    ########################################################
    # Token resolution for mutation / dispatch paths.
    ########################################################

    token: Optional[str] = None

    needs_token = (
        config.dispatch
        or config.commit_baseline
        or config.commit_and_dispatch
        or config.create_pr
    )

    if needs_token:

        token_result = resolve_github_api_token(
            config,
        )

        if not token_result.get("ok"):

            report["token_result"] = token_result

            write_json(
                report_out,
                report,
            )

            print(
                "[RGA-BRIDGE][FAIL] "
                "GitHub credentials unavailable. "
                "Configure GitHub App environment variables "
                "or use --auth-mode token with a valid fallback token."
            )

            print(
                f"[RGA-BRIDGE][REPORT] {report_out}"
            )

            return 3

        token = token_result["token"]

        safe_token_result = dict(token_result)
        safe_token_result.pop(
            "token",
            None,
        )

        report["token_result"] = safe_token_result

    ########################################################
    # Commit runtime baseline.
    ########################################################

    if config.commit_baseline or config.commit_and_dispatch:

        assert token is not None

        commit_result = commit_runtime_baseline_to_github(
            config=config,
            token=token,
        )

        report["commit_result"] = commit_result

        if not commit_result.get("ok"):

            write_json(
                report_out,
                report,
            )

            print(
                "[RGA-BRIDGE][FAIL] "
                "baseline commit failed: "
                f"{commit_result.get('reason') or commit_result.get('stage')}"
            )

            print(
                f"[RGA-BRIDGE][REPORT] {report_out}"
            )

            return 6

        ####################################################
        # Optional pull request creation.
        ####################################################

        if config.create_pr:

            pr_result = create_pull_request(
                config=config,
                token=token,
            )

            report["pull_request_result"] = {
                "attempted": True,
                **pr_result,
            }

            if not pr_result.get("ok"):

                write_json(
                    report_out,
                    report,
                )

                print(
                    "[RGA-BRIDGE][FAIL] "
                    "PR creation failed: "
                    f"{pr_result.get('status')} "
                    f"{pr_result.get('reason')}"
                )

                print(
                    f"[RGA-BRIDGE][REPORT] {report_out}"
                )

                return 7

    ########################################################
    # Workflow dispatch.
    ########################################################

    if config.dispatch or config.commit_and_dispatch:

        assert token is not None

        request_payload = build_workflow_dispatch_payload(
            config
        )

        report["workflow_dispatch"] = {
            "url": workflow_dispatch_url(config),
            "payload": request_payload,
        }

        dispatch_result = dispatch_workflow(
            config=config,
            token=token,
            payload=request_payload,
        )

        report["dispatch_result"] = {
            "attempted": True,
            "dispatch_ref": resolve_effective_dispatch_ref(
                config
            ),
            **dispatch_result,
        }

        if not dispatch_result.get("ok"):

            write_json(
                report_out,
                report,
            )

            print(
                "[RGA-BRIDGE][FAIL] "
                "workflow_dispatch failed: "
                f"{dispatch_result.get('status')} "
                f"{dispatch_result.get('reason')}"
            )

            print(
                f"[RGA-BRIDGE][REPORT] {report_out}"
            )

            return 4

        ####################################################
        # Optional governance backhaul.
        ####################################################

        if dispatch_result.get("ok") and config.wait_and_backhaul:

            time.sleep(5)

            run_id = get_latest_workflow_run_id(
                config=config,
                token=token,
            )

            if run_id:

                backhaul_result = wait_and_backhaul_governance_report(
                    config=config,
                    token=token,
                    run_id=run_id,
                )

                report["backhaul_result"] = backhaul_result

                if not backhaul_result.get("ok"):

                    write_json(
                        report_out,
                        report,
                    )

                    print(
                        "[RGA-BRIDGE][FAIL] "
                        "Governance gate backhaul failed or "
                        "gate reported rejection: "
                        f"{backhaul_result.get('conclusion') or backhaul_result.get('reason')}"
                    )

                    return 8

            else:

                report["backhaul_result"] = {
                    "ok": False,
                    "reason": "could_not_resolve_dispatched_run_id",
                }

                write_json(
                    report_out,
                    report,
                )

                return 9

    ########################################################
    # Dry run reporting.
    ########################################################

    if config.dry_run:

        report["dispatch_result"] = {
            "attempted": False,
            "ok": True,
            "reason": "dry_run",
        }

        report["commit_result"] = {
            "attempted": False,
            "ok": True,
            "reason": "dry_run",
            "target_branch": config.target_branch,
            "remote_path": config.remote_path,
        }

    ########################################################
    # Final report write.
    ########################################################

    write_json(
        report_out,
        report,
    )

    if config.dry_run:

        print(
            "[RGA-BRIDGE][DRY-RUN] "
            "request/report generated; "
            "no GitHub mutation performed."
        )

    else:

        print(
            "[RGA-BRIDGE][OK] "
            "requested bridge operation completed."
        )

    print(
        f"[RGA-BRIDGE][REQUEST] {request_out}"
    )

    print(
        f"[RGA-BRIDGE][REPORT] {report_out}"
    )

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
