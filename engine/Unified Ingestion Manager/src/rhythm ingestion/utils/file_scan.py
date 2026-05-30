from __future__ import annotations
"""
[file_scan.py](https://onedrive.live.com/?id=ecabc053-eeaa-4d86-83bd-bc1153c2db05&cid=d5d62a1ef303ba22&web=1&EntityRepresentationId=1bbe0402-43eb-4b60-a063-2aae966a2f86)
Cross-game file scanner for the Unified Ingestion Manager (Phase 3).

## Sealed responsibilities (Phase 3 utils)
- Recursively scan a directory tree.
- Collect candidate files for ingestion.
- Remain completely adapter-agnostic.
- Provide predictable, deterministic ordering.

This module intentionally does NOT:
- Parse charts
- Infer game IDs
- Validate files
- Apply gameplay logic

Those responsibilities belong to adapters, validators, and the tips pipeline. [1](https://onedrive.live.com/?id=ecabc053-eeaa-4d86-83bd-bc1153c2db05&cid=d5d62a1ef303ba22&web=1)

## Additive capability (control-plane only)
Optional scan-state tracking to support:
- scheduling: "must scan if unscanned candidates exist"
- manual inspection / diff / commit operations

Important:
- "scanned" here means "discovered by the scanner as a candidate file".
- It does NOT claim tips generation succeeded. [1](https://onedrive.live.com/?id=ecabc053-eeaa-4d86-83bd-bc1153c2db05&cid=d5d62a1ef303ba22&web=1)

## Output conventions (per user requirements)
Default chart root:
  C:\\Users\\edfwh\\OneDrive\\Desktop\\Rhythm Game Assistant\\Chart File

Default meta output dir:
  C:\\Users\\edfwh\\OneDrive\\Desktop\\Rhythm Game Assistant\\Tips Output Meta

Scan-state files:
  file_scan_state_YYYY-MM-DD_?.json

Run identity for pairing with QA Summary:
  run_id = "YYYY-MM-DD_?" (date + daily sequence)

Integrity:
- Use [paired_integrity.py](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!sa1a5a7b4e6084b02b05d9f5198778d2d&EntityRepresentationId=065e3551-9a84-4d14-875a-2f6f1b1dc0e7) helpers:
  content hash = SHA-256(canonical JSON payload with top-level 'integrity' removed)
  to avoid circular dependency. [2](https://onedrive.live.com/?id=a1a5a7b4-e608-4b02-b05d-9f5198778d2d&cid=d5d62a1ef303ba22&web=1)

This file is control-plane / observability only and does not modify any completed
semantic phases.
"""

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone, date
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

# IMPORTANT: align integrity implementation with paired_integrity
from .paired_integrity import compute_content_hash_sha256, stamp_integrity  # type: ignore


# -------------------------------
# Defaults
# -------------------------------

DEFAULT_CHART_ROOT = Path(r"C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Chart File")
DEFAULT_STATE_BASE_DIR = Path(r"C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Tips Output Meta")

DEFAULT_ALLOWED_EXTENSIONS = set()  # empty by default

# Scanner-level hygiene (still adapter-agnostic)
SYSTEM_BASENAMES = {
    "thumbs.db",
    "desktop.ini",
    ".ds_store",
}

_STATE_RE = re.compile(r"^file_scan_state_(\d{4}-\d{2}-\d{2})_(\d+)\.json$")
_TIPS_META_RE = re.compile(r"^tips_meta_(\d{4}-\d{2}-\d{2})_(\d+)\.json$")
_RUN_ID_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d+)$")


# -------------------------------
# Deterministic scanning
# -------------------------------

def _walk(root: Path, *, ignore_hidden: bool, follow_symlinks: bool) -> Iterable[Path]:
    """Internal directory walker with deterministic ordering."""
    if not root.exists():
        return
    for dirpath, dirnames, filenames in os.walk(root, followlinks=follow_symlinks):
        dp = Path(dirpath)
        dirnames.sort(key=lambda s: s.casefold())
        filenames.sort(key=lambda s: s.casefold())

        if ignore_hidden:
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]

        for fn in filenames:
            if ignore_hidden and fn.startswith("."):
                continue
            yield dp / fn


