#!/usr/bin/env python3
from __future__ import annotations

"""
arcaea_batch_validate.py (Phase 3 tool)

Batch validator for Arcaea AFF charts.

Runs arcaea_cli via module invocation:
    python -m arcaea_cli <chart.aff> --validate-only --strict --sections <N>

Outputs:
- per-file status
- final summary
- exit code 1 if any file fails strict checks
"""

import os
import sys
import subprocess
import argparse
import json
from typing import List, Tuple, Optional, Dict, Any


# ----------------------------------------------------------------------
# SectionMetrics QA (Phase 3 safety check)
# ----------------------------------------------------------------------

def qa_check_sections_for_pipeline(payload: Dict[str, Any]) -> None:
    """
    Verify adapter-emitted sections are compatible with
    pipeline.section_metrics aggregation.

    Raises AssertionError on failure.
    """
    sections = payload.get("sections")
    assert isinstance(sections, list), "payload['sections'] must be a list"

    # No sections is allowed (e.g. unsupported or empty charts)
    if not sections:
        return

    for i, section in enumerate(sections):
        assert isinstance(section, dict), f"section[{i}] is not a dict"

        assert "nps" in section and isinstance(section["nps"], (int, float)), (
            f"section[{i}] missing numeric 'nps'"
        )

        assert "npb" in section and isinstance(section["npb"], (int, float)), (
            f"section[{i}] missing numeric 'npb'"
        )


def extract_payload_from_cli_output(stdout: str) -> Optional[Dict[str, Any]]:
    """
    Best-effort extraction of canonical payload from CLI stdout.

    Assumes the CLI prints a JSON object when validation succeeds.
    Returns dict or None.
    """
    if not stdout:
        return None

    text = stdout.strip()
    if not text:
        return None

    try:
        return json.loads(text)
    except Exception:
        return None


# ----------------------------------------------------------------------
# File discovery
# ----------------------------------------------------------------------

def find_aff_files(root_dir: str) -> List[str]:
    """
    Recursively find all .aff files under root_dir.
    """
    aff_files: List[str] = []

    for base, _, files in os.walk(root_dir):
        for fname in files:
            if fname.lower().endswith(".aff"):
                aff_files.append(os.path.join(base, fname))

    return aff_files


# ----------------------------------------------------------------------
# CLI invocation
# ----------------------------------------------------------------------

def run_cli(
    path: str,
    *,
    sections: int,
    strict: bool,
    show_debug: bool = False,
) -> Tuple[bool, str, str]:
    """
    Run arcaea_cli in module mode with validation on a single file.

    Returns:
        (success, stdout, stderr)
    """
    cmd: List[str] = [
        sys.executable,
        "-m",
        "arcaea_cli",
        path,
        "--validate-only",
    ]

    if sections and sections > 0:
        cmd.extend(["--sections", str(int(sections))])

    if strict:
        cmd.append("--strict")

    if show_debug:
        cmd.append("--show-difficulty-debug")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    out, err = proc.communicate()
    success = (proc.returncode == 0)
    return success, out, err


# ----------------------------------------------------------------------
# Main entry
# ----------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch validate Arcaea charts using arcaea_cli (module mode)."
    )

    parser.add_argument(
        "folder",
        help="Folder containing .aff charts (recursively searched)",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show difficulty-debug output for each file",
    )

    parser.add_argument(
        "--sections",
        type=int,
        default=8,
        help="Number of sections passed to arcaea_cli (default: 8)",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict mode (non-zero exit on inconsistency)",
    )

    args = parser.parse_args()

    root = args.folder
    if not os.path.isdir(root):
        print(f"ERROR: '{root}' is not a valid directory.")
        raise SystemExit(1)

    print("=== Arcaea Batch Validator ===")
    print(f"Scanning folder: {root}")
    print()

    aff_files = find_aff_files(root)
    if not aff_files:
        print("No .aff files found.")
        raise SystemExit(0)

    total = len(aff_files)
    passed: List[str] = []
    failed: List[str] = []

    for path in sorted(aff_files):
        print(f"--- Validating: {path}")

        success, out, err = run_cli(
            path,
            sections=args.sections,
            strict=args.strict,
            show_debug=args.debug,
        )

        # Forward CLI output
        if out.strip():
            print(out)
        if err.strip():
            print(err)

        if success:
            # Optional SectionMetrics QA (strict-only)
            if args.strict:
                payload = extract_payload_from_cli_output(out)
                if payload is not None:
                    try:
                        qa_check_sections_for_pipeline(payload)
                    except AssertionError as exc:
                        print(f"[SECTION QA FAIL] {path}: {exc}")
                        failed.append(path)
                        print()
                        continue

            print(f"[OK] {path}")
            passed.append(path)
        else:
            print(f"[FAIL] {path}")
            failed.append(path)

        print()

    # Summary
    print("=== Batch Summary ===")
    print(f"Total charts: {total}")
    print(f"Passed: {len(passed)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("\nSome charts failed strict validation.")
        print("List of failed charts:")
        for f in failed:
            print(" -", f)
        raise SystemExit(1)

    print("\nAll charts passed strict validation.")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
