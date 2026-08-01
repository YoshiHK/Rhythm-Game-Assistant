#!/usr/bin/env python3
"""
runtime_verifier.py

RGA Runtime Verifier Bot — v0.1

Purpose:
- Read-only runtime / wiring verification for Rhythm Game Assistant (RGA).
- Detect missing runtime components, REST contract issues, MCP config issues,
  and likely wiring gaps such as games_recommender not being injected.

Boundary:
- This script is verification-only.
- It must not modify Completed Phases 1–7.
- It must not write to production databases.
- It must not change canonical_row, pattern/tag logic, tips generation,
  personalization, localization, or recommendation internals.

Recommended placement:
- tools/runtime_verifier.py

Typical usage from backend root:

  python .\tools\runtime_verifier.py --repo-root . --json-out .\artifacts\runtime_verifier_report.json

REST verification, if backend is running:

  python .\tools\runtime_verifier.py --repo-root . --rest --api-url http://127.0.0.1:8000/api/v1/recommend

Strict mode for CI:

  python .\tools\runtime_verifier.py --repo-root . --strict
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
from typing import Any, Dict, List, Optional


# -----------------------------------------------------------------------------
# Result model
# -----------------------------------------------------------------------------

@dataclass
class CheckResult:
    domain: str
    check: str
    status: str  # pass | warning | fail | skipped | info
    summary: str
    evidence: Dict[str, Any]
    suggested_fix: Optional[str] = None


class RuntimeVerifier:
    def __init__(
        self,
        *,
        repo_root: Path,
        api_url: str,
        token: Optional[str],
        mcp_config: Optional[Path],
        run_rest: bool,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.api_url = api_url
        self.token = token or os.getenv("SOFTR_API_TOKEN")
        self.mcp_config = mcp_config
        self.run_rest = run_rest
        self.results: List[CheckResult] = []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
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
        self.results.append(
            CheckResult(
                domain=domain,
                check=check,
                status=status,
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
                else "SOFTR_API_TOKEN is missing from the verifier process."
            ),
            evidence={"token_present": token_present},
            suggested_fix=(
                None
                if token_present
                else "Set SOFTR_API_TOKEN as a Windows User environment variable or export it before running the verifier."
            ),
        )

    def check_repo_shape(self) -> None:
        expected = {
            "main.py": self.repo_root / "main.py",
            "src": self.repo_root / "src",
            "api_recommend.py": self.repo_root / "src" / "rhythm_ingestion" / "api" / "recommend.py",
            "api_app.py": self.repo_root / "src" / "rhythm_ingestion" / "api" / "app.py",
            "runtime_meta.py": self.repo_root / "src" / "rhythm_ingestion" / "runtime_meta.py",
            "mcp_server.py": self.repo_root / "mcp_server.py",
        }

        for name, path in expected.items():
            exists = path.exists()
            self.add(
                domain="repo",
                check=f"exists_{name}",
                status="pass" if exists else "warning",
                summary=f"{name} {'exists' if exists else 'was not found'}.",
                evidence={"path": str(path), "exists": exists},
            )

    def check_python_imports(self) -> None:
        src = self.repo_root / "src"
        src_pkg = src / "rhythm_ingestion"
        for p in [str(src), str(src_pkg), str(self.repo_root)]:
            if p not in sys.path:
                sys.path.insert(0, p)

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
                suggested_fix="Verify PYTHONPATH includes ./src and ./src/rhythm_ingestion, and check syntax/import errors in API files.",
            )

    def check_runtime_meta_specs(self) -> None:
        src = self.repo_root / "src"
        src_pkg = src / "rhythm_ingestion"
        for p in [str(src), str(src_pkg), str(self.repo_root)]:
            if p not in sys.path:
                sys.path.insert(0, p)

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

        # Song mode minimal schema check.
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

        # Game mode should either pass if recommender exists, or produce known 501 if missing.
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
                evidence={"response_keys": sorted(list(game_result.keys())), "items_count": len(game_result.get("items", [])) if isinstance(game_result, dict) else None},
            )
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            status = "fail"
            summary = f"Game mode REST request returned HTTP {exc.code}."
            if exc.code == 501 and "Games recommender not configured" in body:
                summary = "Game mode confirms games_recommender is not configured."
            self.add(
                domain="rest_api",
                check="game_mode_post",
                status=status,
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
        self.check_repo_shape()
        self.check_python_imports()
        self.check_runtime_meta_specs()
        self.check_mcp_config()
        self.check_rest_contract()

        counts: Dict[str, int] = {}
        for result in self.results:
            counts[result.status] = counts.get(result.status, 0) + 1

        return {
            "schema": "rga.runtime_verifier.report.v1",
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "repo_root": str(self.repo_root),
            "api_url": self.api_url,
            "summary": counts,
            "results": [asdict(r) for r in self.results],
        }


def write_markdown(report: Dict[str, Any], out_path: Path) -> None:
    lines: List[str] = []
    lines.append("# RGA Runtime Verifier Report")
    lines.append("")
    lines.append(f"Generated: `{report.get('generated_at')}`")
    lines.append(f"Repo root: `{report.get('repo_root')}`")
    lines.append(f"API URL: `{report.get('api_url')}`")
    lines.append("")
    lines.append("## Summary")
    for k, v in sorted(report.get("summary", {}).items()):
        lines.append(f"- **{k}**: {v}")
    lines.append("")
    lines.append("## Results")
    for item in report.get("results", []):
        lines.append(f"### [{item['status'].upper()}] {item['domain']} / {item['check']}")
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
    parser.add_argument("--repo-root", default=".", help="Backend repository root containing main.py and src/.")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000/api/v1/recommend", help="RGA REST recommend endpoint.")
    parser.add_argument("--token", default=None, help="Bearer token. Defaults to SOFTR_API_TOKEN environment variable.")
    parser.add_argument("--mcp-config", default=None, help="Optional path to VS Code mcp.json.")
    parser.add_argument("--rest", action="store_true", help="Run REST endpoint checks. Requires backend to be running.")
    parser.add_argument("--json-out", default=None, help="Optional JSON report output path.")
    parser.add_argument("--md-out", default=None, help="Optional Markdown report output path.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any fail results are found.")
    args = parser.parse_args()

    verifier = RuntimeVerifier(
        repo_root=Path(args.repo_root),
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

    if args.strict and report.get("summary", {}).get("fail", 0) > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