def scan_directory(
    root: Path,
    *,
    allowed_extensions: Optional[Sequence[str]] = None,
    ignore_hidden: bool = True,
    follow_symlinks: bool = False,
    drop_system_files: bool = True,
) -> List[Path]:
    """
    Recursively scan a directory for candidate chart files.

    Deterministic:
    - directory entries and candidate list are sorted by casefolded string path.
    """
    exts = set(allowed_extensions or DEFAULT_ALLOWED_EXTENSIONS)
    exts = {e.lower() for e in exts}

    candidates: List[Path] = []
    for p in _walk(root, ignore_hidden=ignore_hidden, follow_symlinks=follow_symlinks):
        if p.suffix.lower() in exts:
            if drop_system_files and p.name.casefold() in SYSTEM_BASENAMES:
                continue
            if drop_system_files and p.name.startswith("._"):
                continue
            candidates.append(p)

    candidates.sort(key=lambda x: str(x).casefold())
    return candidates


def scan_many(roots: Sequence[Path], **kwargs) -> List[Path]:
    """Scan multiple root directories and merge results deterministically."""
    all_candidates: List[Path] = []
    for r in roots:
        all_candidates.extend(scan_directory(r, **kwargs))

    # Deduplicate deterministically by string path
    uniq = sorted(
        {_normalize_key(p): p for p in all_candidates}.items(),
        key=lambda kv: kv[0].casefold()
    )
    return [p for _, p in uniq]


# -------------------------------
# Scan-state model
# -------------------------------

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def make_run_id(report_date: str, seq: int) -> str:
    return f"{report_date}_{seq}"


def parse_run_id(run_id: str) -> Optional[Tuple[str, int]]:
    m = _RUN_ID_RE.match(run_id)
    if not m:
        return None
    return m.group(1), int(m.group(2))


def _normalize_key(path: Path) -> str:
    # Absolute resolved path string for stable identity
    return str(path.resolve())


@dataclass
class FileFingerprint:
    size: int
    mtime_ns: int


@dataclass
class ScanState:
    version: int = 2
    report_date: Optional[str] = None
    report_seq: Optional[int] = None
    run_id: Optional[str] = None
    generated_at: Optional[str] = None
    entries: Dict[str, FileFingerprint] = field(default_factory=dict)
    integrity: Optional[Dict[str, Any]] = None


def fingerprint(path: Path) -> FileFingerprint:
    st = path.stat()
    return FileFingerprint(size=int(st.st_size), mtime_ns=int(st.st_mtime_ns))


# -------------------------------
# Scan-state file IO + sequencing
# -------------------------------

def parse_state_filename(path: Path) -> Optional[Tuple[str, int]]:
    m = _STATE_RE.match(path.name)
    if not m:
        return None
    return m.group(1), int(m.group(2))


def list_state_files(base_dir: Path) -> List[Path]:
    if not base_dir.exists():
        return []
    files = [p for p in base_dir.iterdir() if p.is_file() and parse_state_filename(p) is not None]
    files.sort(key=lambda p: (parse_state_filename(p)[0], parse_state_filename(p)[1], p.name))
    return files


def get_latest_state_path(base_dir: Path) -> Optional[Path]:
    files = list_state_files(base_dir)
    return files[-1] if files else None


def list_tips_meta_files(base_dir: Path) -> List[Path]:
    """List QA summary files (tips_meta_YYYY-MM-DD_?.json) if stored in the same directory."""
    if not base_dir.exists():
        return []
    files = [p for p in base_dir.iterdir() if p.is_file() and _TIPS_META_RE.match(p.name)]
    files.sort(key=lambda p: (_TIPS_META_RE.match(p.name).group(1), int(_TIPS_META_RE.match(p.name).group(2)), p.name))
    return files


def next_run_seq(base_dir: Path, report_date: str) -> int:
    """Next available seq for a date by inspecting BOTH scan_state and tips_meta files."""
    if not base_dir.exists():
        return 1
    seqs: List[int] = []
    for p in base_dir.iterdir():
        if not p.is_file():
            continue
        m1 = _STATE_RE.match(p.name)
        if m1 and m1.group(1) == report_date:
            seqs.append(int(m1.group(2)))
            continue
        m2 = _TIPS_META_RE.match(p.name)
        if m2 and m2.group(1) == report_date:
            seqs.append(int(m2.group(2)))
    return (max(seqs) + 1) if seqs else 1


