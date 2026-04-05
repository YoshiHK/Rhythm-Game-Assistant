from __future__ import annotations

"""
file_scan.py
Cross-game file scanner for the Unified Ingestion Manager (Phase 3).

Responsibilities
----------------
- Recursively scan a directory tree.
- Collect candidate files for ingestion.
- Remain completely adapter-agnostic.
- Provide predictable, deterministic ordering.

This module intentionally does NOT:
- Parse charts
- Infer game IDs
- Validate files
- Apply gameplay logic

Those responsibilities belong to adapters, validators, and the tips pipeline.
"""

from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set


# Default extensions that commonly appear in rhythm game exports.
# This is a *broad filter*, not a guarantee of compatibility.
DEFAULT_ALLOWED_EXTENSIONS: Set[str] = {
    ".html",
    ".htm",
    ".svg",
    ".json",
    ".txt",
}


def scan_directory(
    root: Path,
    *,
    allowed_extensions: Optional[Sequence[str]] = None,
    ignore_hidden: bool = True,
    follow_symlinks: bool = False,
) -> List[Path]:
    """
    Recursively scan a directory for candidate chart files.

    Parameters
    ----------
    root:
        Root directory to scan.

    allowed_extensions:
        Optional whitelist of file extensions (case-insensitive).
        If None, DEFAULT_ALLOWED_EXTENSIONS is used.

    ignore_hidden:
        If True (default), skip hidden files and directories
        (names starting with '.').

    follow_symlinks:
        Whether to follow symlinks when recursing.

    Returns
    -------
    List[Path]
        Sorted list of candidate file paths.

    Notes
    -----
    - This function does NOT attempt to determine which game a file belongs to.
    - Adapters are responsible for deciding whether they accept a file.
    - Sorting ensures deterministic ingestion / QA behavior.
    """
    root = Path(root)

    if not root.exists():
        raise FileNotFoundError(f"Scan root does not exist: {root}")

    if not root.is_dir():
        raise NotADirectoryError(f"Scan root is not a directory: {root}")

    exts: Set[str]
    if allowed_extensions is None:
        exts = {e.lower() for e in DEFAULT_ALLOWED_EXTENSIONS}
    else:
        exts = {e.lower() for e in allowed_extensions}

    results: List[Path] = []

    for path in _walk(root, ignore_hidden=ignore_hidden, follow_symlinks=follow_symlinks):
        if not path.is_file():
            continue
        if path.suffix.lower() not in exts:
            continue
        results.append(path)

    # Deterministic ordering
    results.sort(key=lambda p: str(p).lower())
    return results


def _walk(
    root: Path,
    *,
    ignore_hidden: bool,
    follow_symlinks: bool,
) -> Iterable[Path]:
    """
    Internal directory walker with hidden-file handling.

    Separated for clarity and testability.
    """
    for entry in root.iterdir():
        name = entry.name

        if ignore_hidden and name.startswith("."):
            continue

        try:
            if entry.is_dir():
                if follow_symlinks or not entry.is_symlink():
                    yield from _walk(
                        entry,
                        ignore_hidden=ignore_hidden,
                        follow_symlinks=follow_symlinks,
                    )
            else:
                yield entry
        except PermissionError:
            # Skip unreadable directories/files silently.
            continue


def scan_many(
    roots: Sequence[Path],
    **kwargs,
) -> List[Path]:
    """
    Scan multiple root directories and merge results.

    Parameters
    ----------
    roots:
        Sequence of root directories.

    **kwargs:
        Forwarded to scan_directory().

    Returns
    -------
    List[Path]
        Deduplicated, sorted list of candidate files.
    """
    seen: Set[Path] = set()
    out: List[Path] = []

    for root in roots:
        for p in scan_directory(root, **kwargs):
            if p not in seen:
                seen.add(p)
                out.append(p)

    out.sort(key=lambda p: str(p).lower())
    return out


__all__ = [
    "scan_directory",
    "scan_many",
    "DEFAULT_ALLOWED_EXTENSIONS",
]
``
