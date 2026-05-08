"""
section_validator.py

Optional QA / sanity validation for SectionMetrics (Stage 2–4.1).

This module provides lightweight structural checks for SectionMetrics objects
produced by section_builder. It is intended for:
- internal QA
- regression testing
- debug tooling

This module MUST NOT:
- be invoked automatically
- mutate SectionMetrics
- raise exceptions during import
- replace UMI validators

All validation functions are explicit and opt-in.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

from .section_metrics_dataclasses import SectionMetrics
from .section_utils import clamp


# -------------------------------------------------
# Core validation helpers
# -------------------------------------------------

def validate_section(section: SectionMetrics) -> List[str]:
    """
    Validate a single SectionMetrics object.

    Returns
    -------
    List[str]
        A list of human-readable warning/error messages.
        Empty list means the section passed all checks.
    """
    issues: List[str] = []

    # Index & bounds
    if section.section_index < 0:
        issues.append("section_index must be >= 0")

    if section.end_time_beats < section.start_time_beats:
        issues.append("end_time_beats < start_time_beats")

    # Counts
    if section.note_count < 0:
        issues.append("note_count must be >= 0")

    if section.tap_count < 0:
        issues.append("tap_count must be >= 0")

    if section.hold_count < 0:
        issues.append("hold_count must be >= 0")

    if section.flick_count < 0:
        issues.append("flick_count must be >= 0")

    # Sub-count consistency
    subtype_sum = section.tap_count + section.hold_count + section.flick_count
    if subtype_sum > section.note_count:
        issues.append(
            "tap+hold+flick exceeds note_count "
            f"({subtype_sum} > {section.note_count})"
        )

    # Duration / density
    if section.duration_beats < 0:
        issues.append("duration_beats must be >= 0")

    if section.duration_beats == 0 and section.note_count > 0:
        issues.append("non-zero note_count with zero duration_beats")

    if section.note_density < 0:
        issues.append("note_density must be >= 0")

    # Coverage
    if not (0.0 <= section.section_coverage <= 1.0):
        issues.append("section_coverage must be in [0,1]")

    # Lane usage
    if section.lane_usage:
        for lane_id, count in section.lane_usage.counts.items():
            if count < 0:
                issues.append(f"lane_usage[{lane_id}] must be >= 0")

    return issues


# -------------------------------------------------
# Multi-section validation
# -------------------------------------------------

def validate_sections(
    sections: Sequence[SectionMetrics],
    *,
    expect_monotonic_indices: bool = True,
    expect_contiguous_windows: bool = True,
    coverage_tolerance: float = 1e-6,
) -> List[str]:
    """
    Validate a list of SectionMetrics.

    Parameters
    ----------
    expect_monotonic_indices:
        If True, section_index must be strictly increasing starting from 0.
    expect_contiguous_windows:
        If True, end_time_beats[i] == start_time_beats[i+1] (within tolerance).
    coverage_tolerance:
        Allowed numeric drift for coverage sum checks.

    Returns
    -------
    List[str]
        Aggregated issues across all sections.
    """
    issues: List[str] = []

    if not sections:
        return issues

    # Per-section checks
    for i, sec in enumerate(sections):
        sec_issues = validate_section(sec)
        for msg in sec_issues:
            issues.append(f"section[{i}]: {msg}")

    # Index monotonicity
    if expect_monotonic_indices:
        for i, sec in enumerate(sections):
            if sec.section_index != i:
                issues.append(
                    f"section_index mismatch at position {i}: "
                    f"expected {i}, got {sec.section_index}"
                )

    # Window contiguity
    if expect_contiguous_windows:
        for i in range(len(sections) - 1):
            a = sections[i]
            b = sections[i + 1]
            if abs(a.end_time_beats - b.start_time_beats) > coverage_tolerance:
                issues.append(
                    "non-contiguous windows between sections "
                    f"{i} and {i+1}: "
                    f"{a.end_time_beats} != {b.start_time_beats}"
                )

    # Coverage sanity (sum should be <= 1.0 with tolerance)
    total_coverage = sum(sec.section_coverage for sec in sections)
    if total_coverage > 1.0 + coverage_tolerance:
        issues.append(
            f"total section_coverage exceeds 1.0: {total_coverage}"
        )

    return issues


# -------------------------------------------------
# Assertion helpers (for tests / CI)
# -------------------------------------------------

def assert_sections_valid(
    sections: Sequence[SectionMetrics],
    *,
    context: Optional[str] = None,
) -> None:
    """
    Assert that sections are valid.

    Raises
    ------
    ValueError
        If any validation issue is found.
    """
    issues = validate_sections(sections)
    if issues:
        prefix = f"[{context}] " if context else ""
        joined = "\n".join(prefix + msg for msg in issues)
        raise ValueError(f"SectionMetrics validation failed:\n{joined}")


__all__ = [
    "validate_section",
    "validate_sections",
    "assert_sections_valid",
]
