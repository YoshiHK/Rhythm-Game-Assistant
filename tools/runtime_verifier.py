#!/usr/bin/env python3
"""
runtime_verifier.py

RGA Runtime Verifier Bot — v0.2

New in v0.2:
- Repository Discovery
- Runtime Root Discovery
- Severity Classification

Purpose:
- Read-only runtime / wiring verification for Rhythm Game Assistant (RGA).
- Detect missing runtime components, REST contract issues, MCP config issues,
  and likely wiring gaps such as games_recommender not being injected.

Boundary:
- Verification-only.
- Must not modify Completed Phases 1–7.
- Must not write to production databases.
- Must not change canonical_row, pattern/tag logic, tips generation,
  personalization, localization, or recommendation internals.

Recommended placement:
- tools/runtime_verifier.py

Typical usage from repo root:

  python tools/runtime_verifier.py --json-out artifacts/runtime_verifier_report.json

Typical usage from backend root:

  python tools/runtime_verifier.py --repo-root . --json-out artifacts/runtime_verifier_report.json

REST verification, if backend is running:

  python tools/runtime_verifier.py --rest --api-url http://127.0.0.1:8000/api/v1/recommend

Strict mode for CI:

  python tools/runtime_verifier.py --strict

Notes:
- If --repo-root is not the backend root, v0.2 attempts to auto-discover the backend root.
- In CI without --rest, missing SOFTR_API_TOKEN is classified as warning, not fail.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import platform
import sys
import traceback
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------------------------------------------------------
# Result model
# -----------------------------------------------------------------------------

@dataclass
class CheckResult:
    domain: str
    check: str
    status: str  # pass | warning | fail | skipped | info
    severity: str  # info | warning | fail | critical
    summary: str
    evidence: Dict[str, Any]
    suggested_fix: Optional[str] = None


# -----------------------------------------------------------------------------
# Discovery helpers
# -----------------------------------------------------------------------------

def _is_backend_root(path: Path) -> bool:
    """Return True if path looks like the RGA FastAPI backend root."""
    return (
        (path / "main.py").exists()
        and (path / "src" / "rhythm_ingestion" / "api" / "recommend.py").exists()
        and (path / "src" / "rhythm_ingestion" / "api" / "app.py").exists()
        and (path / "src" / "rhythm_ingestion" / "runtime_meta.py").exists()
    )


def discover_backend_roots(search_root: Path) -> List[Path]:
    """Find candidate backend roots under search_root."""
    search_root = search_root.resolve()
    candidates: List[Path] = []

    # Fast path: given root is already backend root.
    if _is_backend_root(search_root):
        return [search_root]

    # Find main.py candidates, then verify nearby src layout.
    try:
        for main_py in search_root.rglob("main.py"):
            candidate = main_py.parent
            if _is_backend_root(candidate):
                candidates.append(candidate.resolve())
    except Exception:
        # Some CI paths may be inaccessible; keep verifier non-crashing.
        pass

    # Deduplicate while preserving order.
    seen = set()
    unique: List[Path] = []
    for c in candidates:
        key = str(c).casefold()
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def choose_backend_root(repo_root: Path, explicit_backend_root: Optional[Path]) -> Tuple[Path, List[Path], str]:
    """Choose runtime backend root and return (root, candidates, mode)."""
    if explicit_backend_root:
        return explicit_backend_root.resolve(), [explicit_backend_root.resolve()], "explicit"

    candidates = discover_backend_roots(repo_root)
    if candidates:
        return candidates[0], candidates, "auto_discovered"

    return repo_root.resolve(), [], "fallback_to_repo_root"


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
        self.results: List[CheckResult] = []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def classify(
        self,
        *,
        domain: str,
        check: str,
        base_status: str,
    ) -> Tuple[str, str]:
        """Return (status, severity) after context-aware severity classification."""
        # Missing token only blocks REST verification. If --rest is off, warning is enough.
        if domain == "environment" and check == "softr_api_token_present":
            if self.token:
                return "pass", "info"
            if self.run_rest:
                return "fail", "fail"
            return "warning", "warning"

        # Missing MCP config is informational unless explicitly provided and invalid.
        if domain == "mcp" and check == "config_present" and base_status == "skipped":
            return "skipped", "info"

        # Repo shape warnings are fail only if no backend root could be found.
        if domain == "repo" and base_status == "warning":
            if self.backend_root_mode == "fallback_to_repo_root":
                return "fail", "fail"
            return "pass", "info"

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
    ) -> None:
        final_status, severity = self.classify(domain=domain, check=check, base_status=status)
        self.results.append(
            CheckResult(
                domain=domain,
                check=check,
                status=final_status,
                severity=severity,
                summary=summary,
                evidence=evidence or {},
                suggested_fix=suggested_fix,
            )
        )

    def _read_json_file(self, path: Path) -> Optional[Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            self.add(
                domain="file",
                check="json_parse",
                status="fail",
                summary=f"Could not parse JSON file: {path}",
                evidence={"path": str(path), "error": str(exc)},
            )
            return None

    def _inject_pythonpath(self) -> None:
        src = self.backend_root / "src"
        src_pkg = src / "rhythm_ingestion"
        for p in [str(src), str(src_pkg), str(self.backend_root)]:
            if p not in sys.path:
                sys.path.insert(0, p)

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
                else (
                    "SOFTR_API_TOKEN is missing from the verifier process. "
                    "This is only a blocking issue when REST checks are enabled."
                )
            ),
            evidence={"token_present": token_present, "rest_checks_enabled": self.run_rest},
            suggested_fix=(
                None
                if token_present
                else "Set SOFTR_API_TOKEN or pass --token when running REST verification."
            ),
        )

    def check_repository_discovery(self) -> None:
        found = bool(self.backend_candidates)
        self.add(
            domain="repository_discovery",
            check="backend_root_discovery",
            status="pass" if found else "warning",
            summary=(
                "Backend root was discovered automatically."
                if self.backend_root_mode == "auto_discovered"
                else (
                    "Backend root was provided explicitly."
                    if self.backend_root_mode == "explicit"
                    else "No backend root was discovered; verifier is falling back to repo root."
                )
            ),
            evidence={
                "repo_root": str(self.repo_root),
                "backend_root": str(self.backend_root),
                "mode": self.backend_root_mode,
                "candidates": [str(c) for c in self.backend_candidates],
            },
            suggested_fix=(
                None
                if found or self.backend_root_mode == "explicit"
                else "Pass --backend-root or ensure backend root contains main.py and src/rhythm_ingestion/api/recommend.py."
            ),
        )

    def check_repo_shape(self) -> None:
        expected = {
            "main.py": self.backend_root / "main.py",
            "src": self.backend_root / "src",
            "api_recommend.py": self.backend_root / "src" / "rhythm_ingestion" / "api" / "recommend.py",
            "api_app.py": self.backend_root / "src" / "rhythm_ingestion" / "api" / "app.py",
            "runtime_meta.py": self.backend_root / "src" / "rhythm_ingestion" / "runtime_meta.py",
            "mcp_server.py": self.backend_root / "mcp_server.py",
        }

        for name, path in expected.items():
            exists = path.exists()
            self.add(
                domain="repo",
                check=f"exists_{name}",
                status="pass" if exists else "warning",
                summary=f"{name} {'exists' if exists else 'was not found'} at backend root.",
                evidence={"path": str(path), "exists": exists, "backend_root": str(self.backend_root)},
            )

    def check_python_imports(self) -> None:
        self._inject_pythonpath()

        try:
            # Clear previously imported module to avoid stale path confusion during local development.
            # This is inspection-only; it does not mutate project files.
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
            )

            if games_rec is None:
                self.add(
                    domain="runtime_wiring",
                    check="games_recommender_present",
                    status="fail",
                    summary="Games recommender is not injected into the Phase 6 API runtime.",
                    evidence={"_GAMES_RECOMMENDER": None},
                    suggested_fix="Inject a Phase 7 games_recommender through create_app(..., games_recommender=...) in the runtime builder.",
                )
            else:
                self.add(
                    domain="runtime_wiring",
                    check="games_recommender_present",
                    status="pass",
                    summary="Games recommender appears to be injected.",
                    evidence={"games_recommender_type": str(type(games_rec))},
                )

        except Exception as exc:
            self.add(
                domain="runtime_import",
                check="recommend_module_importable",
                status="fail",
                summary="Failed to import rhythm_ingestion.api.recommend.",
                evidence={"error": str(exc), "traceback": traceback.format_exc()},
                suggested_fix="Verify backend root discovery and PYTHONPATH include backend_root/src and backend_root/src/rhythm_ingestion.",
            )

    def check_runtime_meta_specs(self) -> None:
        self._inject_pythonpath()

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
            missing = [k for k in required if k not in specs]
            self.add(
                domain="runtime_meta",
                check="artifact_specs",
                status="pass" if not missing else "fail",
                summary=(
                    "Required runtime metadata artifact specs are registered."
                    if not missing
                    else "Some runtime metadata artifact specs are missing."
                ),
                evidence={"required": required, "missing": missing, "registered": sorted(list(specs.keys()))},
                suggested_fix=(None if not missing else "Add missing artifact keys to ARTIFACT_SPECS in runtime_meta.py."),
            )
        except Exception as exc:
            self.add(
                domain="runtime_meta",
                check="artifact_specs",
                status="fail",
                summary="Could not inspect runtime_meta.ARTIFACT_SPECS.",
                evidence={"error": str(exc), "traceback": traceback.format_exc()},
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
                evidence={"path": str(self.mcp_config)},
            )
            return

        data = self._read_json_file(self.mcp_config)
        if data is None:
            return

        servers = data.get("servers", {}) if isinstance(data, dict) else {}
        server = servers.get("rhythm-game-assistant") if isinstance(servers, dict) else None

        if not server:
            self.add(
                domain="mcp",
                check="rga_server_defined",
                status="fail",
                summary="rhythm-game-assistant MCP server is not defined in the config.",
                evidence={"path": str(self.mcp_config)},
            )
            return

        server_type = server.get("type")
        command = server.get("command")
        args = server.get("args", [])
        env = server.get("env", {})

        self.add(
            domain="mcp",
            check="rga_server_shape",
            status="pass" if server_type == "stdio" else "fail",
            summary=(
                "RGA MCP server is configured as stdio."
                if server_type == "stdio"
                else "RGA MCP server should use stdio adapter mode, not direct REST HTTP mode."
            ),
            evidence={
                "type": server_type,
                "command": command,
                "args": args,
                "env_keys": sorted(list(env.keys())) if isinstance(env, dict) else [],
            },
            suggested_fix=(
                None
                if server_type == "stdio"
                else "Use mcp_server.py as a local stdio MCP adapter and forward to RGA_REST_URL."
            ),
        )

    def _post_json(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.token:
            raise RuntimeError("SOFTR_API_TOKEN is missing; cannot run REST verification.")
        req = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "ngrok-skip-browser-warning": "true",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as res:
            raw = res.read().decode("utf-8")
            return json.loads(raw) if raw else {"ok": True, "status": res.status}

    def check_rest_contract(self) -> None:
        if not self.run_rest:
            self.add(
                domain="rest_api",
                check="rest_verification_enabled",
                status="skipped",
                summary="REST checks were skipped. Use --rest to enable REST verification.",
                evidence={"api_url": self.api_url},
            )
            return

        song_payload = {
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
        }

        try:
            song_result = self._post_json(song_payload)
            self.add(
                domain="rest_api",
                check="song_mode_post",
                status="pass",
                summary="Song mode REST request completed.",
                evidence={"response_keys": sorted(list(song_result.keys()))},
            )
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            self.add(
                domain="rest_api",
                check="song_mode_post",
                status="fail",
                summary=f"Song mode REST request returned HTTP {exc.code}.",
                evidence={"status": exc.code, "body": body},
            )
        except Exception as exc:
            self.add(
                domain="rest_api",
                check="song_mode_post",
                status="fail",
                summary="Song mode REST request failed.",
                evidence={"error": str(exc)},
            )

        game_payload = {
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
        }

        try:
            game_result = self._post_json(game_payload)
            self.add(
                domain="rest_api",
                check="game_mode_post",
                status="pass",
                summary="Game mode REST request completed.",
                evidence={
                    "response_keys": sorted(list(game_result.keys())),
                    "items_count": len(game_result.get("items", [])) if isinstance(game_result, dict) else None,
                },
            )
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            summary = f"Game mode REST request returned HTTP {exc.code}."
            if exc.code == 501 and "Games recommender not configured" in body:
                summary = "Game mode confirms games_recommender is not configured."
            self.add(
                domain="rest_api",
                check="game_mode_post",
                status="fail",
                summary=summary,
                evidence={"status": exc.code, "body": body},
                suggested_fix="Inject a Phase 7 games_recommender into create_app(...)." if exc.code == 501 else None,
            )
        except Exception as exc:
            self.add(
                domain="rest_api",
                check="game_mode_post",
                status="fail",
                summary="Game mode REST request failed.",
                evidence={"error": str(exc)},
            )

    def run_all(self) -> Dict[str, Any]:
        self.check_environment()
        self.check_repository_discovery()
        self.check_repo_shape()
        self.check_python_imports()
        self.check_runtime_meta_specs()
        self.check_mcp_config()
        self.check_rest_contract()

        counts: Dict[str, int] = {}
        severities: Dict[str, int] = {}
        for r in self.results:
            counts[r.status] = counts.get(r.status, 0) + 1
            severities[r.severity] = severities.get(r.severity, 0) + 1

        return {
            "schema": "rga.runtime_verifier.report.v2",
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "repo_root": str(self.repo_root),
            "backend_root": str(self.backend_root),
            "backend_root_mode": self.backend_root_mode,
            "backend_root_candidates": [str(c) for c in self.backend_candidates],
            "api_url": self.api_url,
            "summary": counts,
            "severity_summary": severities,
            "results": [asdict(r) for r in self.results],
        }


def write_markdown(report: Dict[str, Any], out_path: Path) -> None:
    lines: List[str] = []
    lines.append("# RGA Runtime Verifier Report")
    lines.append("")
    lines.append(f"Generated: `{report.get('generated_at')}`")
    lines.append(f"Repo root: `{report.get('repo_root')}`")
    lines.append(f"Backend root: `{report.get('backend_root')}`")
    lines.append(f"Backend root mode: `{report.get('backend_root_mode')}`")
    lines.append(f"API URL: `{report.get('api_url')}`")
    lines.append("")
    lines.append("## Summary")
    for k, v in sorted(report.get("summary", {}).items()):
        lines.append(f"- **{k}**: {v}")
    lines.append("")
    lines.append("## Severity Summary")
    for k, v in sorted(report.get("severity_summary", {}).items()):
        lines.append(f"- **{k}**: {v}")
    lines.append("")
    lines.append("## Results")
    for item in report.get("results", []):
        lines.append(f"### [{item['status'].upper()} / {item['severity'].upper()}] {item['domain']} / {item['check']}")
        lines.append("")
        lines.append(item.get("summary", ""))
        lines.append("")
        evidence = item.get("evidence") or {}
        if evidence:
            lines.append("```json")
            lines.append(json.dumps(evidence, indent=2, ensure_ascii=False))
            lines.append("```")
        if item.get("suggested_fix"):
            lines.append(f"Suggested fix: {item['suggested_fix']}")
        lines.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser("RGA Runtime Verifier Bot")
    parser.add_argument("--repo-root", default=".", help="Repository root or backend root.")
    parser.add_argument("--backend-root", default=None, help="Explicit backend root. Overrides auto-discovery.")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000/api/v1/recommend", help="RGA REST recommend endpoint.")
    parser.add_argument("--token", default=None, help="Bearer token. Defaults to SOFTR_API_TOKEN environment variable.")
    parser.add_argument("--mcp-config", default=None, help="Optional path to VS Code mcp.json.")
    parser.add_argument("--rest", action="store_true", help="Run REST endpoint checks. Requires backend to be running.")
    parser.add_argument("--json-out", default=None, help="Optional JSON report output path.")
    parser.add_argument("--md-out", default=None, help="Optional Markdown report output path.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any fail results are found.")
    parser.add_argument("--strict-severity", choices=["fail", "critical"], default="fail", help="Severity threshold used by --strict.")
    args = parser.parse_args()

    verifier = RuntimeVerifier(
        repo_root=Path(args.repo_root),
        backend_root=Path(args.backend_root) if args.backend_root else None,
        api_url=args.api_url,
        token=args.token,
        mcp_config=Path(args.mcp_config).expanduser() if args.mcp_config else None,
        run_rest=args.rest,
    )
    report = verifier.run_all()

    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text)

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")

    if args.md_out:
        write_markdown(report, Path(args.md_out))

    if args.strict:
        severity = report.get("severity_summary", {})
        if args.strict_severity == "critical" and severity.get("critical", 0) > 0:
            return 1
        if args.strict_severity == "fail" and (severity.get("fail", 0) > 0 or severity.get("critical", 0) > 0):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
