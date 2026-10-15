from __future__ import annotations

import pandas as pd

from patient_flow.analysis import (
    build_baseline_summary,
    filter_analysis_frame,
    summarise_waits_by_stage,
)
from patient_flow.cleaning import (
    build_clean_dataset,
    drop_duplicate_rows,
    ensure_non_negative_waits,
    flag_impossible_timestamps,
)
from patient_flow.features import build_feature_dataset
from patient_flow.io import load_processed_data, load_raw_data
from patient_flow.scenarios import build_scenario_comparison


def test_golden_master_regression():
    df = load_processed_data()
    assert len(df) == 35082
    wait_mean = float(df["Total_Waiting_Time_Valid"].mean())
    assert abs(wait_mean - 13.75) < 0.05


def test_issue_flags_are_detected():
    df = load_processed_data()
    assert "Department_Data_Error" in df.columns
    assert "Impossible_Timestamp_Flag" in df.columns
    assert "Negative_Wait_Flag" in df.columns
    assert "LOS_Outlier_Flag" in df.columns
    assert df["Department_Data_Error"].any()
    assert df["Impossible_Timestamp_Flag"].any()
    assert df["Negative_Wait_Flag"].any()
    assert df["LOS_Outlier_Flag"].any()


def test_duplicates_are_dropped():
    base = pd.DataFrame(
        {"Patient_ID": ["A", "A", "B"], "Total_Waiting_Time_Valid": [1.0, 1.0, 5.0]}
    )
    cleaned = drop_duplicate_rows(base)
    assert len(cleaned) == 2
    assert cleaned["Patient_ID"].tolist() == ["A", "B"]


def test_impossible_timestamps_are_flagged():
    df = pd.DataFrame(
        {
            "Arrival_Time": ["2025-01-01 08:00:00", "2025-01-01 08:00:00"],
            "Consultation_Start_Time": ["2025-01-01 07:55:00", "2025-01-01 08:10:00"],
        }
    )
    flagged = flag_impossible_timestamps(df)
    assert flagged["Impossible_Timestamp_Flag"].tolist() == [True, False]


def test_wait_time_columns_are_non_negative_after_cleaning():
    df = pd.DataFrame(
        {
            "Wait_For_Registration_Min": [0.0, 3.5, -1.0],
            "Wait_For_Triage_Min": [4.0, -2.0, 0.0],
            "Wait_For_Consultation_Min": [1.0, 0.0, 2.0],
            "Total_Waiting_Time_Valid": [5.0, 1.5, -1.0],
        }
    )
    cleaned = ensure_non_negative_waits(df)
    assert (
        (
            cleaned[
                [
                    "Wait_For_Registration_Min",
                    "Wait_For_Triage_Min",
                    "Wait_For_Consultation_Min",
                    "Total_Waiting_Time_Valid",
                ]
            ]
            >= 0
        )
        .all()
        .all()
    )


def test_cleaning_pipeline_matches_repository_contract():
    raw = load_raw_data().copy()
    cleaned = build_clean_dataset(raw)

    required = {
        "Department_Data_Error",
        "Impossible_Timestamp_Flag",
        "Negative_Wait_Flag",
        "Total_Waiting_Time_Valid",
        "LOS_Outlier_Flag",
        "Arrival_Hour",
        "Peak_Period",
        "Long_Wait_Flag",
        "High_Congestion_Flag",
        "Year_Month",
    }

    missing = required - set(cleaned.columns)
    assert not missing
    assert len(cleaned) == 35082
    assert cleaned["Total_Waiting_Time_Valid"].notna().sum() >= 1


def test_feature_pipeline_adds_temporal_and_bottleneck_flags():
    df = load_processed_data().head(100).copy()
    features = build_feature_dataset(df)

    assert "Arrival_Hour" in features.columns
    assert "Peak_Period" in features.columns
    assert "Long_Wait_Flag" in features.columns
    assert "High_Congestion_Flag" in features.columns
    assert set(features["Peak_Period"].unique()).issubset({"Peak", "Non-Peak"})


def test_baseline_analysis_runs_on_processed_data():
    df = load_processed_data()
    summary = build_baseline_summary(df)
    assert summary["overall"]["patient_count"] > 0
    assert summary["audit"]["excluded_invalid_timing_rows"] > 0
    assert not summarise_waits_by_stage(df).empty


def test_analysis_subset_excludes_invalid_rows_and_negative_waits():
    df = pd.DataFrame(
        {
            "Total_Waiting_Time_Valid": [4.0, 5.0, 6.0],
            "Wait_For_Consultation_Min": [3.0, -1.0, 2.0],
            "Impossible_Timestamp_Flag": [False, False, True],
            "Negative_Wait_Flag": [False, False, False],
        }
    )
    filtered = filter_analysis_frame(df)
    assert len(filtered) == 1
    numeric_waits = filtered.select_dtypes(include="number")
    assert not numeric_waits.lt(0).any().any()
    assert filtered.attrs["analysis_audit"]["excluded_invalid_timing_rows"] == 2


def test_scenario_comparison_has_three_comparable_scenarios():
    df = load_processed_data()
    comparison = build_scenario_comparison(df)
    assert len(comparison) == 3
    assert comparison["scenario"].tolist() == [
        "Baseline",
        "Consultation wait reduction",
        "Peak priority fast-track",
    ]
    assert {
        "median_total_valid_wait_minutes",
        "p90_total_valid_wait_minutes",
        "long_wait_pct",
        "urgent_median_wait_minutes",
    }.issubset(comparison.columns)


def test_analysis_export_populates_readme_from_generated_results(tmp_path):
    from patient_flow.analysis import export_analysis_artifacts

    readme = tmp_path / "README.md"
    readme.write_text(
        "<!-- BEGIN GENERATED FINDINGS -->\nplaceholder\n<!-- END GENERATED FINDINGS -->\n"
        "<!-- BEGIN GENERATED DATA COUNTS -->\nplaceholder\n<!-- END GENERATED DATA COUNTS -->",
        encoding="utf-8",
    )
    raw_path = tmp_path / "data" / "raw" / "hospital_patient_flow_synthetic.csv"
    raw_path.parent.mkdir(parents=True)
    pd.DataFrame({"Patient_ID": ["A", "B"]}).to_csv(raw_path, index=False)

    outputs = export_analysis_artifacts(load_processed_data(), project_root=tmp_path)
    generated = readme.read_text(encoding="utf-8")

    assert "34,728 of 35,082 processed rows" in generated
    assert "Laboratory has a p90 of 182.9 min" in generated
    assert "Consultation wait reduction" in generated
    assert "Raw synthetic source: **2 rows**" in generated
    assert outputs["dataset_overview"].exists()
