"""CI Self-test: Ensure CI SUMMARY remains a single physical line.

This test is intentionally strict:
- It asserts there is exactly one line that starts with 'CI SUMMARY:'
- It asserts that 'CI SUMMARY:' does not appear in any other line fragments
- It asserts that the summary line contains no embedded newline escapes.

Why:
- Some CI log parsers depend on one-line key/value format.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_ci_summary_is_single_line(tmp_path: Path) -> None:
    repo = tmp_path / 'repo'
    (repo / 'ci').mkdir(parents=True)
    (repo / 'translations' / 'en-US' / 'templates').mkdir(parents=True)
    (repo / 'translations' / 'ja-JP' / 'templates').mkdir(parents=True)

    # Minimal identical templates
    base_tpl = {"strings": {"default": "Play {song_name} on {difficulty}"}}
    (repo / 'translations' / 'en-US' / 'templates' / 't.json').write_text(json.dumps(base_tpl), encoding='utf-8')
    (repo / 'translations' / 'ja-JP' / 'templates' / 't.json').write_text(json.dumps(base_tpl), encoding='utf-8')

    waiver_cfg = {
        "version": 4,
        "description": "self-test",
        "budget": {"max_total": 5, "per_locale": {"ja-JP": 2}},
        "decay": {"require_review_by": True, "warn_before_days": 7, "fail_on_expired": True},
        "waivers": []
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

    out = proc.stdout
    assert proc.returncode == 0, f"Expected pass exit code 0, got {proc.returncode}\nOutput:\n{out}"

    lines = out.splitlines()
    summary_lines = [ln for ln in lines if ln.startswith('CI SUMMARY:')]
    assert len(summary_lines) == 1, f"Expected exactly 1 CI SUMMARY line, got {len(summary_lines)}\nOutput:\n{out}"

    # Ensure 'CI SUMMARY:' does not appear in any other line.
    other_mentions = [ln for ln in lines if (not ln.startswith('CI SUMMARY:') and 'CI SUMMARY:' in ln)]
    assert not other_mentions, f"Found 'CI SUMMARY:' in non-summary lines: {other_mentions}"

    summary = summary_lines[0]

    # Ensure the printed summary line itself does not contain escaped newlines.
    assert '\\n' not in summary and '\\r' not in summary, f"Summary line contains escaped newline tokens: {summary}"

    # Ensure the summary line is not empty after prefix.
    assert len(summary) > len('CI SUMMARY:'), f"Summary line appears truncated: {summary}"
