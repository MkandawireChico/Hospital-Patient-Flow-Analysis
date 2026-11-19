from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from patient_flow.analysis import export_analysis_artifacts
from patient_flow.analysis import load_processed_data as load_analysis_data
from patient_flow.cleaning import build_clean_dataset
from patient_flow.io import PROCESSED_DATA_PATH, load_raw_data, save_processed_data
from patient_flow.simulation import generate_and_save_raw_dataset


def run_pipeline(regenerate_raw: bool = True) -> dict[str, float | int | str]:
    """Generate (or reuse) raw data, clean it, and export analysis artifacts."""
    if regenerate_raw:
        raw, raw_path = generate_and_save_raw_dataset()
    else:
        raw = load_raw_data()
        raw_path = None

    cleaned = build_clean_dataset(raw)
    processed_path = save_processed_data(cleaned)
    export_analysis_artifacts(cleaned)
    valid_wait = pd.to_numeric(cleaned["Total_Waiting_Time_Valid"], errors="coerce").dropna()
    return {
        "raw_rows": int(len(raw)),
        "processed_rows": int(len(cleaned)),
        "mean_wait_minutes": float(valid_wait.mean()),
        "raw_path": str(raw_path) if raw_path else "existing raw CSV",
        "processed_path": str(processed_path),
    }


def analyse_pipeline() -> dict[str, Path]:
    """Generate baseline, scenario, and report artifacts from processed data."""
    df = load_analysis_data(str(PROCESSED_DATA_PATH))
    return export_analysis_artifacts(df)


def main() -> None:
    parser = argparse.ArgumentParser(description="Patient flow CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run",
        help="Regenerate raw encounters from config, clean data, and export analysis outputs",
    )
    run_parser.add_argument(
        "--use-existing-raw",
        action="store_true",
        help="Skip simulation and rebuild outputs from the committed raw CSV",
    )
    run_parser.set_defaults(handler=lambda args: print(run_pipeline(regenerate_raw=not args.use_existing_raw)))

    analyse_parser = subparsers.add_parser(
        "analyse", help="Generate baseline, scenario and decision-summary outputs from processed data"
    )
    analyse_parser.set_defaults(handler=lambda _args: print(analyse_pipeline()))

    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
