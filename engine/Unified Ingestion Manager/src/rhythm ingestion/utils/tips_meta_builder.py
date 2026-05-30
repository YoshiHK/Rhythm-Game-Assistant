from datetime import date
from pathlib import Path
import json

from utils.qa_reporter import QASummary
from utils.paired_integrity import stamp_integrity
from utils.file_scan import allocate_run_id, utc_now_iso


def build_tips_meta(
    qa: QASummary,
    *,
    base_dir: Path
):
        
    report_date = date.today().isoformat()
    run_id, seq = allocate_run_id(base_dir, report_date)

    payload = {
        "report_type": "tips_meta",
        "report_date": report_date,
        "report_seq": seq,
        "run_id": run_id,
        "generated_at": utc_now_iso(),
        "total_charts": qa.total_charts,
        "total_success": qa.total_success,
        "total_failed": qa.total_failed,
        "by_game": qa.by_game,
        "failures": qa.failures,
        "metadata_stats": qa.metadata_stats,
        "sections_by_game": {},
    }

    stamp_integrity(payload)
    return payload


def save_tips_meta(payload: dict, base_dir: Path):
    path = base_dir / f"tips_meta_{payload['run_id']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return path