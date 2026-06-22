from __future__ import annotations

"""
file_scan.py

Cross-game file scanner for the Unified Ingestion Manager (Phase 3).

--------------------------------------------------
✅ Sealed responsibilities (Phase 3 control-plane)
--------------------------------------------------
- Recursively scan directory trees
- Collect candidate files for ingestion
- Remain completely adapter-agnostic
- Provide deterministic, stable ordering of results

This module is intentionally LIMITED in scope.

It does NOT:
- parse chart content
- infer game identities
- validate or verify assets
- perform conversion or persistence (beyond scan-state / inventory utilities)
- apply gameplay or recommendation logic

Those responsibilities belong to:
- classifiers / validators (validation layer)
- converters (conversion layer)
- orchestrators (pipeline control)
- verification tools (system-level checks)

--------------------------------------------------
✅ Additive capabilities (control-plane only)
--------------------------------------------------
This module supports scan-state tracking to enable:

- scheduling:
  → detect whether new/unseen files exist

- observability:
  → inspect / diff / commit scan snapshots

Important:
- "scanned" means "discovered as a candidate file"
- it does NOT imply ingestion success or tip generation

--------------------------------------------------
✅ Output conventions
--------------------------------------------------

Default chart root:
  C:\\Users\\edfwh\\OneDrive\\Desktop\\Rhythm Game Assistant\\Chart File

Default meta output dir:
  C:\\Users\\edfwh\\OneDrive\\Desktop\\Rhythm Game Assistant\\Tips Output Meta

Scan-state files:
  file_scan_state_YYYY-MM-DD_?.json

Run identity:
  run_id = "YYYY-MM-DD_?" (date + sequence)

--------------------------------------------------
✅ Integrity model
--------------------------------------------------

Uses paired_integrity helpers:

- content_hash_sha256:
    SHA-256 over canonical JSON payload (excluding "integrity")

- prev_content_hash_sha256:
    previous scan-state hash (same day chain)

- pair_content_hash_sha256:
    optional linkage with tips_meta

This avoids circular dependencies and preserves deterministic hashing.

--------------------------------------------------
✅ Architectural note
--------------------------------------------------

file_scan.py is strictly a control-plane module.

It MUST remain:
- lightweight
- deterministic
- side-effect minimal

It may WIRE into ingestion / verification layers
(via CLI or higher-level orchestration),

but MUST NOT directly implement them.
"""

# --------------------------------------------------
# Standard libraries
# --------------------------------------------------

import argparse
import json
import os
import re
import hashlib
import sqlite3

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

# --------------------------------------------------
# Integrity helpers
# --------------------------------------------------

# Support both:
# - package execution: python -m rhythm_ingestion.utils.file_scan
# - direct script execution fallback
try:
    from .paired_integrity import compute_content_hash_sha256, stamp_integrity  # type: ignore
except ImportError:
    from paired_integrity import compute_content_hash_sha256, stamp_integrity  # type: ignore

# --------------------------------------------------
# Identity normalization (control-plane safe)
# --------------------------------------------------

try:
    from .identity_normalizer import normalize_folder_identity  # type: ignore
except ImportError:
    try:
        from rhythm_ingestion.writers.normalizers import normalize_folder_identity  # type: ignore
    except ImportError:
        try:
            from writers.normalizers import normalize_folder_identity  # type: ignore
        except ImportError:
            from identity_normalizer import normalize_folder_identity  # type: ignore
            
# --------------------------------------------------
# IMPORTANT ARCHITECTURE RULE
# --------------------------------------------------

# ⚠️ DO NOT import orchestrators / validators / converters at module level
#
# Reasons:
# - keep file_scan lightweight
# - avoid heavy dependency graph
# - prevent unintended side-effects in simple commands (inspect / diff)
# - preserve clean layer separation
#
# ✅ Any ingestion / verification MUST use lazy imports inside CLI commit flow

# --------------------------------------------------
# Defaults
# --------------------------------------------------

DEFAULT_CHART_ROOT = Path(
    r"C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Chart File"
)

DEFAULT_STATE_BASE_DIR = Path(
    r"C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Tips Output Meta"
)

DEFAULT_SCAN_DB_FILENAME = "file_scan_inventory.db"

# empty = "scan everything"
DEFAULT_ALLOWED_EXTENSIONS: Set[str] = set()

# --------------------------------------------------
# Scanner hygiene (still adapter-agnostic)
# --------------------------------------------------

SYSTEM_BASENAMES = {
    "thumbs.db",
    "desktop.ini",
    ".ds_store",
}

# --------------------------------------------------
# Naming patterns
# --------------------------------------------------

_STATE_RE = re.compile(r"^file_scan_state_(\d{4}-\d{2}-\d{2})_(\d+)\.json$")
_TIPS_META_RE = re.compile(r"^tips_meta_(\d{4}-\d{2}-\d{2})_(\d+)\.json$")
_RUN_ID_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d+)$")

# -------------------------------
# Deterministic scanning
# -------------------------------

# cache (lazy-loaded)
_GAME_ROUTING_CACHE: Optional[Dict[str, Any]] = None