def allocate_run_id(base_dir: Path, report_date: str) -> Tuple[str, int]:
    seq = next_run_seq(base_dir, report_date)
    return make_run_id(report_date, seq), seq


def state_path_for_date_seq(base_dir: Path, report_date: str, seq: int) -> Path:
    return base_dir / f"file_scan_state_{report_date}_{seq}.json"


def load_state(state_path: Path) -> ScanState:
    if not state_path.exists():
        return ScanState()
    raw = json.loads(state_path.read_text(encoding="utf-8"))

    entries_raw = raw.get("entries") or {}
    entries: Dict[str, FileFingerprint] = {}
    for k, v in entries_raw.items():
        try:
            entries[k] = FileFingerprint(size=int(v["size"]), mtime_ns=int(v["mtime_ns"]))
        except Exception:
            continue

    return ScanState(
        version=int(raw.get("version", 1)),
        report_date=raw.get("report_date"),
        report_seq=raw.get("report_seq"),
        run_id=raw.get("run_id"),
        generated_at=raw.get("generated_at"),
        entries=entries,
        integrity=raw.get("integrity"),
    )


def save_state_atomic(payload: Dict[str, Any], state_path: Path) -> None:
    """Atomic write to prevent partial/corrupted JSON."""
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_path.with_suffix(state_path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, state_path)


def diff_unscanned(candidates: Sequence[Path], state: ScanState) -> List[Path]:
    """Return candidates that are new/changed vs scan-state."""
    unscanned: List[Path] = []
    for p in candidates:
        key = _normalize_key(p)
        try:
            fp = fingerprint(p)
        except FileNotFoundError:
            continue
        old = state.entries.get(key)
        if old is None or old.size != fp.size or old.mtime_ns != fp.mtime_ns:
            unscanned.append(p)
    unscanned.sort(key=lambda x: str(x).casefold())
    return unscanned


def should_run_scan(
    roots: Sequence[Path],
    *,
    base_dir: Path,
    allowed_extensions: Optional[Sequence[str]] = None,
    ignore_hidden: bool = True,
    follow_symlinks: bool = False,
    drop_system_files: bool = True,
) -> Tuple[bool, List[Path]]:
    """Scheduling helper implementing must-scan rule."""
    candidates = scan_many(
        roots,
        allowed_extensions=allowed_extensions,
        ignore_hidden=ignore_hidden,
        follow_symlinks=follow_symlinks,
        drop_system_files=drop_system_files,
    )
    latest_path = get_latest_state_path(base_dir)
    st = load_state(latest_path) if latest_path else ScanState()
    unscanned = diff_unscanned(candidates, st)
    return (len(unscanned) > 0), unscanned


def commit_scan_state_for_run(
    candidates: Sequence[Path],
    *,
    base_dir: Path,
    run_id: str,
    pair_tips_meta_path: Optional[Path] = None,
) -> Tuple[Path, Dict[str, Any]]:
    """
    Commit scan-state for a run_id to file_scan_state_YYYY-MM-DD_?.json.

    Adds integrity block using [paired_integrity.py](https://onedrive.live.com?cid=D5D62A1EF303BA22&id=D5D62A1EF303BA22!sa1a5a7b4e6084b02b05d9f5198778d2d&EntityRepresentationId=065e3551-9a84-4d14-875a-2f6f1b1dc0e7):
    - content_hash_sha256
    - prev_content_hash_sha256 (chain within scan_state stream, optional)
    - pair_content_hash_sha256 (tips_meta content hash, optional)
    """
    parsed = parse_run_id(run_id)
    if not parsed:
        raise ValueError(f"Invalid run_id: {run_id}")
    report_date, seq = parsed

    # prev hash: chain within scan_state stream for the same date (optional)
    prev_hash = None
    same_day_states = [p for p in list_state_files(base_dir) if parse_state_filename(p)[0] == report_date]
    if same_day_states:
        prev = json.loads(same_day_states[-1].read_text(encoding="utf-8"))
        integ = prev.get("integrity") or {}
        if isinstance(integ, dict):
            prev_hash = integ.get("content_hash_sha256")

    # pair hash: tips_meta content hash (optional)
    pair_hash = None
    if pair_tips_meta_path and pair_tips_meta_path.exists():
        try:
            tips_meta = json.loads(pair_tips_meta_path.read_text(encoding="utf-8"))
            pair_hash = compute_content_hash_sha256(tips_meta)
        except Exception:
            pair_hash = None

    # Build entries deterministically
    entries: Dict[str, Dict[str, int]] = {}
    for p in sorted(candidates, key=lambda x: str(x).casefold()):
        try:
            fp = fingerprint(p)
        except FileNotFoundError:
            continue
        entries[_normalize_key(p)] = {"size": fp.size, "mtime_ns": fp.mtime_ns}

    payload: Dict[str, Any] = {
        "version": 2,
        "report_date": report_date,
        "report_seq": seq,
        "run_id": run_id,
        "generated_at": utc_now_iso(),
        "entries": entries,
    }

    # Stamp integrity using shared helper
    stamp_integrity(
        payload,
        prev_content_hash_sha256=prev_hash,
        pair_content_hash_sha256=pair_hash,
        schema_version=1,
    )

    out_path = state_path_for_date_seq(base_dir, report_date, seq)
    save_state_atomic(payload, out_path)
    return out_path, payload


