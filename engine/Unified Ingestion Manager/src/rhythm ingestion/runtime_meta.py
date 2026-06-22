"""Runtime metadata manager for UMI artifacts.

Purpose:
- Provide a single run context for manual and scheduled executions.
- Generate consistent artifact names for file scan, song DB, song DB meta,
  and tips meta outputs.
- Maintain a per-date sequence index so run_id stays deterministic and
  traceable across the pipeline.

Notes:
- This module is a control-plane helper only.
- It does not modify Completed Phases logic.
- It is designed to be wired into existing CLI / orchestrator entrypoints.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_ARTIFACTS_DIRNAME = "artifacts"
DEFAULT_INDEX_FILENAME = "runtime_index.json"

ARTIFACT_SPECS: Dict[str, Dict[str, str]] = {
    "file_scan_state": {"prefix": "file_scan_state", "ext": ".json"},
    "song_db": {"prefix": "song_db", "ext": ".xlsx"},
    "song_db_meta": {"prefix": "song_db_meta", "ext": ".json"},
    "tips_meta": {"prefix": "tips_meta", "ext": ".json"},
    "personalization_meta": {"prefix": "personalization_meta", "ext": ".json"},
    "localization_meta": {"prefix": "localization_meta", "ext": ".json"},
    "song_recommendation_meta": {"prefix": "song_recommendation_meta", "ext": ".json"},
    "recommendation_meta": {"prefix": "recommendation_meta", "ext": ".json"}
}

def run_file_scan_wrapper(*, source_dir: str, output_path: str, **kwargs):
    from rhythm_ingestion.utils import scan_directory, log
    from pathlib import Path
    import json

    from rhythm_ingestion.orchestrator import SUPPORTED_CHART_EXTENSIONS

    src = Path(source_dir)

    files = scan_directory(
        src,
        allowed_extensions=sorted(SUPPORTED_CHART_EXTENSIONS),
    )

    total = len(files)
    run_id = kwargs.get("run_id") or "unknown"

    payload = {
        "report_type": "file_scan_state",
        "run_id": run_id,
        "report_date": kwargs.get("report_date"),
        "summary": {
            "total_files": total,
            "supported_files": total,
            "excluded_files": 0,
        },

        # full replay source
        "all_files": [str(p) for p in files],

        # lightweight preview
        "sample_files": [str(p) for p in files[:20]],

        "integrity": {
            "schema_version": 2,
        },
    }

    log(f"[SCAN] files={total}")

    Path(output_path).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return payload
    

def run_tips_wrapper(*, rows, output_path: str, **kwargs):

    from rhythm_ingestion.utils.tips_meta_builder import build_tips_meta
    from pathlib import Path
    import json

    payload = build_tips_meta(
        rows=rows,
        run_id=kwargs.get("run_id") or "unknown",
        report_date=kwargs.get("report_date"),
        tips_mode=kwargs.get("tips_mode", "production"),
    )

    Path(output_path).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return payload
    

def run_personalization_wrapper(*, rows, output_path: str, **kwargs):
    """
    Phase 4 personalization wrapper.

    Safe design:
    - does NOT modify completed phase logic
    - only builds a personalization_meta artifact
    - consumes runtime signals already available at the pipeline surface
    """
    from datetime import datetime, timezone
    from pathlib import Path
    import json

    batch_summary = kwargs.get("batch_summary") or {}
    locale = kwargs.get("locale", "en-US")

    player_signals = kwargs.get("player_signals") or {}
    preferences = kwargs.get("preferences") or {}
    player_profile = kwargs.get("player_profile") or {}
    player_history = kwargs.get("player_history") or {}

    def _to_float(v, default=0.0):
        try:
            if v is None or v == "":
                return default
            return float(v)
        except Exception:
            return default

    total_rows = len(rows)
    games = sorted(
        list(
            {
                item.get("game_id")
                for item in rows
                if isinstance(item, dict) and item.get("game_id")
            }
        )
    )

    # ------------------------------------------------------
    # Simple capability snapshot (safe / metadata-only)
    # ------------------------------------------------------
    expert_ap = _to_float(player_signals.get("expert_ap_count"))
    expert_fc = _to_float(player_signals.get("expert_fc_count"))
    master_ap = _to_float(player_signals.get("master_ap_count"))
    master_fc = _to_float(player_signals.get("master_fc_count"))
    expert_clear = _to_float(player_signals.get("expert_clear_rate"))
    master_clear = _to_float(player_signals.get("master_clear_rate"))

    signal_score = (
        expert_ap * 3.0
        + expert_fc * 2.0
        + master_ap * 4.0
        + master_fc * 3.0
        + expert_clear * 0.25
        + master_clear * 0.35
    )

    highest_confirmed = (
        player_signals.get("highest_confirmed_difficulty")
        or player_profile.get("highest_confirmed_difficulty")
        or "Expert"
    )

    allow_personalization = bool(preferences.get("allow_personalization", True))
    variant = preferences.get("variant", "expert")

    # Lightweight inferred capability bucket
    if signal_score >= 120:
        capability_tier = "advanced"
        recommended_focus = "master_growth"
    elif signal_score >= 40:
        capability_tier = "intermediate"
        recommended_focus = "expert_consistency"
    else:
        capability_tier = "beginner"
        recommended_focus = "clear_stability"

    payload = {
        "report_type": "personalization_meta",
        "run_id": kwargs.get("run_id") or "unknown",
        "report_date": kwargs.get("report_date"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "locale": locale,

        "summary": {
            "total_rows": total_rows,
            "games_count": len(games),
        },

        "inputs": {
            "player_signals_present": bool(player_signals),
            "preferences_present": bool(preferences),
            "player_profile_present": bool(player_profile),
            "player_history_present": bool(player_history),
            "batch_summary_present": bool(batch_summary),
        },

        "player_signals": {
            "expert_ap_count": player_signals.get("expert_ap_count"),
            "expert_fc_count": player_signals.get("expert_fc_count"),
            "master_ap_count": player_signals.get("master_ap_count"),
            "master_fc_count": player_signals.get("master_fc_count"),
            "expert_clear_rate": player_signals.get("expert_clear_rate"),
            "master_clear_rate": player_signals.get("master_clear_rate"),
            "highest_confirmed_difficulty": highest_confirmed,
        },

        "preferences": {
            "variant": variant,
            "allow_personalization": allow_personalization,
        },

        "personalization": {
            "applied": allow_personalization,
            "capability_tier": capability_tier,
            "recommended_focus": recommended_focus,
            "signal_score": signal_score,

            "decision_source": "rule_based_engine",
            "applied_reason": (
                "allowed_by_preferences"
                if allow_personalization else
                "disabled_by_user"
            ),
        },

        "coverage": {
            "games": games,
            "tips_mode": batch_summary.get("tips_mode"),
            "batch_total_rows": batch_summary.get("total_rows"),
        },

        "pipeline": {
            "stage": "personalization",
            "mode": "inference_only",
            "deterministic": True,
        },

        "integrity": {
            "schema_version": 2,
        },
    }

    Path(output_path).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return payload

def run_localization_wrapper(*, rows, output_path: str, **kwargs):
    """
    Phase 4.5 localization wrapper.

    Safe design:
    - does NOT change recommendation / tips logic
    - only builds a localization_meta artifact
    - records locale-aware message templates / fallback behavior
    """
    from datetime import datetime, timezone
    from pathlib import Path
    import json

    requested_locale = kwargs.get("locale", "en-US")
    
    if not requested_locale:
        requested_locale = "en-US"

    batch_summary = kwargs.get("batch_summary") or {}
    personalization_result = kwargs.get("personalization_result") or {}
    tips_result = kwargs.get("tips_result") or {}

    total_rows = len(rows)

    games = sorted(
        list(
            {
                item.get("game_id")
                for item in rows
                if isinstance(item, dict) and item.get("game_id")
            }
        )
    )


    def _translation_provider(locale: str):
        """
        Phase 4.5 Translation Provider

        Supports:
        - Canonical locales: en, zh, ja, ko
        - Regional variants: en-US, zh-HK, zh-TW, ja-JP, ko-KR, etc.
        """

        def _normalize_locale(loc):
            if not loc:
                return "en"

            loc = loc.lower()

            if loc.startswith("en"):
                return "en"
            if loc.startswith("zh"):
                return "zh"
            if loc.startswith("ja"):
                return "ja"
            if loc.startswith("ko"):
                return "ko"

            return "en"  # fallback to english

        canonical = _normalize_locale(locale)
        
        I18N = {
            "en": {
                "headline": "Your recommendation is ready",
                "tips_label": "Gameplay Tips",
                "recommendation_label": "Recommended Songs",
                "locale_status": "English template applied",
            },
            "zh": {
                "headline": "你的推薦已準備好",
                "tips_label": "遊玩提示",
                "recommendation_label": "推薦歌曲",
                "locale_status": "已套用中文模板",
            },
            "ja": {
                "headline": "おすすめの結果が準備できました",
                "tips_label": "プレイのコツ",
                "recommendation_label": "おすすめ楽曲",
                "locale_status": "日本語テンプレートを適用しました",
            },
            "ko": {
                "headline": "추천 결과가 준비되었습니다",
                "tips_label": "플레이 팁",
                "recommendation_label": "추천 곡",
                "locale_status": "한국어 템플릿이 적용되었습니다",
            },
        }

        localized = I18N.get(canonical)
        fallback_used = False

        if localized is None:
            localized = I18N["en"]
            fallback_used = True
            canonical = "en"

        return localized, fallback_used, canonical

    # ------------------------------------------------------
    # Resolve localization
    # ------------------------------------------------------

    localized, fallback_used, canonical = _translation_provider(requested_locale)

    # safe getter
    def _safe(key, default=""):
        return localized.get(key) or default

    # ------------------------------------------------------
    # Build payload
    # ------------------------------------------------------

    payload = {
        "report_type": "localization_meta",
        "run_id": kwargs.get("run_id") or "unknown",
        "report_date": kwargs.get("report_date"),
        "generated_at": datetime.now(timezone.utc).isoformat(),

        "locale": requested_locale,

        "summary": {
            "total_rows": total_rows,
            "games_count": len(games),
        },

        "coverage": {
            "games": games,
            "tips_mode": batch_summary.get("tips_mode"),
            "batch_total_rows": batch_summary.get("total_rows"),
        },

        "messages": {
            "headline": _safe("headline"),
            "tips_label": _safe("tips_label"),
            "recommendation_label": _safe("recommendation_label"),
            "locale_status": _safe("locale_status"),
        },

        "sources": {
            "personalization_present": bool(personalization_result),
            "tips_present": bool(tips_result),
        },

        "localization": {
            "requested_locale": requested_locale,   
            "resolved_locale": canonical,           
            "fallback_used": fallback_used,
            "translation_source": "in_memory_provider",
        },

        "integrity": {
            "schema_version": 2,
        }
    }

    # ------------------------------------------------------
    # Write artifact
    # ------------------------------------------------------

    Path(output_path).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return payload
    
def run_song_recommendation_wrapper(*, rows, output_path: str, **kwargs):
    from pathlib import Path
    import json
    from datetime import datetime, timezone

    run_id = kwargs.get("run_id") or "unknown"
    report_date = kwargs.get("report_date")

    total = len(rows)

    # ------------------------------------------------------
    # Build candidate list (simple ranking baseline)
    # ------------------------------------------------------
    candidates = []

    for idx, item in enumerate(rows):
        row = item.get("canonical_row") or {}
        name = row.get("name")

        if not name:
            continue

        candidates.append({
            "rank": idx + 1,
            "song_name": name,
            "game_id": row.get("game_id"),
            "difficulty": row.get("difficulty"),

            # ✅ placeholder scoring (future upgrade point)
            "score": max(0.0, 1.0 - (idx * 0.05)),

            # ✅ explainability-ready (align with API rationale)            
            "reason_codes": ["top_ranked"],
            "primary_reason": "top_ranked",

        })

    # keep top N
    top_n = min(10, len(candidates))
    selected = candidates[:top_n]

    # ------------------------------------------------------
    # Build payload
    # ------------------------------------------------------
    payload = {
        "report_type": "song_recommendation_meta",
        "run_id": run_id,
        "report_date": report_date,
        "generated_at": datetime.now(timezone.utc).isoformat(),

        "summary": {
            "total_rows": total,
            "candidates": len(candidates),
            "recommended_count": len(selected),
        },

        "recommendations": {
            "items": selected,
            "strategy": "rank_truncate_v1",
        },

        "coverage": {
            "has_names": sum(1 for c in candidates if c.get("song_name")),
        },

        "pipeline": {
            "stage": "song_recommendation",
            "mode": "offline_batch",
            "deterministic": True,
        },

        "integrity": {
            "schema_version": 2,
        },
    }

    Path(output_path).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return payload
    
def run_recommendation_wrapper(*, rows, output_path: str, **kwargs):

    from rhythm_ingestion.utils.recommendation_builder import build_recommendation_meta
    from pathlib import Path
    import json
    from datetime import datetime, timezone

    run_id = kwargs.get("run_id") or "unknown"
    report_date = kwargs.get("report_date")

    base_payload = build_recommendation_meta(
        rows=rows,
        run_id=run_id,
        report_date=report_date,
    )

    # ------------------------------------------------------
    # Build reasoning-enhanced items (Phase 7 alignment)
    # ------------------------------------------------------
    enriched_items = []

    candidates = base_payload.get("recommendations", {}).get("items", [])

    if isinstance(candidates, list):
        for idx, item in enumerate(candidates):

            score = item.get("score")
            rank = item.get("rank")

            # simple baseline reasoning (expandable later)
            reason_codes = []

            if rank == 1:
                reason_codes.append("top_match")
            if score is not None:
                if score >= 0.9:
                    reason_codes.append("high_score")
                elif score >= 0.7:
                    reason_codes.append("strong_match")
                else:
                    reason_codes.append("moderate_match")

            # fallback if nothing triggered
            if not reason_codes:
                reason_codes = ["default_match"]

            enriched_items.append({
                **item,

                # unified reasoning format (match API)
                "reason_codes": reason_codes,
                "primary_reason": reason_codes[0],

                # keep traceability
                "rank": rank,
                "score": score,
            })

    # ------------------------------------------------------
    # Build final payload
    # ------------------------------------------------------
    payload = base_payload

    payload["report_type"] = "game_recommendation_meta"
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()

    payload["recommendations"] = {
        "items": enriched_items,
        "strategy": "game_rank_v1",
    }

    payload.setdefault("pipeline", {
        "stage": "game_recommendation",
        "mode": "offline_batch",
        "deterministic": True,
    })

    payload.setdefault("integrity", {
        "schema_version": 3,
    })

    Path(output_path).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return payload

@dataclass(frozen=True)
class RuntimeContext:
    run_id: str
    report_date: str
    report_seq: int
    mode: str
    started_at: str
    artifacts_dir: str


class RuntimeMetaManager:
    def __init__(
        self,
        *,
        repo_root: Optional[str | Path] = None,
        artifacts_root: Optional[str | Path] = None,
        index_path: Optional[str | Path] = None,
    ) -> None:
        self.repo_root = Path(repo_root) if repo_root else Path.cwd()
        self.artifacts_root = Path(artifacts_root) if artifacts_root else self.repo_root / DEFAULT_ARTIFACTS_DIRNAME
        self.index_path = Path(index_path) if index_path else self.artifacts_root / DEFAULT_INDEX_FILENAME
        self.current_context: Optional[RuntimeContext] = None

        self.artifacts_root.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self._write_index({
                "schema_version": 1,
                "by_date": {},
                "last_run": None,
            })

    # ------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------
    def _read_index(self) -> Dict[str, Any]:
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except Exception:
            return {
                "schema_version": 1,
                "by_date": {},
                "last_run": None,
            }

    def _write_index(self, data: Dict[str, Any]) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ------------------------------------------------------------
    # Run lifecycle
    # ------------------------------------------------------------
    def start_run(self, *, mode: str = "manual", now: Optional[datetime] = None) -> RuntimeContext:
        now = now or datetime.now(timezone.utc)
        report_date = now.astimezone().date().isoformat()

        index = self._read_index()
        by_date = index.setdefault("by_date", {})
        seq = int(by_date.get(report_date, 0)) + 1
        by_date[report_date] = seq

        run_id = f"{report_date}_{seq}"
        run_dir = self.artifacts_root / report_date / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        ctx = RuntimeContext(
            run_id=run_id,
            report_date=report_date,
            report_seq=seq,
            mode=str(mode),
            started_at=now.isoformat(),
            artifacts_dir=str(run_dir),
        )
        self.current_context = ctx

        index["last_run"] = {
            "run_id": ctx.run_id,
            "report_date": ctx.report_date,
            "report_seq": ctx.report_seq,
            "mode": ctx.mode,
            "started_at": ctx.started_at,
            "artifacts_dir": ctx.artifacts_dir,
            "status": "started",
        }
        self._write_index(index)
        
        
        # ------------------------------------------------------
        # CLEANUP: remove empty date folder (legacy / safety)
        # ------------------------------------------------------
        try:
            for date_dir in self.artifacts_root.glob("*"):
                if not date_dir.is_dir():
                    continue

                # check if contains any run_id folders
                has_run_dirs = any(p.is_dir() for p in date_dir.iterdir())

                if not any(date_dir.iterdir()):
                    date_dir.rmdir()

        except Exception:
            pass


        return ctx

    def get_current_context(self) -> RuntimeContext:
        if self.current_context is None:
            raise RuntimeError("No active runtime context. Call start_run() first.")
        return self.current_context

    def finalize_run(self, *, status: str = "completed", extra: Optional[Dict[str, Any]] = None) -> None:
        ctx = self.get_current_context()
        index = self._read_index()
        last_run = index.get("last_run") or {}
        last_run.update({
            "run_id": ctx.run_id,
            "report_date": ctx.report_date,
            "report_seq": ctx.report_seq,
            "mode": ctx.mode,
            "started_at": ctx.started_at,
            "artifacts_dir": ctx.artifacts_dir,
            "status": status,
        })
        if extra:
            last_run.update(extra)
        index["last_run"] = last_run
        self._write_index(index)

    # ------------------------------------------------------------
    # Artifact naming
    # ------------------------------------------------------------
    def build_artifact_name(self, artifact_type: str) -> str:
        spec = ARTIFACT_SPECS[artifact_type]
        return f"{spec['prefix']}{spec['ext']}"

    def build_artifact_path(self, artifact_type: str) -> Path:
        ctx = self.get_current_context()
        return Path(ctx.artifacts_dir) / self.build_artifact_name(artifact_type)

    # ------------------------------------------------------------
    # Metadata builders
    # ------------------------------------------------------------
    def build_song_db_meta(
        self,
        *,
        db_file: str,
        summary: Dict[str, Any],
        validation: Dict[str, Any],
        by_game: Dict[str, Any],
        data_quality: Optional[Dict[str, Any]] = None,
        lookup_stats: Optional[Dict[str, Any]] = None,
        integrity: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ctx = self.get_current_context()
        return {
            "report_type": "song_db_meta",
            "report_date": ctx.report_date,
            "report_seq": ctx.report_seq,
            "run_id": ctx.run_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "db_file": db_file,
            "pipeline": {
                "phase": "Phase 3 - Unified Ingestion Manager",
                "mode": ctx.mode,
            },
            "summary": summary,
            "validation": validation,
            "by_game": by_game,
            "data_quality": data_quality or {},
            "lookup_stats": lookup_stats or {},
            "integrity": integrity or {
                "schema_version": 1,
                "hash_algo": "sha256",
                "content_hash_sha256": None,
                "prev_content_hash_sha256": None,
            },
        }

    def write_json_artifact(self, artifact_type: str, payload: Dict[str, Any]) -> Path:
        path = self.build_artifact_path(artifact_type)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def snapshot_context(self) -> Dict[str, Any]:
        return asdict(self.get_current_context())

    # ------------------------------------------------------------
    # Pipeline runner
    # ------------------------------------------------------------

    def run_ingestion_pipeline(
        self,
        *,
        ingest_fn,
        source_dir: str,
        mode: str = "scheduled",
        scan_state_path: Optional[str] = None,
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Unified runner for ingestion pipeline (manual or scheduled).

        ingest_fn = orchestrator.ingest (injected)

        Phase 3.5 note:
        - If scan_state_path is provided, ingestion may reuse a previous scan snapshot
          instead of walking the source tree again.
        """

        kwargs = dict(kwargs or {})

        if scan_state_path:
            kwargs.setdefault("scan_state_path", scan_state_path)

        ctx = self.start_run(mode=mode)

        db_path = str(self.build_artifact_path("song_db"))
        meta_path = str(self.build_artifact_path("song_db_meta"))

        result_code = 1
        status = "failed"

        try:
            ingest_result = ingest_fn(
                source_dir,
                db_path=db_path,
                json_out=meta_path,
                dry_run=False,
                only_game=None,
                **kwargs,
            )

            if isinstance(ingest_result, dict):
                result_code = int(ingest_result.get("status_code", 1))
            else:
                result_code = int(ingest_result)

            status = "completed" if result_code == 0 else "failed"

        except Exception as e:
            status = "failed"
            self.write_json_artifact(
                "song_db_meta",
                {
                    "report_type": "song_db_meta",
                    "error": str(e),
                    "run_id": ctx.run_id,
                    "scan_state_path": scan_state_path,
                },
            )

        self.finalize_run(
            status=status,
            extra={
                "db_file": db_path,
                "meta_file": meta_path,
                "result_code": result_code,
                "source_dir": source_dir,
                "scan_state_path": scan_state_path,
            },
        )

        return {
            "run_id": ctx.run_id,
            "status": status,
            "db_path": db_path,
            "meta_path": meta_path,
            "scan_state_path": scan_state_path,
        }


    def run_full_pipeline(
        self,
        *,
        source_dir: str,
        ingest_fn,
        scan_fn=None,
        tips_fn=None,
        personalization_fn=None,
        localization_fn=None,
        song_recommendation_fn=None,
        recommendation_fn=None,
        mode: str = "scheduled",
        use_scan_state: bool = True,
        ingest_kwargs: Optional[Dict[str, Any]] = None,
        tips_kwargs: Optional[Dict[str, Any]] = None,
        personalization_kwargs: Optional[Dict[str, Any]] = None,
        localization_kwargs: Optional[Dict[str, Any]] = None,
        song_recommendation_kwargs: Optional[Dict[str, Any]] = None,
        recommendation_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        ingest_kwargs = dict(ingest_kwargs or {})
        tips_kwargs = dict(tips_kwargs or {})
        personalization_kwargs = dict(personalization_kwargs or {})
        localization_kwargs = dict(localization_kwargs or {})
        song_recommendation_kwargs = dict(song_recommendation_kwargs or {})
        recommendation_kwargs = dict(recommendation_kwargs or {})

        ctx = self.start_run(mode=mode)

        db_path = str(self.build_artifact_path("song_db"))
        db_meta_path = str(self.build_artifact_path("song_db_meta"))
        scan_path = str(self.build_artifact_path("file_scan_state"))
        tips_path = str(self.build_artifact_path("tips_meta"))
        personalization_path = str(self.build_artifact_path("personalization_meta"))
        localization_path = str(self.build_artifact_path("localization_meta"))
        song_rec_path = str(self.build_artifact_path("song_recommendation_meta"))
        rec_path = str(self.build_artifact_path("recommendation_meta"))

        result: Dict[str, Any] = {
            "run_id": ctx.run_id,
            "status": "started",
            "artifact_dir": ctx.artifacts_dir,
            "scan": None,
            "ingestion": None,
            "tips": None,
            "personalization": None,
            "localization": None,
            "song_recommendation": None,
            "recommendation": None,
            "integrity_check": None,
        }

        rows: List[Dict[str, Any]] = []
        batch_summary = None

        # Phase 3.5 state reuse hook
        scan_state_for_ingest: Optional[str] = None

        # ------------------------------------------------------
        # 1) FILE SCAN (incremental / reuse-aware)
        # ------------------------------------------------------
        try:
            if scan_fn:

                reuse_scan = False

                # condition: existing scan artifact present
                try:
                    from pathlib import Path

                    existing = Path(scan_path)
                    if existing.exists():
                        reuse_scan = True
                except Exception:
                    reuse_scan = False

                if reuse_scan:
                    # Phase 3.5 behavior: reuse scan snapshot
                    result["scan"] = {
                        "status": "reused",
                        "output": scan_path,
                    }
                    
                    from rhythm_ingestion.writers.persistence import (
                        file_scan_inventory_writer,
                    )

                    file_scan_inventory_writer.persist_from_scan_state(
                        scan_state_path=scan_path,
                        db_path=r"C:\Users\edfwh\OneDrive\Desktop\Rhythm Game Assistant\Github Repository\runtime\ingestion\file_scan_inventory.db"
                    )

                else:
                    # fallback: full scan
                    scan_fn(
                        source_dir=source_dir,
                        output_path=scan_path,
                        run_id=ctx.run_id,
                        report_date=ctx.report_date,
                    )

                    result["scan"] = {
                        "status": "completed",
                        "output": scan_path,
                    }

            else:
                result["scan"] = {"status": "skipped"}

        except Exception as e:
            result["scan"] = {
                "status": "failed",
                "error": str(e),
            }
    
        # ------------------------------------------------------
        # 2) INGESTION
        # ------------------------------------------------------
        try:
            # ------------------------------------------
            # Phase 3.5: allow ingestion to reuse scan snapshot
            # ------------------------------------------
            effective_ingest_kwargs = dict(ingest_kwargs)

            if use_scan_state:
                scan_info = result.get("scan") or {}
                scan_status = scan_info.get("status")
                scan_output = scan_info.get("output")

                if scan_status in {"completed", "reused"} and scan_output:
                    scan_state_for_ingest = str(scan_output)
                    effective_ingest_kwargs.setdefault("scan_state_path", scan_state_for_ingest)

            ingest_result = ingest_fn(
                source_dir,
                db_path=db_path,
                json_out=db_meta_path,
                dry_run=False,
                only_game=None,
                **effective_ingest_kwargs,
            )

            if isinstance(ingest_result, dict):
                status_code = int(ingest_result.get("status_code", 1))
                ingest_status = "completed" if status_code == 0 else "failed"
                rows = ingest_result.get("rows") or []
                batch_summary = ingest_result.get("batch_summary")
            else:
                status_code = int(ingest_result)
                ingest_status = "completed" if status_code == 0 else "failed"
                rows = []
                batch_summary = None

            result["ingestion"] = {
                "status": ingest_status,
                "rows": len(rows),
                "db_path": db_path,
                "meta_path": db_meta_path,
            }

            if scan_state_for_ingest:
                result["ingestion"]["scan_state_path"] = scan_state_for_ingest
                result["ingestion"]["scan_mode"] = "reused_snapshot"                
                result["ingestion"]["incremental_skip_enabled"] = True
                result["ingestion"]["chart_asset_db"] = (
                    ingest_kwargs.get("chart_asset_db")
                    or ingest_kwargs.get("chart_assets_db")
)


            if batch_summary is not None:
                result["ingestion"]["batch_summary"] = batch_summary

            if ingest_status != "completed":
                fail_extra = dict(result)
                fail_extra["source_dir"] = source_dir
                fail_extra["scan_state_path"] = scan_state_for_ingest

                self.finalize_run(status="failed", extra=fail_extra)
                result["status"] = "failed"
                return result

        except Exception as e:
            result["ingestion"] = {
                "status": "completed_with_warnings",
                "error": str(e),
            }

            if scan_state_for_ingest:
                result["ingestion"]["scan_state_path"] = scan_state_for_ingest
                result["ingestion"]["scan_mode"] = "reused_snapshot"

            warn_extra = dict(result)
            warn_extra["source_dir"] = source_dir
            warn_extra["scan_state_path"] = scan_state_for_ingest

            self.finalize_run(status="completed_with_warnings", extra=warn_extra)

            result["status"] = "completed_with_warnings"
            return result


        # ------------------------------------------------------
        # 3) TIPS
        # ------------------------------------------------------
        try:
            if tips_fn:
                tips_fn(
                    rows=rows,
                    output_path=tips_path,
                    run_id=ctx.run_id,
                    report_date=ctx.report_date,
                    **tips_kwargs,
                )
                result["tips"] = {
                    "status": "completed",
                    "output": tips_path,
                }
            else:
                result["tips"] = {"status": "skipped"}

        except Exception as e:
            result["tips"] = {
                "status": "failed",
                "error": str(e),
            }

        # ------------------------------------------------------
        # 4) PERSONALIZATION (Phase 4)
        # ------------------------------------------------------
        try:
            if personalization_fn:
                personalization_fn(
                    rows=rows,
                    batch_summary=batch_summary,
                    output_path=personalization_path,
                    run_id=ctx.run_id,
                    report_date=ctx.report_date,
                    **personalization_kwargs,
                )
                result["personalization"] = {
                    "status": "completed",
                    "output": personalization_path,
                }
            else:
                result["personalization"] = {"status": "skipped"}

        except Exception as e:
            result["personalization"] = {
                "status": "failed",
                "error": str(e),
            }

        # ------------------------------------------------------
        # 5) LOCALIZATION (Phase 4.5)
        # ------------------------------------------------------
        try:
            if localization_fn:
                localization_fn(
                    rows=rows,
                    batch_summary=batch_summary,
                    personalization_result=result.get("personalization"),
                    tips_result=result.get("tips"),
                    output_path=localization_path,
                    run_id=ctx.run_id,
                    report_date=ctx.report_date,
                    **localization_kwargs,
                )
                result["localization"] = {
                    "status": "completed",
                    "output": localization_path,
                }
            else:
                result["localization"] = {"status": "skipped"}

        except Exception as e:
            result["localization"] = {
                "status": "failed",
                "error": str(e),
            }

        # ------------------------------------------------------
        # 6) SONG RECOMMENDATION (Phase 5)
        # ------------------------------------------------------
        try:
            if song_recommendation_fn:
                song_recommendation_fn(                   
                    rows=rows,
                    output_path=song_rec_path,
                    run_id=ctx.run_id,
                    report_date=ctx.report_date,
                    **song_recommendation_kwargs,
                )

                result["song_recommendation"] = {
                    "status": "completed",
                    "output": song_rec_path,
                }
            else:
                result["song_recommendation"] = {"status": "skipped"}

        except Exception as e:
            result["song_recommendation"] = {
                "status": "failed",
                "error": str(e),
            }

        # ------------------------------------------------------
        # 7) GAME RECOMMENDATION (Phase 7)
        # ------------------------------------------------------
        try:
            if recommendation_fn:
                recommendation_fn(
                    rows=rows,
                    output_path=rec_path,
                    run_id=ctx.run_id,
                    report_date=ctx.report_date,
                    **recommendation_kwargs,
                )

                result["recommendation"] = {
                    "status": "completed",
                    "output": rec_path,
                }
            else:
                result["recommendation"] = {"status": "skipped"}

        except Exception as e:
            result["recommendation"] = {
                "status": "failed",
                "error": str(e),
            }

        # ------------------------------------------------------
        # 8) INTEGRITY CHECK
        # ------------------------------------------------------
        try:
            from rhythm_ingestion.utils import paired_integrity

            if hasattr(paired_integrity, "run_integrity_check"):
                integrity_result = paired_integrity.run_integrity_check(
                    scan_result=result.get("scan"),
                    ingestion_rows=len(rows),
                    tips_result=result.get("tips"),
                    song_recommendation_result=result.get("song_recommendation"),
                    recommendation_result=result.get("recommendation"),
                )

                result["integrity_check"] = {
                    "status": "completed",
                    "details": integrity_result,
                }

                if not integrity_result.get("passed", False):
                    result["status"] = "failed"

            else:
                result["integrity_check"] = {
                    "status": "skipped",
                    "reason": "run_integrity_check not implemented",
                }

        except Exception as e:
            result["integrity_check"] = {
                "status": "failed",
                "error": str(e),
            }
            result["status"] = "failed"

        # ------------------------------------------------------
        # FINAL SUMMARY LOG
        # ------------------------------------------------------
        try:
            from rhythm_ingestion.utils import log

            log("\n================ PIPELINE SUMMARY ================")
            log(f"Run ID: {ctx.run_id}")
            log(f"Status: {result.get('status')}")
            log(f"Artifacts: {ctx.artifacts_dir}")
            log("-------------------------------------------------")

            for stage in [
                "scan",
                "ingestion",
                "tips",
                "personalization",
                "localization",
                "song_recommendation",
                "recommendation",
                "integrity_check",
            ]:
                info = result.get(stage) or {}
                stage_status = info.get("status")

                line = f"{stage:20s} : {stage_status}"

                # attach key signals
                if stage == "scan":
                    line += f" | output={info.get('output')}"
                    if stage_status == "reused":
                        line += " | mode=reused_snapshot"

                if stage == "ingestion":
                    line += f" | rows={info.get('rows')}"
                    if info.get("scan_state_path"):
                        line += f" | scan_state={info.get('scan_state_path')}"
                    if info.get("scan_mode"):
                        line += f" | scan_mode={info.get('scan_mode')}"

                if stage == "integrity_check":
                    details = info.get("details") or {}
                    line += f" | passed={details.get('passed')}"

                log(line)

            log("=================================================\n")

        except Exception:
            pass


        # ------------------------------------------------------
        # FINALIZE
        # ------------------------------------------------------
        if result.get("status") != "failed":
            result["status"] = "completed"

        finalize_extra = dict(result)
        finalize_extra.update(
            {
                "source_dir": source_dir,
                "scan_state_path": scan_state_for_ingest,
            }
        )

        self.finalize_run(
            status=result["status"],
            extra=finalize_extra,
        )

        return result