def _get_game_routing() -> Dict[str, Any]:
    """
    Lazy-load game routing from games.json via game_router.

    This stays control-plane safe:
    - no validation
    - no adapter logic
    - no heavy dependency at import time
    """
    global _GAME_ROUTING_CACHE

    if _GAME_ROUTING_CACHE is not None:
        return _GAME_ROUTING_CACHE

    try:
        try:
            from .game_router import build_routing, DEFAULT_CONFIG_PATH
        except ImportError:
            from game_router import build_routing, DEFAULT_CONFIG_PATH

        routing = build_routing(DEFAULT_CONFIG_PATH)

        # expected contract:
        # routing.games = list of game configs
        # each game has:
        #   - game_id
        #   - match_keywords (optional)

        game_map: Dict[str, Dict[str, Any]] = {}

        for g in getattr(routing, "games", []) or []:
            game_id = getattr(g, "game_id", None)
            if not game_id:
                continue

            keywords = getattr(g, "match_keywords", None)

            if not keywords:
                # fallback: use game_id as keyword
                keywords = [game_id]

            game_map[game_id] = {
                "keywords": [str(k).casefold() for k in keywords],
            }

        _GAME_ROUTING_CACHE = game_map
        return game_map

    except Exception:
        # fallback: empty routing (will use heuristic)
        _GAME_ROUTING_CACHE = {}
        return _GAME_ROUTING_CACHE


def infer_game_id_from_path(path: Path) -> Optional[str]:
    """
    Best-effort game_id inference (control-plane only).

    Priority:
    1. games.json routing (keywords)
    2. fallback heuristic (legacy mapping)

    This is non-authoritative.
    Adapters / classifiers remain the source of truth.
    """

    lowered_parts = [p.casefold() for p in path.parts]
    joined = " / ".join(lowered_parts)

    # --------------------------------------------------
    # 1) config-driven routing (games.json)
    # --------------------------------------------------
    routing = _get_game_routing()

    for game_id, cfg in routing.items():
        for token in cfg.get("keywords", []):
            if token and token in joined:
                return game_id

    # --------------------------------------------------
    # 2) fallback heuristic (legacy safety)
    # --------------------------------------------------
    fallback = {
        "bang dream": "bandori",
        "bandori": "bandori",
        "project sekai": "pjsekai",
        "pj sekai": "pjsekai",
        "pjsekai": "pjsekai",
        "arcaea": "arcaea",
        "maimai": "maimai",
    }

    for token, game_id in fallback.items():
        if token in joined:
            return game_id

    return None


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
    - directory entries are sorted
    - final candidate list sorted by casefolded path
    """

    exts = set(allowed_extensions or DEFAULT_ALLOWED_EXTENSIONS)
    exts = {e.lower() for e in exts}

    candidates: List[Path] = []

    for p in _walk(root, ignore_hidden=ignore_hidden, follow_symlinks=follow_symlinks):

        if exts and p.suffix.lower() not in exts:
            continue

        if drop_system_files:
            nm = p.name.casefold()
            if nm in SYSTEM_BASENAMES:
                continue
            if p.name.startswith("._"):
                continue

        candidates.append(p)

    candidates.sort(key=lambda x: str(x).casefold())
    return candidates


def scan_many(roots: Sequence[Path], **kwargs) -> List[Path]:
    """Scan multiple root directories and merge results deterministically."""

    all_candidates: List[Path] = []

    for r in roots:
        try:
            all_candidates.extend(scan_directory(r, **kwargs))
        except Exception:
            continue

    uniq = sorted(
        {_normalize_key(p): p for p in all_candidates}.items(),
        key=lambda kv: kv[0].casefold(),
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
    try:
        return m.group(1), int(m.group(2))
    except Exception:
        return None


def _normalize_key(path: Path) -> str:
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

@contextmanager
def open_scan_inventory_db(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        yield conn
        conn.commit()
    finally:
        conn.close()


def ensure_scan_inventory_schema(conn: sqlite3.Connection) -> None:
    """
    Ensure schema for scan inventory (control-plane only).

    Design goals:
    - Backward compatible
    - Additive schema evolution
    - Deterministic + stable
    """

    cursor = conn.cursor()

    # --------------------------------------------------
    # Core tables (idempotent)
    # --------------------------------------------------
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS scan_runs (
            run_id TEXT PRIMARY KEY,
            report_date TEXT NOT NULL,
            report_seq INTEGER NOT NULL,
            generated_at TEXT NOT NULL,
            chart_root TEXT NOT NULL,
            total_candidates INTEGER NOT NULL,
            integrity_json TEXT
        );

        CREATE TABLE IF NOT EXISTS scan_candidates (
            candidate_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            source_path TEXT NOT NULL,
            normalized_key TEXT NOT NULL,
            basename TEXT NOT NULL,
            extension TEXT NOT NULL,
            size INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            file_hash TEXT,
            game_id TEXT,

            game_folder TEXT,
            difficulty_folder TEXT,
            level_folder TEXT,

            game_normalized TEXT,
            difficulty_normalized TEXT,
            level_normalized INTEGER,
            normalization_issues_json TEXT,

            parent_dir TEXT,
            relative_path TEXT,

            discovered_at TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES scan_runs(run_id)
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_scan_candidates_key_run
            ON scan_candidates(run_id, normalized_key);

        CREATE INDEX IF NOT EXISTS idx_scan_candidates_game
            ON scan_candidates(game_id);

        CREATE INDEX IF NOT EXISTS idx_scan_candidates_game_norm
            ON scan_candidates(game_normalized);

        CREATE INDEX IF NOT EXISTS idx_scan_candidates_diff_norm
            ON scan_candidates(difficulty_normalized);
        """
    )

    # --------------------------------------------------
    # Safe additive migration
    # --------------------------------------------------
    def _column_exists(table: str, column: str) -> bool:
        rows = cursor.execute(f"PRAGMA table_info({table})").fetchall()
        cols = {r[1] for r in rows}
        return column in cols

    def _safe_add_column(table: str, column: str, decl: str) -> None:
        if not _column_exists(table, column):
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")

    _safe_add_column("scan_candidates", "game_folder", "TEXT")
    _safe_add_column("scan_candidates", "difficulty_folder", "TEXT")
    _safe_add_column("scan_candidates", "level_folder", "TEXT")

    _safe_add_column("scan_candidates", "game_normalized", "TEXT")
    _safe_add_column("scan_candidates", "difficulty_normalized", "TEXT")
    _safe_add_column("scan_candidates", "level_normalized", "INTEGER")
    _safe_add_column("scan_candidates", "normalization_issues_json", "TEXT")

    _safe_add_column("scan_candidates", "parent_dir", "TEXT")
    _safe_add_column("scan_candidates", "relative_path", "TEXT")

    conn.commit()


