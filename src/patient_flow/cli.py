from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from patient_flow.analysis import (
    department_wait_summary,
    export_analysis_artifacts,
)
from patient_flow.analysis import (
    load_processed_data as load_analysis_data,
)
from patient_flow.cleaning import build_clean_dataset
from patient_flow.io import (
    PROCESSED_DATA_PATH,
    load_processed_data,
    load_raw_data,
    save_processed_data,
)


def run_pipeline() -> dict[str, float | int]:
    """Run cleaning, baseline analysis, scenarios, and report generation end to end."""
    raw = load_raw_data()
    cleaned = build_clean_dataset(raw)
    save_processed_data(cleaned)
    export_analysis_artifacts(cleaned)
    metrics = {
        "rows": int(len(cleaned)),
        "mean_wait_minutes": float(cleaned["Total_Waiting_Time_Valid"].mean()),
    }
    return metrics


def analyse_pipeline() -> pd.DataFrame:
    """Generate a summary table for department-level waiting time analysis."""
    df = load_processed_data()
    return department_wait_summary(df)


def export_analysis_pipeline() -> dict[str, Path]:
    """Generate baseline, scenario, and report artifacts from the processed dataset."""
    df = load_analysis_data(str(PROCESSED_DATA_PATH))
    return export_analysis_artifacts(df)


def main() -> None:
    parser = argparse.ArgumentParser(description="Patient flow CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Rebuild the processed dataset and analysis outputs from the committed raw CSV")
    run_parser.set_defaults(handler=lambda: print(run_pipeline()))

    analyse_parser = subparsers.add_parser(
        "analyse", help="Generate department-level waiting summaries"
    )
    analyse_parser.set_defaults(handler=lambda: print(export_analysis_pipeline()))

    args = parser.parse_args()
    args.handler()


if __name__ == "__main__":
    main()
