
# Orchestrator integration update for `runtime_meta.py`

This patch is designed as a wiring-layer update only. It does **not** change
completed phase logic; it only adds automatic run/context generation and
artifact naming.

## 1) Add import

```python
from rhythm_ingestion.runtime_meta import RuntimeMetaManager
```

## 2) Initialize runtime context near the top of `ingest(...)`

Place this after `src = Path(source_dir)` and the directory existence check:

```python
runtime = RuntimeMetaManager(repo_root=Path.cwd())
ctx = runtime.start_run(mode="manual")
```

## 3) Auto-resolve artifact paths when CLI values are not provided

Add this before file scan begins:

```python
resolved_db_path = db_path or str(runtime.build_artifact_path("song_db"))
resolved_json_out = json_out or str(runtime.build_artifact_path("song_db_meta"))
```

## 4) Keep ingest logic unchanged, but pass resolved output paths to writer/meta

Replace writer call:

```python
writer.write_rows(rows, db_path=db_path)
```

with:

```python
writer.write_rows(rows, db_path=resolved_db_path)
```

## 5) Build and write `song_db_meta`

After `rows` are built and before final logging, add:

```python
by_game = {}
for item in rows:
    gid = item.get("game_id")
    if not gid:
        continue
    slot = by_game.setdefault(gid, {"files": 0, "rows": 0, "failures": 0})
    slot["files"] += 1
    slot["rows"] += 1

song_db_meta = runtime.build_song_db_meta(
    db_file=Path(resolved_db_path).name,
    summary={
        "total_files_scanned": len(files),
        "total_supported_files": len(files),
        "rows_built": len(rows),
        "rows_written": len(rows) if not dry_run else 0,
    },
    validation={
        "routing_failures": 0,
        "adapter_failures": 0,
        "canonical_row_errors": 0,
        "validation_errors": 0,
    },
    by_game=by_game,
    data_quality={},
    lookup_stats={},
)

runtime.write_json_artifact("song_db_meta", song_db_meta)
```

## 6) Finalize run state

Add just before `return 0`:

```python
runtime.finalize_run(
    status="completed",
    extra={
        "db_file": resolved_db_path,
        "meta_file": resolved_json_out,
        "rows_built": len(rows),
    },
)
```

## 7) Optional: use the same runtime manager in scan / tips pipelines

Suggested artifact family:

- `file_scan_state_YYYY-MM-DD_SEQ.json`
- `song_db_YYYY-MM-DD_SEQ.xlsx`
- `song_db_meta_YYYY-MM-DD_SEQ.json`
- `tips_meta_YYYY-MM-DD_SEQ.json`

This mirrors the naming structure already seen in `tips_meta_2026-05-30_4.json`.
