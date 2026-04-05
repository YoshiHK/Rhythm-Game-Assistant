"""CI Self-tests: Lock token parity CI SUMMARY format + single-line guarantee.

This file merges two micro-tests:
1) Summary format lock (required key=value tokens present)
2) Summary single-line lock (exactly one physical line, no fragments/escapes)

These tests are non-semantic: they do not judge localization quality.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


def _run_check(tmp_path: Path) -> tuple[int, str]:
    """Run the token parity check in an isolated repo-like temp directory."""
    repo = tmp_path / 'repo'
    (repo / 'ci').mkdir(parents=True)
    (repo / 'translations' / 'en-US' / 'templates').mkdir(parents=True)
    (repo / 'translations' / 'ja-JP' / 'templates').mkdir(parents=True)

    base_tpl = {"strings": {"default": "Play {song_name} on {difficulty}"}}
    (repo / 'translations' / 'en-US' / 'templates' / 't.json').write_text(json.dumps(base_tpl), encoding='utf-8')
    (repo / 'translations' / 'ja-JP' / 'templates' / 't.json').write_text(json.dumps(base_tpl), encoding='utf-8')

    waiver_cfg = {
        "version": 4,
        "description": "self-test",
        "budget": {"max_total": 5, "per_locale": {"ja-JP": 2}},
        "decay": {"require_review_by": True, "warn_before_days": 7, "fail_on_expired": True},
        "waivers": [],
    }
    (repo / 'ci' / 'token_parity_waivers.json').write_text(json.dumps(waiver_cfg), encoding='utf-8')

    src = Path('ci/check_token_parity_per_string.py')
    assert src.exists(), 'Expected ci/check_token_parity_per_string.py to exist in repo'
    (repo / 'ci' / 'check_token_parity_per_string.py').write_text(src.read_text(encoding='utf-8'), encoding='utf-8')

    proc = subprocess.run(
        [sys.executable, str(repo / 'ci' / 'check_token_parity_per_string.py')],
        cwd=str(repo),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout


def test_ci_summary_line_format(tmp_path: Path) -> None:
    code, out = _run_check(tmp_path)
    assert code == 0, f"Expected pass exit code 0, got {code}\nOutput:\n{out}"

    summary_lines = [ln for ln in out.splitlines() if ln.startswith('CI SUMMARY:')]
    assert len(summary_lines) == 1, f"Expected exactly 1 CI SUMMARY line, got {len(summary_lines)}\nOutput:\n{out}"

    line = summary_lines[0]
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

    assert re.search(r"status=(PASS|FAIL)", line), f"Invalid status token: {line}"
    assert re.search(r"suggested_review_by=\d{4}-\d{2}-\d{2}", line), f"Missing/invalid suggested_review_by: {line}"


def test_ci_summary_is_single_line(tmp_path: Path) -> None:
    code, out = _run_check(tmp_path)
    assert code == 0, f"Expected pass exit code 0, got {code}\nOutput:\n{out}"

    lines = out.splitlines()
    summary_lines = [ln for ln in lines if ln.startswith('CI SUMMARY:')]
    assert len(summary_lines) == 1, f"Expected exactly 1 CI SUMMARY line, got {len(summary_lines)}\nOutput:\n{out}"

    other_mentions = [ln for ln in lines if (not ln.startswith('CI SUMMARY:') and 'CI SUMMARY:' in ln)]
    assert not other_mentions, f"Found 'CI SUMMARY:' in non-summary lines: {other_mentions}"

    summary = summary_lines[0]
    assert '\\n' not in summary and '\\r' not in summary, f"Summary line contains escaped newline tokens: {summary}"
    assert len(summary) > len('CI SUMMARY:'), f"Summary line appears truncated: {summary}"
