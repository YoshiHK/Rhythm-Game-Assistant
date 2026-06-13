
from __future__ import annotations

"""
chart_pattern_writer.py

Framework writer for chart_patterns.db.

Design goals:
- Keep file_scan.py scanner-only / control-plane-only.
- Accept downstream extraction results from adapters / pattern extractors.
- Persist chart_patterns, pattern_features, and pattern_blobs according to
  chart_patterns.schema.json.
- Support deterministic, versioned, idempotent writes.

This module does NOT parse chart visuals on its own.
That responsibility belongs to downstream extractors/adapters.
"""

import argparse
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------
DEFAULT_DB_PATH = Path("chart_patterns.db")
DEFAULT_SCHEMA_PATH = Path("chart_patterns.schema.json")
DEFAULT_BLOB_ROOT = Path("chart_pattern_blobs")


# ---------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------
@dataclass(frozen=True)
class ChartPatternRow:
    chart_id: str
    game_id: str
    extraction_version: int
    pattern_hash: str
    note_count: Optional[int] = None
    section_count: Optional[int] = None
    dominant_pattern: Optional[str] = None
    difficulty_signal: Optional[float] = None
    created_at: Optional[str] = None


@dataclass(frozen=True)
class PatternFeatureRow:
    chart_id: str
    extraction_version: int
    density: Optional[float] = None
    burst_density: Optional[float] = None
    stream_length_avg: Optional[float] = None
    jump_ratio: Optional[float] = None
    hold_complexity: Optional[float] = None
    section_variance: Optional[float] = None
    spike_count: Optional[int] = None
    pattern_score_json: Optional[str] = None


@dataclass(frozen=True)
class PatternBlobRow:
    blob_id: str
    chart_id: str
    extraction_version: int
    blob_path: str
    compression_type: Optional[str] = None
    checksum: Optional[str] = None


@dataclass(frozen=True)
class ChartExtractionBundle:
    chart_pattern: ChartPatternRow
    pattern_features: Optional[PatternFeatureRow] = None
    pattern_blobs: Tuple[PatternBlobRow, ...] = ()
    source_path: Optional[str] = None


@dataclass(frozen=True)
class WriteSummary:
    db_path: str
    extraction_version: int
    chart_patterns_written: int
    pattern_features_written: int
    pattern_blobs_written: int


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_created_at(value: Optional[str]) -> str:
    return value or utc_now_iso()


def load_schema(schema_path: Path = DEFAULT_SCHEMA_PATH) -> Dict[str, Any]:
    return json.loads(schema_path.read_text(encoding="utf-8"))


