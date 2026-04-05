"""CI Self-test: Lock token parity summary line format.

This test runs the token parity check in an isolated temp repo layout and asserts
that the final output contains exactly one CI SUMMARY line matching the expected
key structure.

Why:
- Downstream CI parsing and dashboards depend on a stable summary line.
- We lock the format without judging translation semantics.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


def test_ci_summary_line_format(tmp_path: Path) -> None:
    # Create isolated repo-like structure
    repo = tmp_path / 'repo'
    (repo / 'ci').mkdir(parents=True)
    (repo / 'translations' / 'en-US' / 'templates').mkdir(parents=True)
    (repo / 'translations' / 'ja-JP' / 'templates').mkdir(parents=True)

    # Minimal templates with identical placeholder tokens
    base_tpl = {
        "strings": {
            "default": "Play {song_name} on {difficulty}"
        }
    }
    import json
    (repo / 'translations' / 'en-US' / 'templates' / 't.json').write_text(json.dumps(base_tpl), encoding='utf-8')
    (repo / 'translations' / 'ja-JP' / 'templates' / 't.json').write_text(json.dumps(base_tpl), encoding='utf-8')

    # Waiver config (no waivers needed; include decay/budgets to exercise parsing)
    waiver_cfg = {
        "version": 4,
        "description": "self-test",
        "budget": {"max_total": 5, "per_locale": {"ja-JP": 2}},
        "decay": {"require_review_by": True, "warn_before_days": 7, "fail_on_expired": True},
        "waivers": []
    }
    (repo / 'ci' / 'token_parity_waivers.json').write_text(json.dumps(waiver_cfg), encoding='utf-8')

    # Copy the check script under test into repo/ci/
    # Assumes the real file exists in the working tree when CI runs.
    src = Path('ci/check_token_parity_per_string.py')
    assert src.exists(), 'Expected ci/check_token_parity_per_string.py to exist in repo'
    (repo / 'ci' / 'check_token_parity_per_string.py').write_text(src.read_text(encoding='utf-8'), encoding='utf-8')

    # Execute
    proc = subprocess.run(
        [sys.executable, str(repo / 'ci' / 'check_token_parity_per_string.py')],
        cwd=str(repo),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )

    out = proc.stdout
    assert proc.returncode == 0, f"Expected pass exit code 0, got {proc.returncode}
Output:
{out}"

    # Must contain exactly one summary line.
    summary_lines = [ln for ln in out.splitlines() if ln.startswith('CI SUMMARY:')]
    assert len(summary_lines) == 1, f"Expected exactly 1 CI SUMMARY line, got {len(summary_lines)}
Output:
{out}"

    line = summary_lines[0]

    # Format lock: require key=value tokens to be present.
    required_keys = [
        'status=',
        'base=',
        'waived_total=',
        'waived_by_locale=',
        'per_locale_budget=',
        'decay=',
        'suggested_review_by=',
        'reason=',
    ]
    for k in required_keys:
        assert k in line, f"Missing '{k}' in summary line: {line}"

    # Basic structure checks
    assert re.search(r"status=(PASS|FAIL)", line), f"Invalid status token: {line}"
    assert re.search(r"suggested_review_by=\d{4}-\d{2}-\d{2}", line), f"Missing/invalid suggested_review_by: {line}"
