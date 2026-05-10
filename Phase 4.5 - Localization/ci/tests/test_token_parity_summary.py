"""
CI Infrastructure Test: Token Parity CI SUMMARY Contract

Purpose:
- Lock the CI SUMMARY output format for token parity checks
- Ensure exactly one physical summary line is emitted
- Ensure the line is machine-consumable for observability scraping

Non-goals:
- Localization policy validation
- Translation correctness
- Token parity correctness itself
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Tuple


def _run_check(tmp_path: Path) -> Tuple[int, str]:
    """
    Run the token parity check in an isolated, repo-like temp directory.
    """
    repo = tmp_path / "repo"
    (repo / "ci").mkdir(parents=True)
    (repo / "translations" / "_meta").mkdir(parents=True)
    (repo / "translations" / "en-US" / "templates").mkdir(parents=True)
    (repo / "translations" / "ja-JP" / "templates").mkdir(parents=True)

    # Minimal locales.json
    locales = {"supported_locales": ["en-US", "ja-JP"]}
    (repo / "translations" / "_meta" / "locales.json").write_text(
        json.dumps(locales),
        encoding="utf-8",
    )

    # Minimal identical template (no mismatches)
    tpl = {"strings": {"default": {"text": "Play {song_name} on {difficulty}"}}}
    (repo / "translations" / "en-US" / "templates" / "t.json").write_text(
        json.dumps(tpl),
        encoding="utf-8",
    )
    (repo / "translations" / "ja-JP" / "templates" / "t.json").write_text(
        json.dumps(tpl),
        encoding="utf-8",
    )

    # Minimal waivers config (no versioning semantics)
    waiver_cfg = {
        "format": "stable",
        "budget": {"max_total": 0},
        "waivers": [],
    }
    (repo / "ci" / "token_parity_waivers.json").write_text(
        json.dumps(waiver_cfg),
        encoding="utf-8",
    )

    # Copy the actual check under test
    src = Path("ci/check_token_parity_per_string.py")
    assert src.exists(), "Expected ci/check_token_parity_per_string.py to exist"
    (repo / "ci" / "check_token_parity_per_string.py").write_text(
        src.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    proc = subprocess.run(
        [sys.executable, str(repo / "ci" / "check_token_parity_per_string.py")],
        cwd=str(repo),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout


def test_ci_summary_line_format(tmp_path: Path) -> None:
    code, out = _run_check(tmp_path)
    assert code == 0, f"Expected exit code 0, got {code}\nOutput:\n{out}"

    summary_lines = [ln for ln in out.splitlines() if ln.startswith("CI SUMMARY:")]
    assert len(summary_lines) == 1, (
        f"Expected exactly 1 CI SUMMARY line, got {len(summary_lines)}\nOutput:\n{out}"
    )

    line = summary_lines[0]

    # Required tokens (order-independent)
    required = [
        "status=",
        "mismatches=",
        "waivers_used=",
        "invalid_waivers=",
    ]
    for k in required:
        assert k in line, f"Missing '{k}' in CI SUMMARY line: {line}"

    assert re.search(r"status=(PASS|FAIL)", line), f"Invalid status token: {line}"
    assert re.search(r"mismatches=\d+", line), f"Invalid mismatches token: {line}"
    assert re.search(r"waivers_used=\d+", line), f"Invalid waivers_used token: {line}"
    assert re.search(r"invalid_waivers=\d+", line), f"Invalid invalid_waivers token: {line}"


def test_ci_summary_is_single_line(tmp_path: Path) -> None:
    code, out = _run_check(tmp_path)
    assert code == 0, f"Expected exit code 0, got {code}\nOutput:\n{out}"

    lines = out.splitlines()
    summary_lines = [ln for ln in lines if ln.startswith("CI SUMMARY:")]
    assert len(summary_lines) == 1, (
        f"Expected exactly 1 CI SUMMARY line, got {len(summary_lines)}\nOutput:\n{out}"
    )

    summary = summary_lines[0]

    # Ensure no embedded or escaped newlines
    assert "\n" not in summary and "\r" not in summary, (
        f"CI SUMMARY line contains newline tokens: {summary}"
    )
    assert len(summary) > len("CI SUMMARY:"), f"CI SUMMARY line appears truncated: {summary}"