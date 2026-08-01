#!/usr/bin/env python3
"""
runtime_verifier.py

RGA Runtime Verifier Bot — v0.3

New in v0.3:
- Discovery Confidence Engine
- Partial Runtime Candidate reporting
- Repository evidence inventory
- Better CI behavior when backend files are partially present

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

Typical CI usage from repository root:

  python tools/runtime_verifier.py \
    --repo-root . \
    --json-out artifacts/runtime_verifier_report.json \
    --md-out artifacts/runtime_verifier_report.md

Strict mode:

  python tools/runtime_verifier.py --repo-root . --strict
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


@dataclass
class CheckResult:
    domain: str
    check: str
    status: str  # pass | warning | fail | skipped | info
    severity: str  # info | warning | fail | critical
    summary: str
    evidence: Dict[str, Any]
    suggested_fix: Optional[str] = None


@dataclass
class RuntimeCandidate:
    root: str
    score: int
    confidence: str
    matched: List[str]
    missing: List[str]


ARTIFACT_WEIGHTS: Dict[str, int] = {
    "main.py": 40,
    "src/rhythm_ingestion/api/recommend.py": 25,
    "src/rhythm_ingestion/api/app.py": 15,
    "src/rhythm_ingestion/runtime_meta.py": 10,
    "mcp_server.py": 10,
}


def _artifact_path(root: Path, artifact: str) -> Path:
    return root.joinpath(*artifact.split("/"))


def score_candidate(root: Path) -> RuntimeCandidate:
    matched: List[str] = []
    missing: List[str] = []
    score = 0
    for artifact, weight in ARTIFACT_WEIGHTS.items():
        if _artifact_path(root, artifact).exists():
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

    return RuntimeCandidate(
        root=str(root.resolve()),
        score=score,
        confidence=confidence,
        matched=matched,
        missing=missing,
    )


def discover_files(search_root: Path) -> Dict[str, List[str]]:
    patterns = {
        "main.py": "main.py",
        "recommend.py": "recommend.py",
        "app.py": "app.py",
        "runtime_meta.py": "runtime_meta.py",
        "mcp_server.py": "mcp_server.py",
    }
    out: Dict[str, List[str]] = {k: [] for k in patterns}
    try:
        for path in search_root.rglob("*"):
            if path.is_file():
                name = path.name
                for label, expected_name in patterns.items():
                    if name == expected_name:
                        out[label].append(str(path.resolve()))
    except Exception:
        pass
    for k in out:
        out[k] = sorted(out[k])
    return out


def discover_runtime_candidates(search_root: Path) -> List[RuntimeCandidate]:
    search_root = search_root.resolve()
    roots: Dict[str, Path] = {}

    # Candidate roots are directories containing main.py or ancestors of key files.
    try:
        for main_py in search_root.rglob("main.py"):
            roots[str(main_py.parent.resolve())] = main_py.parent.resolve()
        for rec_py in search_root.rglob("recommend.py"):
            # Try walking upward until a src/rhythm_ingestion layout is found.
            for parent in [rec_py.parent, *rec_py.parents]:
                if (parent / "src" / "rhythm_ingestion").exists() or parent.name == "src":
                    if parent.name == "src":
                        candidate = parent.parent
                    else:
                        candidate = parent
                    roots[str(candidate.resolve())] = candidate.resolve()
                    break
    except Exception:
        pass

    candidates = [score_candidate(p) for p in roots.values()]
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


def choose_backend_root(repo_root: Path, explicit_backend_root: Optional[Path]) -> Tuple[Path, List[RuntimeCandidate], str]:
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
        self.discovered_files = discover_files(self.repo_root)

    def classify(self, *, domain: str, check: str, base_status: str) -> Tuple[str, str]:
        if domain == "environment" and check == "softr_api_token_present":
            if self.token:
                return "pass", "info"
            if self.run_rest:
                return "fail", "fail"
            return "warning", "warning"

        if domain == "mcp" and check == "config_present" and base_status == "skipped":
            return "skipped", "info"

        if domain == "repo" and base_status == "warning":
            if self.backend_root_mode in {"auto_discovered", "explicit"}:
                return "warning", "warning"
            if self.backend_root_mode == "partial_discovery":
                return "warning", "warning"
            return "fail", "fail"

        if domain == "repository_discovery" and check == "runtime_candidate_confidence":
            # Partial discovery is a warning, not fail. It means the repo has some backend evidence.
            if base_status == "warning":
                return "warning", "warning"

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

    def _inject_pythonpath(self) -> None:
        src = self.backend_root / "src"
        src_pkg = src / "rhythm_ingestion"
        for p in [str(src), str(src_pkg), str(self.backend_root)]:
            if p not in sys.path:
                sys.path.insert(0, p)

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
            evidence={"token_present": token_present, "rest_checks_enabled": self.run_rest},
            suggested_fix=None if token_present else "Set SOFTR_API_TOKEN or pass --token when running REST verification.",
        )

    def check_repository_discovery(self) -> None:
        candidates = [asdict(c) for c in self.backend_candidates]
        best = candidates[0] if candidates else None
        if self.backend_root_mode == "auto_discovered":
            status = "pass"
            summary = "Backend root was discovered with sufficient confidence."
        elif self.backend_root_mode == "partial_discovery":
            status = "warning"
            summary = "Partial runtime candidate was discovered, but required backend artifacts are missing."
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
            },
            suggested_fix=(
                None
                if status == "pass"
                else "Ensure the backend root contains main.py plus src/rhythm_ingestion/api/recommend.py, app.py, runtime_meta.py, and mcp_server.py; or pass --backend-root explicitly."
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
                summary=f"{name} {'exists' if exists else 'was not found'} at selected backend root.",
                evidence={"path": str(path), "exists": exists, "backend_root": str(self.backend_root)},
            )

    def check_python_imports(self) -> None:
        self._inject_pythonpath()
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
                suggested_fix="Verify backend root discovery and PYTHONPATH include selected_backend_root/src and selected_backend_root/src/rhythm_ingestion.",
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
                summary="Required runtime metadata artifact specs are registered." if not missing else "Some runtime metadata artifact specs are missing.",
                evidence={"required": required, "missing": missing, "registered": sorted(list(specs.keys()))},
                suggested_fix=None if not missing else "Add missing artifact keys to ARTIFACT_SPECS in runtime_meta.py.",
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
            self.add(domain="mcp", check="config_present", status="skipped", summary="No MCP config path was provided.", evidence={})
            return
        if not self.mcp_config.exists():
            self.add(domain="mcp", check="config_present", status="warning", summary="Provided MCP config path does not exist.", evidence={"path": str(self.mcp_config)})
            return
        data = self._read_json_file(self.mcp_config)
        if data is None:
            return
        servers = data.get("servers", {}) if isinstance(data, dict) else {}
        server = servers.get("rhythm-game-assistant") if isinstance(servers, dict) else None
        if not server:
            self.add(domain="mcp", check="rga_server_defined", status="fail", summary="rhythm-game-assistant MCP server is not defined.", evidence={"path": str(self.mcp_config)})
            return
        server_type = server.get("type")
        self.add(
            domain="mcp",
            check="rga_server_shape",
            status="pass" if server_type == "stdio" else "fail",
            summary="RGA MCP server is configured as stdio." if server_type == "stdio" else "RGA MCP server should use stdio adapter mode, not direct REST HTTP mode.",
            evidence={"type": server_type, "command": server.get("command"), "args": server.get("args", []), "env_keys": sorted(list((server.get("env") or {}).keys()))},
            suggested_fix=None if server_type == "stdio" else "Use mcp_server.py as a local stdio MCP adapter and forward to RGA_REST_URL.",
        )

    def _post_json(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.token:
            raise RuntimeError("SOFTR_API_TOKEN is missing; cannot run REST verification.")
        req = urllib.request.Request(
            self.api_url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json", "ngrok-skip-browser-warning": "true"},
        )
        with urllib.request.urlopen(req, timeout=30) as res:
            raw = res.read().decode("utf-8")
            return json.loads(raw) if raw else {"ok": True, "status": res.status}

    def check_rest_contract(self) -> None:
        if not self.run_rest:
            self.add(domain="rest_api", check="rest_verification_enabled", status="skipped", summary="REST checks were skipped. Use --rest to enable REST verification.", evidence={"api_url": self.api_url})
            return
        payloads = {
            "song_mode_post": {
                "mode": "song", "game_id": "proseka", "locale": "en-US", "max_items": 1,
                "song_ids": ["local-test-song"], "player_signals": {}, "player_profile": {}, "player_history": {}, "preferences": {}, "evidence": {},
            },
            "game_mode_post": {
                "mode": "game", "game_id": "proseka", "locale": "en-US", "max_items": 3,
                "player_signals": {"expert_fc_count": "120", "master_fc_count": "20", "highest_confirmed_difficulty": "32"},
                "player_profile": {}, "player_history": {}, "preferences": {}, "evidence": {},
            },
        }
        for check, payload in payloads.items():
            try:
                result = self._post_json(payload)
                self.add(domain="rest_api", check=check, status="pass", summary=f"{check} completed.", evidence={"response_keys": sorted(list(result.keys())) if isinstance(result, dict) else []})
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                summary = f"{check} returned HTTP {exc.code}."
                if check == "game_mode_post" and exc.code == 501 and "Games recommender not configured" in body:
                    summary = "Game mode confirms games_recommender is not configured."
                self.add(domain="rest_api", check=check, status="fail", summary=summary, evidence={"status": exc.code, "body": body}, suggested_fix="Inject a Phase 7 games_recommender into create_app(...)." if exc.code == 501 else None)
            except Exception as exc:
                self.add(domain="rest_api", check=check, status="fail", summary=f"{check} failed.", evidence={"error": str(exc)})

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
            "schema": "rga.runtime_verifier.report.v3",
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "repo_root": str(self.repo_root),
            "backend_root": str(self.backend_root),
            "backend_root_mode": self.backend_root_mode,
            "backend_root_candidates": [asdict(c) for c in self.backend_candidates],
            "discovered_files": self.discovered_files,
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
    lines.append("## Backend Candidates")
    lines.append("```json")
    lines.append(json.dumps(report.get("backend_root_candidates", []), indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")
    lines.append("## Discovered Files")
    lines.append("```json")
    lines.append(json.dumps(report.get("discovered_files", {}), indent=2, ensure_ascii=False))
    lines.append("```")
    lines.append("")
    lines.append("## Results")
    for item in report.get("results", []):
        lines.append(f"### [{item['status'].upper()} / {item['severity'].upper()}] {item['domain']} / {item['check']}")
        lines.append("")
        lines.append(item.get("summary", ""))
        evidence = item.get("evidence") or {}
        if evidence:
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(evidence, indent=2, ensure_ascii=False))
            lines.append("```")
        if item.get("suggested_fix"):
            lines.append("")
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
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any fail severity results are found.")
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