def persist_scan_inventory(
    *,
    db_path: Path,
    chart_root: Path,
    run_id: str,
    report_date: str,
    report_seq: int,
    generated_at: str,
    candidates: Sequence[Path],
    include_file_hash: bool = False,
    integrity: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Persist deterministic scan inventory into SQLite.

    Control-plane only:
    - stores discovered candidates
    - stores fingerprints
    - stores raw + normalized identity
    - does NOT parse chart semantics
    """

    rows_written = 0

    with open_scan_inventory_db(db_path) as conn:
        ensure_scan_inventory_schema(conn)

        conn.execute(
            """
            INSERT OR REPLACE INTO scan_runs(
                run_id, report_date, report_seq, generated_at,
                chart_root, total_candidates, integrity_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                report_date,
                report_seq,
                generated_at,
                str(chart_root),
                len(candidates),
                json.dumps(integrity or {}, ensure_ascii=False),
            ),
        )

        # --------------------------------------------------
        # Deterministic iteration
        # --------------------------------------------------
        for p in sorted(candidates, key=lambda x: str(x).casefold()):
            try:
                fp = fingerprint(p)
            except FileNotFoundError:
                continue

            normalized_key = _normalize_key(p)
            candidate_id = f"{run_id}:{normalized_key}"

            file_hash = None
            if include_file_hash:
                try:
                    file_hash = sha256_file(p)
                except Exception:
                    file_hash = None

            # --------------------------
            # hierarchy (safe)
            # --------------------------
            try:
                hier = extract_chart_hierarchy(p)
            except Exception:
                hier = {}

            # --------------------------
            # normalization (safe)
            # --------------------------
            try:
                normalized_identity = normalize_folder_identity(
                    game_folder=hier.get("game_folder"),
                    difficulty_folder=hier.get("difficulty_folder"),
                    level_folder=hier.get("level_folder"),
                )
            except Exception:
                normalized_identity = {}

            # --------------------------
            # safe JSON encoding
            # --------------------------
            try:
                issues_json = json.dumps(
                    normalized_identity.get("issues") or [],
                    ensure_ascii=False,
                )
            except Exception:
                issues_json = "[]"

            # --------------------------
            # misc fields
            # --------------------------
            try:
                game_id = infer_game_id_from_path(p)
            except Exception:
                game_id = None

            parent_dir = str(p.parent)

            try:
                relative_path = str(p.relative_to(chart_root))
            except Exception:
                relative_path = str(p)

            # --------------------------
            # DB write (row-safe)
            # --------------------------
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO scan_candidates(
                        candidate_id,
                        run_id,
                        source_path,
                        normalized_key,
                        basename,
                        extension,
                        size,
                        mtime_ns,
                        file_hash,
                        game_id,

                        game_folder,
                        difficulty_folder,
                        level_folder,

                        game_normalized,
                        difficulty_normalized,
                        level_normalized,
                        normalization_issues_json,

                        parent_dir,
                        relative_path,
                        discovered_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        candidate_id,
                        run_id,
                        str(p),
                        normalized_key,
                        p.name,
                        p.suffix.lower(),
                        fp.size,
                        fp.mtime_ns,
                        file_hash,
                        game_id,

                        hier.get("game_folder"),
                        hier.get("difficulty_folder"),
                        hier.get("level_folder"),

                        normalized_identity.get("game"),
                        normalized_identity.get("difficulty"),
                        normalized_identity.get("level"),
                        issues_json,

                        parent_dir,
                        relative_path,
                        generated_at,
                    ),
                )
                rows_written += 1

            except Exception:
                # skip bad row (control-plane safety)
                continue

    return {
        "db_path": str(db_path),
        "rows_written": rows_written,
        "run_id": run_id,
    }

