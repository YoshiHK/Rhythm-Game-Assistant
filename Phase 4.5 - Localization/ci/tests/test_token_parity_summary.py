"""
CI Infrastructure Test: Token Parity CI SUMMARY Contract

Purpose:
- Lock the CI SUMMARY output format for token parity checks
- Ensure exactly one physical summary line is emitted
- Ensure the line is machine-consumable for observability scraping

Non-goals:
- Localization policy validation
- Translation correctness
- Token parity correctness itself (beyond summary contract)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Tuple


SUMMARY_RE = re.compile(
    r"^CI SUMMARY: token_parity_per_string status=(PASS|FAIL) mismatches=\d+ waivers_used=\d+ expired_waivers=\d+$"
)


def _make_fixture(translations_root: Path) -> None:
    # translations/_meta/locales.json
    meta = translations_root / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "locales.json").write_text(
        """{
  "base_locale": "en-US",
  "supported_locales": ["en-US", "ja-JP"]
}""",
        encoding="utf-8",
    )

    # minimal templates for both locales (layer-based)
    for loc in ["en-US", "ja-JP"]:
        loc_dir = translations_root / loc
        (loc_dir / "chart_level").mkdir(parents=True, exist_ok=True)

        # identical tokens: include one placeholder {base_text} in both
        (loc_dir / "chart_level" / "chart_summary.json").write_text(
            """{
  "template_id": "chart_summary",
  "version": "v3",
  "strings": {
    "default": {
      "text": "Summary: {base_text}",
      "placeholders": ["base_text"]
    }
  }
}""",
            encoding="utf-8",
        )


def _run_check(tmp_path: Path) -> Tuple[int, str]:
    # Create fixture translations
    translations_root = tmp_path / "translations"
    _make_fixture(translations_root)

    # Locate the real check script relative to this test file:
    # Phase 4.5 - Localization/ci/tests/test_token_parity_summary.py
    # -> ../checks/check_token_parity_per_string.py
    ci_dir = Path(__file__).resolve().parent.parent
    check_script = ci_dir / "checks" / "check_token_parity_per_string.py"

    proc = subprocess.run(
        [sys.executable, str(check_script), "--translations-root", str(translations_root)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc.returncode, proc.stdout


def test_ci_summary_line_format(tmp_path: Path) -> None:
    code, out = _run_check(tmp_path)
    assert code == 0, f"Expected exit code 0, got {code}\nOutput:\n{out}"

    summary_lines = [ln for ln in out.splitlines() if ln.startswith("CI SUMMARY:")]
    assert len(summary_lines) == 1, f"Expected exactly 1 CI SUMMARY line, got {len(summary_lines)}\nOutput:\n{out}"
    assert SUMMARY_RE.match(summary_lines[0]), f"CI SUMMARY line format mismatch:\n{summary_lines[0]}"


def test_ci_summary_is_single_line(tmp_path: Path) -> None:
    code, out = _run_check(tmp_path)
    assert code == 0, f"Expected exit code 0, got {code}\nOutput:\n{out}"

    # the summary must be exactly one physical line (no embedded newlines)
    summary_lines = [ln for ln in out.splitlines() if ln.startswith("CI SUMMARY:")]
    assert len(summary_lines) == 1, f"Expected exactly 1 CI SUMMARY line, got {len(summary_lines)}\nOutput:\n{out}"
    assert "\n" not in summary_lines[0], "CI SUMMARY line contains newline characters"