@contextmanager
def open_db(db_path: Path) -> Iterator[sqlite3.Connection]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        yield conn
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------
# Schema / DDL
# ---------------------------------------------------------------------
def ensure_chart_pattern_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS chart_patterns (
            chart_id TEXT NOT NULL,
            game_id TEXT NOT NULL,
            extraction_version INTEGER NOT NULL,
            pattern_hash TEXT NOT NULL,
            note_count INTEGER,
            section_count INTEGER,
            dominant_pattern TEXT,
            difficulty_signal REAL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (chart_id, extraction_version)
        );

        CREATE TABLE IF NOT EXISTS pattern_features (
            chart_id TEXT NOT NULL,
            extraction_version INTEGER NOT NULL,
            density REAL,
            burst_density REAL,
            stream_length_avg REAL,
            jump_ratio REAL,
            hold_complexity REAL,
            section_variance REAL,
            spike_count INTEGER,
            pattern_score_json TEXT,
            PRIMARY KEY (chart_id, extraction_version),
            FOREIGN KEY(chart_id, extraction_version)
                REFERENCES chart_patterns(chart_id, extraction_version)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS pattern_blobs (
            blob_id TEXT PRIMARY KEY,
            chart_id TEXT NOT NULL,
            extraction_version INTEGER NOT NULL,
            blob_path TEXT NOT NULL,
            compression_type TEXT,
            checksum TEXT,
            FOREIGN KEY(chart_id, extraction_version)
                REFERENCES chart_patterns(chart_id, extraction_version)
                ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_chart_patterns_game
            ON chart_patterns(game_id);

        CREATE INDEX IF NOT EXISTS idx_chart_patterns_hash
            ON chart_patterns(pattern_hash);

        CREATE INDEX IF NOT EXISTS idx_pattern_blobs_chart
            ON pattern_blobs(chart_id, extraction_version);
        """
    )


# ---------------------------------------------------------------------
# Upserts
# ---------------------------------------------------------------------
def upsert_chart_pattern(conn: sqlite3.Connection, row: ChartPatternRow) -> None:
    conn.execute(
        """
        INSERT INTO chart_patterns(
            chart_id, game_id, extraction_version, pattern_hash,
            note_count, section_count, dominant_pattern,
            difficulty_signal, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(chart_id, extraction_version) DO UPDATE SET
            game_id=excluded.game_id,
            pattern_hash=excluded.pattern_hash,
            note_count=excluded.note_count,
            section_count=excluded.section_count,
            dominant_pattern=excluded.dominant_pattern,
            difficulty_signal=excluded.difficulty_signal,
            created_at=excluded.created_at
        """,
        (
            row.chart_id,
            row.game_id,
            row.extraction_version,
            row.pattern_hash,
            row.note_count,
            row.section_count,
            row.dominant_pattern,
            row.difficulty_signal,
            _normalize_created_at(row.created_at),
        ),
    )


def upsert_pattern_features(conn: sqlite3.Connection, row: PatternFeatureRow) -> None:
    conn.execute(
        """
        INSERT INTO pattern_features(
            chart_id, extraction_version, density, burst_density,
            stream_length_avg, jump_ratio, hold_complexity,
            section_variance, spike_count, pattern_score_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(chart_id, extraction_version) DO UPDATE SET
            density=excluded.density,
            burst_density=excluded.burst_density,
            stream_length_avg=excluded.stream_length_avg,
            jump_ratio=excluded.jump_ratio,
            hold_complexity=excluded.hold_complexity,
            section_variance=excluded.section_variance,
            spike_count=excluded.spike_count,
            pattern_score_json=excluded.pattern_score_json
        """,
        (
            row.chart_id,
            row.extraction_version,
            row.density,
            row.burst_density,
            row.stream_length_avg,
            row.jump_ratio,
            row.hold_complexity,
            row.section_variance,
            row.spike_count,
            row.pattern_score_json,
        ),
    )


def upsert_pattern_blob(conn: sqlite3.Connection, row: PatternBlobRow) -> None:
    conn.execute(
        """
        INSERT INTO pattern_blobs(
            blob_id, chart_id, extraction_version,
            blob_path, compression_type, checksum
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(blob_id) DO UPDATE SET
            chart_id=excluded.chart_id,
            extraction_version=excluded.extraction_version,
            blob_path=excluded.blob_path,
            compression_type=excluded.compression_type,
            checksum=excluded.checksum
        """,
        (
            row.blob_id,
            row.chart_id,
            row.extraction_version,
            row.blob_path,
            row.compression_type,
            row.checksum,
        ),
    )


# ---------------------------------------------------------------------
# Public writer API
# ---------------------------------------------------------------------
def write_chart_pattern_bundles(
    bundles: Sequence[ChartExtractionBundle],
    *,
    db_path: Path = DEFAULT_DB_PATH,
) -> WriteSummary:
    chart_count = 0
    feature_count = 0
    blob_count = 0

    with open_db(db_path) as conn:
        ensure_chart_pattern_schema(conn)

        for bundle in bundles:
            upsert_chart_pattern(conn, bundle.chart_pattern)
            chart_count += 1

            if bundle.pattern_features is not None:
                upsert_pattern_features(conn, bundle.pattern_features)
                feature_count += 1

            for blob in bundle.pattern_blobs:
                upsert_pattern_blob(conn, blob)
                blob_count += 1

    extraction_version = bundles[0].chart_pattern.extraction_version if bundles else 0
    return WriteSummary(
        db_path=str(db_path),
        extraction_version=extraction_version,
        chart_patterns_written=chart_count,
        pattern_features_written=feature_count,
        pattern_blobs_written=blob_count,
    )


# ---------------------------------------------------------------------
# Integration bridge from scan inventory
# ---------------------------------------------------------------------
def iter_scan_inventory_candidates(conn: sqlite3.Connection, run_id: Optional[str] = None) -> Iterable[Dict[str, Any]]:
    if run_id:
        cur = conn.execute(
            """
            SELECT candidate_id, run_id, source_path, normalized_key, basename,
                   extension, size, mtime_ns, file_hash, game_id, discovered_at
            FROM scan_candidates
            WHERE run_id = ?
            ORDER BY normalized_key COLLATE NOCASE ASC
            """,
            (run_id,),
        )
    else:
        cur = conn.execute(
            """
            SELECT candidate_id, run_id, source_path, normalized_key, basename,
                   extension, size, mtime_ns, file_hash, game_id, discovered_at
            FROM scan_candidates
            ORDER BY run_id COLLATE NOCASE ASC, normalized_key COLLATE NOCASE ASC
            """
        )

    cols = [d[0] for d in cur.description]
    for row in cur.fetchall():
        yield dict(zip(cols, row))


def write_from_scan_inventory(
    *,
    scan_db_path: Path,
    extractor: Callable[[Dict[str, Any]], Optional[ChartExtractionBundle]],
    output_db_path: Path = DEFAULT_DB_PATH,
    run_id: Optional[str] = None,
) -> WriteSummary:
    bundles: List[ChartExtractionBundle] = []

    with sqlite3.connect(str(scan_db_path)) as conn:
        for candidate in iter_scan_inventory_candidates(conn, run_id=run_id):
            bundle = extractor(candidate)
            if bundle is not None:
                bundles.append(bundle)

    return write_chart_pattern_bundles(bundles, db_path=output_db_path)


def phase5_bridge_extractor(candidate: Dict[str, Any]) -> Optional[ChartExtractionBundle]:
    """
    Phase 5 bridge extractor.

    Responsibilities:
    - Bridge existing Phase 1–2 / Phase 5 outputs into chart_patterns DB schema
    - DOES NOT parse raw chart files (adapter responsibility)
    - DOES NOT introduce new gameplay logic

    Expected future inputs:
    - SectionMetrics output
    - Pattern tags / taxonomy
    - Feature vectors

    Current behavior:
    - Framework-safe extraction using candidate metadata
    """

    # --------------------------------------------------
    # Basic identity
    # --------------------------------------------------
    chart_id = candidate.get("normalized_key")
    if not chart_id:
        return None

    game_id = candidate.get("game_id") or "unknown"
    extraction_version = 1

    # --------------------------------------------------
    # Pattern identity (deterministic)
    # --------------------------------------------------
    pattern_hash = (
        candidate.get("file_hash")
        or candidate.get("candidate_id")
        or chart_id
    )

    # --------------------------------------------------
    # PLACEHOLDER: Phase 1–2 / Phase 5 pipeline outputs
    #
    # These will later come from:
    # - SectionMetrics
    # - Pattern classification
    # - Feature aggregation
    # --------------------------------------------------

    note_count = None
    section_count = None
    dominant_pattern = None
    difficulty_signal = None

    # --------------------------------------------------
    # Feature layer (Phase 5 + Phase 7 consumption)
    # --------------------------------------------------
    pattern_features = PatternFeatureRow(
        chart_id=chart_id,
        extraction_version=extraction_version,

        density=None,
        burst_density=None,
        stream_length_avg=None,
        jump_ratio=None,
        hold_complexity=None,
        section_variance=None,
        spike_count=None,

        pattern_score_json=None,
    )

    # --------------------------------------------------
    # Blob layer (optional, future extension)
    # --------------------------------------------------
    pattern_blobs: Tuple[PatternBlobRow, ...] = ()

    # --------------------------------------------------
    # Bundle assembly
    # --------------------------------------------------
    return ChartExtractionBundle(
        chart_pattern=ChartPatternRow(
            chart_id=chart_id,
            game_id=game_id,
            extraction_version=extraction_version,
            pattern_hash=str(pattern_hash),
            note_count=note_count,
            section_count=section_count,
            dominant_pattern=dominant_pattern,
            difficulty_signal=difficulty_signal,
        ),
        pattern_features=pattern_features,
        pattern_blobs=pattern_blobs,
        source_path=candidate.get("source_path"),
    )

# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Write chart_patterns.db from scan inventory")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init-db", help="Initialize chart_patterns.db schema only")
    p_init.add_argument("--db-path", default=str(DEFAULT_DB_PATH))

    p_write = sub.add_parser("write-from-scan-db", help="Read scan inventory DB and populate chart_patterns.db via extractor")
    p_write.add_argument("--scan-db-path", required=True)
    p_write.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    p_write.add_argument("--run-id", default=None)
    p_write.add_argument("--use-example-extractor", action="store_true", help="Framework-only example extractor")

    return p


def cli_main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if args.cmd == "init-db":
        with open_db(Path(args.db_path)) as conn:
            ensure_chart_pattern_schema(conn)
        print(f"Initialized chart pattern DB: {args.db_path}")
        return 0

    if args.cmd == "write-from-scan-db":
        if not args.use_example_extractor:
            raise SystemExit(
                "No extractor selected. Use --use-example-extractor for framework validation, "
                "or wire a real adapter extractor in code."
            )

        summary = write_from_scan_inventory(
            scan_db_path=Path(args.scan_db_path),
            extractor=example_noop_extractor,
            output_db_path=Path(args.db_path),
            run_id=args.run_id,
        )

        print(json.dumps({
            "db_path": summary.db_path,
            "extraction_version": summary.extraction_version,
            "chart_patterns_written": summary.chart_patterns_written,
            "pattern_features_written": summary.pattern_features_written,
            "pattern_blobs_written": summary.pattern_blobs_written,
        }, indent=2, ensure_ascii=False))
        return 0

    return 1


__all__ = [
    "ChartPatternRow",
    "PatternFeatureRow",
    "PatternBlobRow",
    "ChartExtractionBundle",
    "WriteSummary",
    "ensure_chart_pattern_schema",
    "write_chart_pattern_bundles",
    "write_from_scan_inventory",
    "iter_scan_inventory_candidates",
    "example_noop_extractor",
    "DEFAULT_DB_PATH",
    "DEFAULT_SCHEMA_PATH",
    "DEFAULT_BLOB_ROOT",
]


if __name__ == "__main__":
    raise SystemExit(cli_main())
