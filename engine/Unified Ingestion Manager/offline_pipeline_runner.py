from rhythm_ingestion.runtime_meta import RuntimeMetaManager
from rhythm_ingestion.orchestrator import ingest

from rhythm_ingestion.runtime_meta import (
    run_file_scan_wrapper,
    run_tips_wrapper,
    run_personalization_wrapper,
    run_localization_wrapper,
    run_song_recommendation_wrapper,
    run_recommendation_wrapper,
)


def run_pipeline(source_dir: str):
    runtime_meta = RuntimeMetaManager()

    
    result = runtime_meta.run_full_pipeline(
        source_dir=source_dir,
        ingest_fn=ingest,
        scan_fn=run_file_scan_wrapper,
        tips_fn=run_tips_wrapper,
        personalization_fn=run_personalization_wrapper,
        localization_fn=run_localization_wrapper,
        song_recommendation_fn=run_song_recommendation_wrapper,
        recommendation_fn=run_recommendation_wrapper,
        ingest_kwargs={
            "tips_mode": "production",
        },
    )


    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--source_dir", required=True)

    args = parser.parse_args()

    result = run_pipeline(args.source_dir)

    print("Pipeline completed:")
    print(result)