# -------------------------------
# CLI (manual handle)
# -------------------------------

def _ext_counts(paths: List[Path]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for p in paths:
        ext = p.suffix.lower()
        counts[ext] = counts.get(ext, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def _print_sample(label: str, paths: List[Path], limit: int) -> None:
    print(f"{label}: {len(paths)}")
    for p in paths[:limit]:
        print(f"  - {p}")
    if len(paths) > limit:
        print(f"  ... ({len(paths) - limit} more)")


def cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser("RGA Phase 3 file scanner (manual handle)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--root", default=str(DEFAULT_CHART_ROOT), help=f"Root directory to scan (default: {DEFAULT_CHART_ROOT})")
        p.add_argument("--base-dir", default=str(DEFAULT_STATE_BASE_DIR), help=f"Output meta directory (default: {DEFAULT_STATE_BASE_DIR})")
        p.add_argument("--extensions", default=",".join(sorted(DEFAULT_ALLOWED_EXTENSIONS)), help="Comma-separated allowed extensions")
        p.add_argument("--include-hidden", action="store_true", help="Include hidden files and directories")
        p.add_argument("--follow-symlinks", action="store_true", help="Follow symlinks when walking directories")
        p.add_argument("--keep-system-files", action="store_true", help="Do not filter system files (Thumbs.db, .DS_Store, etc.)")

    # inspect
    p_inspect = sub.add_parser("inspect", help="Scan and print summary (no state write)")
    add_common(p_inspect)
    p_inspect.add_argument("--limit", type=int, default=20, help="Max sample paths to print")

    # diff
    p_diff = sub.add_parser("diff", help="Scan and show unscanned vs latest state (no state write)")
    add_common(p_diff)
    p_diff.add_argument("--limit", type=int, default=50, help="Max unscanned paths to print")

    # commit
    p_commit = sub.add_parser("commit", help="Scan and write a new scan_state JSON")
    add_common(p_commit)
    p_commit.add_argument("--report-date", default=None, help="Report date YYYY-MM-DD (default: today local)")
    p_commit.add_argument("--seq", type=int, default=None, help="Optional explicit seq for the day")
    p_commit.add_argument("--run-id", default=None, help='Optional explicit run_id "YYYY-MM-DD_?" (overrides --report-date/--seq)')
    p_commit.add_argument("--pair-tips-meta", default=None, help="Optional path to paired tips_meta_YYYY-MM-DD_?.json to embed pair hash")

    # should-run
    p_should = sub.add_parser("should-run", help="Exit 0 if unscanned exists, else 2")
    add_common(p_should)

    args = parser.parse_args(argv)

    root = Path(args.root)
    base_dir = Path(args.base_dir)
    allowed_extensions = [e.strip() for e in str(args.extensions).split(",") if e.strip()]
    ignore_hidden = not bool(args.include_hidden)
    follow_symlinks = bool(args.follow_symlinks)
    drop_system_files = not bool(args.keep_system_files)

    if args.cmd == "inspect":
        candidates = scan_directory(
            root,
            allowed_extensions=allowed_extensions,
            ignore_hidden=ignore_hidden,
            follow_symlinks=follow_symlinks,
            drop_system_files=drop_system_files,
        )
        print(f"Root: {root}")
        print(f"Candidates: {len(candidates)}")
        counts = _ext_counts(candidates)
        print("Extension counts:")
        for k, v in counts.items():
            print(f"  {k}: {v}")
        _print_sample("Sample candidates", candidates, args.limit)
        return 0

    if args.cmd == "diff":
        candidates = scan_directory(
            root,
            allowed_extensions=allowed_extensions,
            ignore_hidden=ignore_hidden,
            follow_symlinks=follow_symlinks,
            drop_system_files=drop_system_files,
        )
        latest = get_latest_state_path(base_dir)
        st = load_state(latest) if latest else ScanState()
        unscanned = diff_unscanned(candidates, st)
        print(f"Root: {root}")
        print(f"Candidates: {len(candidates)}")
        print(f"Latest state: {latest if latest else '(none)'}")
        print(f"Unscanned: {len(unscanned)}")
        _print_sample("Sample unscanned", unscanned, args.limit)
        return 0

    if args.cmd == "should-run":
        should, unscanned = should_run_scan(
            [root],
            base_dir=base_dir,
            allowed_extensions=allowed_extensions,
            ignore_hidden=ignore_hidden,
            follow_symlinks=follow_symlinks,
            drop_system_files=drop_system_files,
        )
        print(f"should_run={should} unscanned={len(unscanned)}")
        return 0 if should else 2

    if args.cmd == "commit":
        candidates = scan_directory(
            root,
            allowed_extensions=allowed_extensions,
            ignore_hidden=ignore_hidden,
            follow_symlinks=follow_symlinks,
            drop_system_files=drop_system_files,
        )

        # Determine run_id
        if args.run_id:
            run_id = str(args.run_id)
        else:
            report_date = args.report_date or date.today().isoformat()
            if args.seq is not None:
                run_id = make_run_id(report_date, int(args.seq))
            else:
                run_id, _ = allocate_run_id(base_dir, report_date)

        pair_path = Path(args.pair_tips_meta) if args.pair_tips_meta else None
        out_path, payload = commit_scan_state_for_run(
            candidates,
            base_dir=base_dir,
            run_id=run_id,
            pair_tips_meta_path=pair_path,
        )

        print(f"Wrote scan_state: {out_path}")
        print(f"run_id: {payload.get('run_id')}")
        print(f"entries: {len(payload.get('entries') or {})}")
        integ = payload.get("integrity") or {}
        print(f"content_hash_sha256: {integ.get('content_hash_sha256')}")
        if integ.get("pair_content_hash_sha256"):
            print(f"pair_content_hash_sha256: {integ.get('pair_content_hash_sha256')}")
        return 0

    parser.print_help()
    return 1
    
def scan_directory_using_games_json(
    root: Path,
    *,
    config_path: Optional[Path] = None,
    ignore_hidden: bool = True,
    follow_symlinks: bool = False,
    drop_system_files: bool = True,
) -> List[Path]:
    """
    Convenience wrapper (control-plane only):
    - Loads games.json via game_router
    - Scans using allowed_extensions union across enabled games
    """
    from .game_router import build_routing, DEFAULT_CONFIG_PATH  # local import to avoid cycles

    routing = build_routing(config_path or DEFAULT_CONFIG_PATH)

    return scan_directory(
        root,
        allowed_extensions=routing.allowed_extensions,
        ignore_hidden=ignore_hidden,
        follow_symlinks=follow_symlinks,
        drop_system_files=drop_system_files,
    )


if __name__ == "__main__":
    raise SystemExit(cli_main())


__all__ = [
    # scanning
    "scan_directory",
    "scan_many",
    "DEFAULT_ALLOWED_EXTENSIONS",
    "DEFAULT_CHART_ROOT",
    "DEFAULT_STATE_BASE_DIR",
    # state + run_id
    "ScanState",
    "FileFingerprint",
    "make_run_id",
    "parse_run_id",
    "allocate_run_id",
    "next_run_seq",
    "get_latest_state_path",
    "list_state_files",
    "list_tips_meta_files",
    "diff_unscanned",
    "should_run_scan",
    "commit_scan_state_for_run",
]