# -------------------------------
# Scan-state file IO + sequencing
# -------------------------------

def parse_state_filename(path: Path) -> Optional[Tuple[str, int]]:
    m = _STATE_RE.match(path.name)
    if not m:
        return None
    try:
        return m.group(1), int(m.group(2))
    except Exception:
        return None


def list_state_files(base_dir: Path) -> List[Path]:
    if not base_dir.exists():
        return []

    parsed: List[Tuple[Path, str, int]] = []

    for p in base_dir.iterdir():
        if not p.is_file():
            continue
        ps = parse_state_filename(p)
        if ps is None:
            continue
        parsed.append((p, ps[0], ps[1]))

    parsed.sort(key=lambda t: (t[1], t[2], t[0].name))
    return [t[0] for t in parsed]


def get_latest_state_path(base_dir: Path) -> Optional[Path]:
    files = list_state_files(base_dir)
    return files[-1] if files else None


def list_tips_meta_files(base_dir: Path) -> List[Path]:
    """
    List QA summary files (tips_meta_YYYY-MM-DD_?.json)
    """
    if not base_dir.exists():
        return []

    parsed: List[Tuple[Path, str, int]] = []

    for p in base_dir.iterdir():
        if not p.is_file():
            continue
        m = _TIPS_META_RE.match(p.name)
        if not m:
            continue
        try:
            parsed.append((p, m.group(1), int(m.group(2))))
        except Exception:
            continue

    parsed.sort(key=lambda t: (t[1], t[2], t[0].name))
    return [t[0] for t in parsed]


def next_run_seq(base_dir: Path, report_date: str) -> int:
    """
    Next available seq for a date by inspecting BOTH:
    - file_scan_state
    - tips_meta
    """

    if not base_dir.exists():
        return 1

    seqs: List[int] = []

    for p in base_dir.iterdir():
        if not p.is_file():
            continue

        # state files
        m1 = _STATE_RE.match(p.name)
        if m1 and m1.group(1) == report_date:
            try:
                seqs.append(int(m1.group(2)))
            except Exception:
                pass
            continue

        # tips_meta files
        m2 = _TIPS_META_RE.match(p.name)
        if m2 and m2.group(1) == report_date:
            try:
                seqs.append(int(m2.group(2)))
            except Exception:
                pass

    return (max(seqs) + 1) if seqs else 1


def allocate_run_id(base_dir: Path, report_date: str) -> Tuple[str, int]:
    seq = next_run_seq(base_dir, report_date)
    return make_run_id(report_date, seq), seq


def state_path_for_date_seq(base_dir: Path, report_date: str, seq: int) -> Path:
    return base_dir / f"file_scan_state_{report_date}_{seq}.json"


