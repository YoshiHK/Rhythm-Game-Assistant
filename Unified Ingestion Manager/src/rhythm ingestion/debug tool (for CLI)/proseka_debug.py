#!/usr/bin/env python3
"""
CLI Debug Tool for Proseka Charts

Usage:
    python -m proseka_debug [--dump-events] [--dump-sections] [--dump-meta] [--dump-full] path/to/chart_file.html

Options:
    --dump-events     Print note_events in full canonical form
    --dump-sections   Print sections (SectionMetrics) in full canonical form, if present
    --dump-meta       Print chart_meta + difficulty_details + difficulty_consistency
    --dump-full       Print everything above plus full payload, row, and diagnostics
"""

import json
import sys
from pathlib import Path

# Import your adapter + validator
from rhythm_ingestion.adapters.adapter_proseka import (
    to_canonical_payload,
    ProsekaAdapter,
)
from rhythm_ingestion.validators.validator_proseka import ProsekaValidator


def pretty(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False)


def build_canonical_row_for_debug(path: Path):
    """
    Mirror what ingestion does:
        raw = adapter.load(path)
        canonical_row = adapter.to_canonical_row(raw)
    """
    adapter = ProsekaAdapter()
    raw = adapter.load(path)
    return adapter.to_canonical_row(raw)

# Argument parsing for all flags

def parse_args(argv):
    dump_events = False
    dump_sections = False
    dump_meta = False
    dump_full = False
    paths = []
   
    for arg in argv:
            if arg == "--dump-events":
                dump_events = True
            elif arg == "--dump-sections":
                dump_sections = True
            elif arg == "--dump-meta":
                dump_meta = True
            elif arg == "--dump-full":
                dump_full = True
            else:
                paths.append(arg)

        if len(paths) != 1:
            print(
                "Usage:\n"
                "  python -m proseka_debug [--dump-events] [--dump-sections] "
                "[--dump-meta] [--dump-full] path/to/chart.html"
            )
            sys.exit(1)

        return dump_events, dump_sections, dump_meta, dump_full, paths[0]



# Main logic of debug tool

def run_debug_tool(
    chart_path: str,
    dump_events: bool,
    dump_sections: bool,
    dump_meta: bool,
    dump_full: bool,
):
    path = Path(chart_path)
    if not path.exists():
        print(f"Error: file not found: {path}")
        return 1

    # --dump-full implies all more granular dumps
    if dump_full:
        dump_events = True
        dump_sections = True
        dump_meta = True

    print("\n=== STEP 1 — BUILD CANONICAL PAYLOAD ===")
    payload = to_canonical_payload(str(path))
    print("canonical_payload keys:", list(payload.keys()))

    # Optional dump: note_events
    if dump_events:
        print("\n=== DUMP: note_events ===")
        note_events = payload.get("note_events", [])
        print(pretty(note_events))

    # Optional dump: sections (if any)
    if dump_sections:
        print("\n=== DUMP: sections ===")
        sections = payload.get("sections", [])
        if not sections:
            print("(no sections found in payload)")
        else:
            print(pretty(sections))

    # Optional dump: metadata blocks
    if dump_meta:
        print(
            "\n=== DUMP: metadata (chart_meta, difficulty_details, difficulty_consistency) ==="
        )
        chart_meta = payload.get("chart_meta", {})
        adapter_meta = payload.get("adapter_metadata", {})
        difficulty_details = adapter_meta.get("difficulty_details", {})
        difficulty_consistency = adapter_meta.get("difficulty_consistency", {})

        to_show = {
            "chart_meta": chart_meta,
            "difficulty_details": difficulty_details,
            "difficulty_consistency": difficulty_consistency,
        }
        print(pretty(to_show))

    print("\n=== STEP 2 — BUILD CANONICAL ROW (INGESTION VIEW) ===")
    canonical_row = build_canonical_row_for_debug(path)
    print(pretty(canonical_row))

    print("\n=== STEP 3 — VALIDATE (ProsekaValidator) ===")
    validator = ProsekaValidator()

    try:
        validator.validate(
            raw_chart=None,  # not used yet
            canonical_payload=payload,
            canonical_row=canonical_row,
        )
        print("✔ Validation PASSED.")
        validation_status = "passed"
    except Exception as exc:
        print("✘ Validation FAILED:")
        print(str(exc))
        validation_status = f"failed: {exc}"

    print("\n=== STEP 4 — METADATA PARITY SUMMARY ===")
    diag = payload.get("diagnostics", {})
    metadata_parity = diag.get("metadata_parity")
    if metadata_parity is None:
        print("No metadata_parity found in payload.diagnostics!")
    else:
        print(pretty(metadata_parity))

    # Optional: full dump of payload + diagnostics
    if dump_full:
        print("\n=== DUMP-FULL: canonical_payload ===")
        print(pretty(payload))

        print("\n=== DUMP-FULL: diagnostics ===")
        print(pretty(diag))

        full_summary = {
            "chart_path": str(path),
            "validation_status": validation_status,
            "payload_keys": list(payload.keys()),
        }
        print("\n=== DUMP-FULL: summary ===")
        print(pretty(full_summary))

    print("\n=== DONE ===\n")
    return 0

# Entry Point

if __name__ == "__main__":
    dump_events, dump_sections, dump_meta, dump_full, chart_path = parse_args(
        sys.argv[1:]
    )
    sys.exit(
        run_debug_tool(chart_path, dump_events, dump_sections, dump_meta, dump_full)
    )