def load_state(state_path: Path) -> ScanState:
    if not state_path or not state_path.exists():
        return ScanState()

    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return ScanState()

    entries_raw = raw.get("entries") or {}
    entries: Dict[str, FileFingerprint] = {}

    for k, v in entries_raw.items():
        try:
            entries[k] = FileFingerprint(
                size=int(v.get("size", 0)),
                mtime_ns=int(v.get("mtime_ns", 0)),
            )
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
    """
    Atomic write to prevent partial/corrupted JSON.
    """
    state_path.parent.mkdir(parents=True, exist_ok=True)

    tmp = state_path.with_suffix(state_path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    os.replace(tmp, state_path)


def diff_unscanned(candidates: Sequence[Path], state: ScanState) -> List[Path]:
    """
    Return candidates that are new or changed vs scan-state.
    """
    unscanned: List[Path] = []

    for p in candidates:
        key = _normalize_key(p)

        try:
            fp = fingerprint(p)
        except FileNotFoundError:
            continue

        old = state.entries.get(key)

        if (
            old is None
            or old.size != fp.size
            or old.mtime_ns != fp.mtime_ns
        ):
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
    """
    Scheduling helper implementing 'must-scan-if-unscanned-exists'.
    """

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

    Control-plane only:
    - deterministic scan snapshot
    - no ingestion
    - no validation decisions

    Integrity includes:
    - content_hash_sha256
    - prev_content_hash_sha256 (chain within same date)
    - pair_content_hash_sha256 (optional tips_meta pairing)
    """

    # --------------------------------------------------
    # run_id parse
    # --------------------------------------------------
    parsed = parse_run_id(run_id)
    if not parsed:
        raise ValueError(f"Invalid run_id: {run_id}")

    report_date, seq = parsed

    # --------------------------------------------------
    # previous hash (same-day chain)
    # --------------------------------------------------
    prev_hash = None

    try:
        same_day_states = []
        for p in list_state_files(base_dir):
            parsed_state = parse_state_filename(p)
            if not parsed_state:
                continue
            if parsed_state[0] == report_date:
                same_day_states.append(p)
    except Exception:
        same_day_states = []

    if same_day_states:
        try:
            prev = json.loads(
                same_day_states[-1].read_text(encoding="utf-8")
            )
            integ = prev.get("integrity") or {}
            if isinstance(integ, dict):
                prev_hash = integ.get("content_hash_sha256")
        except Exception:
            prev_hash = None  # safe fallback

    # --------------------------------------------------
    # pair hash (tips_meta)
    # --------------------------------------------------
    pair_hash = None

    if pair_tips_meta_path and pair_tips_meta_path.exists():
        try:
            tips_meta = json.loads(
                pair_tips_meta_path.read_text(encoding="utf-8")
            )
            pair_hash = compute_content_hash_sha256(tips_meta)
        except Exception:
            pair_hash = None

    # --------------------------------------------------
    # entries (deterministic build)
    # --------------------------------------------------
    entries: Dict[str, Dict[str, Any]] = {}

    for p in sorted(candidates, key=lambda x: str(x).casefold()):
        try:
            fp = fingerprint(p)
        except FileNotFoundError:
            continue

        # ----------------------
        # hierarchy extraction (safe)
        # ----------------------
        try:
            hier = extract_chart_hierarchy(p)
        except Exception:
            hier = {}

        # ----------------------
        # normalization (safe)
        # ----------------------
        try:
            norm = normalize_folder_identity(
                game_folder=hier.get("game_folder"),
                difficulty_folder=hier.get("difficulty_folder"),
                level_folder=hier.get("level_folder"),
            )
        except Exception:
            norm = {}

        key = _normalize_key(p)

        entries[key] = {
            # file-level
            "size": fp.size,
            "mtime_ns": fp.mtime_ns,
            "basename": p.name,

            # raw hierarchy
            "game_folder": hier.get("game_folder"),
            "difficulty_folder": hier.get("difficulty_folder"),
            "level_folder": hier.get("level_folder"),

            # normalized identity
            "game_normalized": norm.get("game"),
            "difficulty_normalized": norm.get("difficulty"),
            "level_normalized": norm.get("level"),

            # normalization diagnostics
            "normalization_issues": norm.get("issues") or [],
        }

    # --------------------------------------------------
    # payload
    # --------------------------------------------------
    payload: Dict[str, Any] = {
        "version": 2,
        "report_date": report_date,
        "report_seq": seq,
        "run_id": run_id,
        "generated_at": utc_now_iso(),
        "entries": entries,
    }

    # --------------------------------------------------
    # integrity
    # --------------------------------------------------
    stamp_integrity(
        payload,
        prev_content_hash_sha256=prev_hash,
        pair_content_hash_sha256=pair_hash,
        schema_version=1,
    )

    # --------------------------------------------------
    # save
    # --------------------------------------------------
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
        try:
            hier = extract_chart_hierarchy(p)
            norm = normalize_folder_identity(
                game_folder=hier.get("game_folder"),
                difficulty_folder=hier.get("difficulty_folder"),
                level_folder=hier.get("level_folder"),
            )
        except Exception:
            hier = {}
            norm = {}

        print(f"  - {p}")
        print(
            f"      raw: game={hier.get('game_folder')}, "
            f"difficulty={hier.get('difficulty_folder')}, "
            f"level={hier.get('level_folder')}"
        )
        print(
            f"      normalized: game={norm.get('game')}, "
            f"difficulty={norm.get('difficulty')}, "
            f"level={norm.get('level')}"
        )

        if norm.get("issues"):
            print(f"      issues={norm.get('issues')}")

    if len(paths) > limit:
        print(f"  ... ({len(paths) - limit} more)")



def cli_main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser("RGA Phase 3 file scanner (manual handle)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--root",
            default=str(DEFAULT_CHART_ROOT),
            help=f"Root directory to scan (default: {DEFAULT_CHART_ROOT})",
        )
        p.add_argument(
            "--base-dir",
            default=str(DEFAULT_STATE_BASE_DIR),
            help=f"Output meta directory (default: {DEFAULT_STATE_BASE_DIR})",
        )
        p.add_argument(
            "--extensions",
            default=",".join(sorted(DEFAULT_ALLOWED_EXTENSIONS)),
            help="Comma-separated allowed extensions",
        )
        p.add_argument(
            "--include-hidden",
            action="store_true",
            help="Include hidden files and directories",
        )
        p.add_argument(
            "--follow-symlinks",
            action="store_true",
            help="Follow symlinks when walking directories",
        )
        p.add_argument(
            "--keep-system-files",
            action="store_true",
            help="Do not filter system files (Thumbs.db, .DS_Store, etc.)",
        )

    # --------------------------------------------------
    # inspect
    # --------------------------------------------------
    p_inspect = sub.add_parser(
        "inspect",
        help="Scan and print summary (no state write)",
    )
    add_common(p_inspect)
    p_inspect.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Max sample paths to print",
    )

    # --------------------------------------------------
    # diff
    # --------------------------------------------------
    p_diff = sub.add_parser(
        "diff",
        help="Scan and show unscanned vs latest state (no state write)",
    )
    add_common(p_diff)
    p_diff.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max unscanned paths to print",
    )

    # --------------------------------------------------
    # commit
    # --------------------------------------------------
    p_commit = sub.add_parser(
        "commit",
        help="Scan and write a new scan_state JSON",
    )
    add_common(p_commit)
    p_commit.add_argument(
        "--report-date",
        default=None,
        help="Report date YYYY-MM-DD (default: today local)",
    )
    p_commit.add_argument(
        "--seq",
        type=int,
        default=None,
        help="Optional explicit seq for the day",
    )
    p_commit.add_argument(
        "--run-id",
        default=None,
        help='Optional explicit run_id "YYYY-MM-DD_?" (overrides --report-date/--seq)',
    )
    p_commit.add_argument(
        "--pair-tips-meta",
        default=None,
        help="Optional path to paired tips_meta_YYYY-MM-DD_?.json to embed pair hash",
    )
    p_commit.add_argument(
        "--write-sqlite-inventory",
        action="store_true",
        help="Persist scan inventory to SQLite",
    )
    p_commit.add_argument(
        "--scan-db-path",
        default=None,
        help="Optional explicit SQLite inventory DB path",
    )
    p_commit.add_argument(
        "--include-file-hash",
        action="store_true",
        help="Include SHA-256 file hash in SQLite inventory (slower)",
    )
    p_commit.add_argument(
        "--asset-db-path",
        default=None,
        help="Optional explicit chart assets DB path (default: <base-dir>/chart_assets.db)",
    )
    p_commit.add_argument(
        "--verify-bundle",
        action="store_true",
        help="Run verify_asset_bundle after asset ingestion",
    )
    p_commit.add_argument(
        "--verify-json-out",
        default=None,
        help="Optional JSON path for verify_asset_bundle report",
    )
    p_commit.add_argument(
        "--chart-patterns-db",
        default=None,
        help="Optional explicit chart_patterns.db path for bundle verification",
    )
    p_commit.add_argument(
        "--delete-candidates",
        action="store_true",
        help="Actually delete candidate files (requires verification pass)",
    )
    
    p_commit.add_argument(
        "--delete-policy",
        default=None,
        help="Path to delete policy JSON",
    )


    # --------------------------------------------------
    # should-run
    # --------------------------------------------------
    p_should = sub.add_parser(
        "should-run",
        help="Exit 0 if unscanned exists, else 2",
    )
    add_common(p_should)

    args = parser.parse_args(argv)

    root = Path(args.root)
    base_dir = Path(args.base_dir)

    allowed_extensions = [
        e.strip() for e in str(args.extensions).split(",") if e.strip()
    ]
    ignore_hidden = not bool(args.include_hidden)
    follow_symlinks = bool(args.follow_symlinks)
    drop_system_files = not bool(args.keep_system_files)

    def _scan_candidates() -> List[Path]:
        return scan_directory(
            root,
            allowed_extensions=allowed_extensions,
            ignore_hidden=ignore_hidden,
            follow_symlinks=follow_symlinks,
            drop_system_files=drop_system_files,
        )

    # --------------------------------------------------
    # inspect
    # --------------------------------------------------
    if args.cmd == "inspect":
        candidates = _scan_candidates()

        print(f"Root: {root}")
        print(f"Candidates: {len(candidates)}")

        counts = _ext_counts(candidates)
        print("\nExtension counts:")
        for k, v in counts.items():
            print(f"  {k}: {v}")

        print("\nIdentity summary (first few):")
        seen = 0
        issues_counter: Dict[str, int] = {}

        for p in candidates:
            try:
                hier = extract_chart_hierarchy(p)
                norm = normalize_folder_identity(
                    game_folder=hier.get("game_folder"),
                    difficulty_folder=hier.get("difficulty_folder"),
                    level_folder=hier.get("level_folder"),
                )
            except Exception:
                continue

            if (
                norm.get("game") is not None
                or norm.get("difficulty") is not None
                or norm.get("level") is not None
            ):
                print(f"  raw={hier} -> normalized={norm}")
                seen += 1

            for issue in norm.get("issues") or []:
                issue_key = str(issue)
                issues_counter[issue_key] = issues_counter.get(issue_key, 0) + 1

            if seen >= 5:
                break

        if issues_counter:
            print("\nDetected normalization issues:")
            for k, v in sorted(
                issues_counter.items(),
                key=lambda kv: (-kv[1], kv[0]),
            ):
                print(f"  {k}: {v}")

        _print_sample("Sample candidates", candidates, args.limit)
        return 0

    # --------------------------------------------------
    # diff
    # --------------------------------------------------
    if args.cmd == "diff":
        candidates = _scan_candidates()

        latest = get_latest_state_path(base_dir)
        state = load_state(latest) if latest else ScanState()
        unscanned = diff_unscanned(candidates, state)

        print(f"Root: {root}")
        print(f"Candidates: {len(candidates)}")
        print(f"Latest state: {latest if latest else '(none)'}")
        print(f"Unscanned: {len(unscanned)}")

        _print_sample("Sample unscanned", unscanned, args.limit)
        return 0

    # --------------------------------------------------
    # should-run
    # --------------------------------------------------
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
        return 0 if should else 1

    # --------------------------------------------------
    # commit
    # --------------------------------------------------
    if args.cmd == "commit":
        candidates = scan_directory(
            root,
            allowed_extensions=allowed_extensions,
            ignore_hidden=ignore_hidden,
            follow_symlinks=follow_symlinks,
            drop_system_files=drop_system_files,
        )

        # ------------------------------------------
        # run_id
        # ------------------------------------------
        if args.run_id:
            run_id = str(args.run_id)
        else:
            report_date = args.report_date or date.today().isoformat()
            if args.seq is not None:
                run_id = make_run_id(report_date, int(args.seq))
            else:
                run_id, _ = allocate_run_id(base_dir, report_date)

        parsed = parse_run_id(run_id)
        if not parsed:
            raise ValueError(f"Invalid run_id: {run_id}")

        report_date, seq = parsed
        pair_path = Path(args.pair_tips_meta) if args.pair_tips_meta else None

        # ------------------------------------------
        # 1) scan-state commit
        # ------------------------------------------
        out_path, payload = commit_scan_state_for_run(
            candidates,
            base_dir=base_dir,
            run_id=run_id,
            pair_tips_meta_path=pair_path,
        )

        print(f"Wrote scan_state: {out_path}")
        print(f"run_id: {payload.get('run_id')}")
        print(f"entries: {len(payload.get('entries') or {})}")

        # ------------------------------------------
        # 2) optional SQLite inventory
        # ------------------------------------------
        scan_db_path_used: Optional[Path] = None

        if args.write_sqlite_inventory:
            scan_db_path_used = (
                Path(args.scan_db_path)
                if args.scan_db_path
                else base_dir / DEFAULT_SCAN_DB_FILENAME
            )

            db_result = persist_scan_inventory(
                db_path=scan_db_path_used,
                chart_root=root,
                run_id=run_id,
                report_date=report_date,
                report_seq=seq,
                generated_at=str(payload.get("generated_at") or utc_now_iso()),
                candidates=candidates,
                include_file_hash=bool(args.include_file_hash),
                integrity=payload.get("integrity"),
            )

            print(f"\nsqlite_inventory_db: {db_result['db_path']}")
            print(f"sqlite_rows_written: {db_result['rows_written']}")

        # ------------------------------------------
        # 3) asset ingestion (clean version ✅)
        # ------------------------------------------
        try:
            from writers.orchestrators import ingest_chart_assets_from_file_scan_candidates
        except Exception:
            ingest_chart_assets_from_file_scan_candidates = None

        asset_db_path = (
            Path(args.asset_db_path)
            if args.asset_db_path
            else base_dir / "chart_assets.db"
        )

        if ingest_chart_assets_from_file_scan_candidates:
            try:
                asset_candidates: List[Dict[str, Any]] = []

                for p in candidates:
                    try:
                        hier = extract_chart_hierarchy(p)
                    except Exception:
                        hier = {}

                    try:
                        inferred_game_id = infer_game_id_from_path(p)
                    except Exception:
                        inferred_game_id = None

                    asset_candidates.append(
                        {
                            "candidate_id": f"{run_id}:{_normalize_key(p)}",
                            "run_id": run_id,
                            "source_path": str(p),
                            "basename": p.name,
                            "extension": p.suffix.lower(),

                            # raw hierarchy
                            "game_folder": hier.get("game_folder"),
                            "difficulty_folder": hier.get("difficulty_folder"),
                            "level_folder": hier.get("level_folder"),

                            # hint
                            "game_id_hint": inferred_game_id,

                            # metadata
                            "extra_metadata": {
                                "source": "file_scan_commit",
                                "inferred_game_id": inferred_game_id,
                                "inferred_from": "path",
                                "inference_version": 1,
                            },
                        }
                    )

                asset_result = ingest_chart_assets_from_file_scan_candidates(
                    db_path=asset_db_path,
                    candidates=asset_candidates,
                )

                print(f"\n[ASSET INGEST]")
                print(f"  db: {asset_db_path}")
                print(f"  persisted: {asset_result['summary']['persisted_assets']}")
                print(f"  skipped: {asset_result['summary']['skipped_assets']}")
                print(f"  failed: {asset_result['summary']['failed_assets']}")

            except Exception as e:
                print(f"\n[ASSET INGEST FAILED] {e}")
        else:
            print("\n[ASSET INGEST SKIPPED] orchestrator import unavailable")

        # ------------------------------------------
        # 4) verify bundle
        # ------------------------------------------
        verify_summary = None

        if args.verify_bundle:
            try:
                from writers.validators import verify_asset_bundle
            except Exception:
                verify_asset_bundle = None

            if verify_asset_bundle:
                verify_report = verify_asset_bundle(
                    chart_asset_db=asset_db_path,
                    chart_patterns_db=Path(args.chart_patterns_db or "chart_patterns.db"),
                    file_scan_inventory_db=scan_db_path_used,
                    sample_limit=20,
                )

                verify_summary = verify_report.get("summary", {})

                print("\n[VERIFY BUNDLE]")
                print(f"  all_ok: {verify_summary.get('all_ok')}")
                print(f"  deletion_safe: {verify_summary.get('deletion_safe')}")

        # ------------------------------------------
        # 5) safe delete (policy-driven)
        # ------------------------------------------

        # explicit delete intent
        perform_delete = getattr(args, "delete_candidates", False)

        # policy flags (safe defaults)
        keep_at_least_one_copy = not bool(
            getattr(args, "allow_delete_last_copy", False)
        )
        only_type_a = not bool(
            getattr(args, "include_type_b_in_delete", False)
        )
        quarantine_dir = (
            Path(args.quarantine_dir)
            if getattr(args, "quarantine_dir", None)
            else None
        )

        if verify_summary and verify_summary.get("deletion_safe"):
            try:
                # consistent lazy import pattern
                try:
                    from writers.safety.safe_delete_candidates import safe_delete_candidates
                except Exception:
                    try:
                        from .safety.safe_delete_candidates import safe_delete_candidates
                    except Exception:
                        from safe_delete_candidates import safe_delete_candidates  # fallback

                # ----------------------------------
                # 5.1 policy display
                # ----------------------------------
                print("\n[SAFE DELETE POLICY]")
                print(f"  keep_at_least_one_copy: {keep_at_least_one_copy}")
                print(f"  only_type_a: {only_type_a}")
                print(f"  quarantine_dir: {quarantine_dir or '(default under chart_assets db dir)'}")
                print(f"  perform_delete: {perform_delete}")

                # ----------------------------------
                # 5.2 dry-run (ALWAYS first)
                # ----------------------------------
                dry_result = safe_delete_candidates(
                    paths=list(candidates),
                    chart_asset_db=asset_db_path,
                    chart_patterns_db=Path(args.chart_patterns_db or "chart_patterns.db"),
                    file_scan_inventory_db=scan_db_path_used,
                    policy_path=policy_path,
                    dry_run=True,
                    require_verification=True,
                    verify_report=verify_report if "verify_report" in locals() else None,
                    quarantine_dir=quarantine_dir,
                    keep_at_least_one_copy=keep_at_least_one_copy,
                    only_type_a=only_type_a,
                )

                dry_summary = dry_result.get("summary", {})

                print("\n[SAFE DELETE - DRY RUN]")
                print(f"  total_requested: {dry_summary.get('total_requested')}")
                print(f"  total_known_assets: {dry_summary.get('total_known_assets')}")
                print(f"  total_groups: {dry_summary.get('total_groups')}")
                print(f"  keep_count: {dry_summary.get('keep_count')}")
                print(f"  quarantine_count: {dry_summary.get('quarantine_count')}")
                print(f"  skip_count: {dry_summary.get('skip_count')}")
                print(f"  error_count: {dry_summary.get('error_count')}")
                print(f"  quarantine_dir: {dry_summary.get('quarantine_dir')}")

                print("\n[SAFE DELETE PLAN]")
                highlighted = dry_result.get("highlighted", []) or []
                for line in highlighted[:20]:
                    print(" ", line)
                if len(highlighted) > 20:
                    print(f"  ... ({len(highlighted) - 20} more)")

                # ----------------------------------
                # 5.3 actual execution (explicit only)
                # ----------------------------------
                if perform_delete:
                    print("\n[SAFE DELETE - EXECUTION]")
                    print("⚠️  WARNING: chart files will be moved to quarantine")

                    delete_result = safe_delete_candidates(
                        paths=list(candidates),
                        chart_asset_db=asset_db_path,
                        chart_patterns_db=Path(args.chart_patterns_db or "chart_patterns.db"),
                        file_scan_inventory_db=scan_db_path_used,
                        dry_run=False,
                        require_verification=True,
                        verify_report=verify_report if "verify_report" in locals() else None,
                        quarantine_dir=quarantine_dir,
                        keep_at_least_one_copy=keep_at_least_one_copy,
                        only_type_a=only_type_a,
                    )

                    delete_summary = delete_result.get("summary", {})

                    print(f"  keep_count: {delete_summary.get('keep_count')}")
                    print(f"  quarantine_count: {delete_summary.get('quarantine_count')}")
                    print(f"  skip_count: {delete_summary.get('skip_count')}")
                    print(f"  error_count: {delete_summary.get('error_count')}")
                    print(f"  quarantine_dir: {delete_summary.get('quarantine_dir')}")

                    print("\n[SAFE DELETE RESULT]")
                    highlighted_exec = delete_result.get("highlighted", []) or []
                    for line in highlighted_exec[:20]:
                        print(" ", line)
                    if len(highlighted_exec) > 20:
                        print(f"  ... ({len(highlighted_exec) - 20} more)")

                else:
                    print("\n[SAFE DELETE NOT EXECUTED]")
                    print("  Use --delete-candidates to enable actual quarantine move")

            except Exception as e:
                print(f"\n[SAFE DELETE FAILED] {type(e).__name__}: {e}")

        elif args.verify_bundle:
            print("\n[SAFE DELETE SKIPPED] verification not passed")