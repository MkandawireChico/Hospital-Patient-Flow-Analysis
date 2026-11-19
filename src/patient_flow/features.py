from __future__ import annotations

import pandas as pd

from patient_flow.flags import boolean_flag_column


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Generate temporal features used in patient-flow audit and scenario analysis."""
    output = df.copy()

    if "Arrival_Time" in output.columns:
        output["Arrival_Hour"] = pd.to_datetime(output["Arrival_Time"], errors="coerce").dt.hour
    else:
        output["Arrival_Hour"] = pd.NA

    if "Arrival_Hour" in output.columns:
        output["Peak_Period"] = output["Arrival_Hour"].apply(
            lambda hour: "Peak" if pd.notna(hour) and 8 <= int(hour) <= 9 else "Non-Peak"
        )
    else:
        output["Peak_Period"] = "Non-Peak"

    if "Visit_Date" in output.columns:
        output["Year_Month"] = pd.to_datetime(output["Visit_Date"], errors="coerce").dt.strftime("%Y-%m")
    else:
        output["Year_Month"] = pd.NA

    return output


def add_wait_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Flag long waits and invalid results that should be excluded from KPI summaries."""
    output = df.copy()

    invalid_mask = boolean_flag_column(output, "Negative_Wait_Flag")
    invalid_mask |= boolean_flag_column(output, "Impossible_Timestamp_Flag")

    if "Total_Waiting_Time_Valid" in output.columns:
        output["Total_Waiting_Time_Valid"] = pd.to_numeric(output["Total_Waiting_Time_Valid"], errors="coerce")
        output["Total_Waiting_Time_Valid"] = output["Total_Waiting_Time_Valid"].where(~invalid_mask, pd.NA)
        output["Long_Wait_Flag"] = output["Total_Waiting_Time_Valid"].gt(60)
    elif "Total_Waiting_Time" in output.columns:
        wait = pd.to_numeric(output["Total_Waiting_Time"], errors="coerce")
        output["Total_Waiting_Time_Valid"] = wait.where(~invalid_mask, pd.NA)
        output["Long_Wait_Flag"] = output["Total_Waiting_Time_Valid"].gt(60)
    else:
        output["Long_Wait_Flag"] = False

    return output


def add_bottleneck_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Add queue-pressure flags for bottleneck and congestion analysis."""
    output = df.copy()

    if "Queue_Size" in output.columns:
        q75 = output["Queue_Size"].quantile(0.75)
        output["High_Congestion_Flag"] = output["Queue_Size"].fillna(0) >= q75
    else:
        output["High_Congestion_Flag"] = False

    if "Long_Wait_Flag" not in output.columns:
        output["Long_Wait_Flag"] = False

    return output


def add_feature_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Compatibility wrapper for earlier project versions that expected a single flag builder."""
    output = df.copy()
    output = add_temporal_features(output)
    output = add_wait_quality_flags(output)
    output = add_bottleneck_flags(output)
    return output


def build_feature_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Construct the feature table used for baseline analysis and scenario planning."""
    output = df.copy()
    output = add_temporal_features(output)
    output = add_wait_quality_flags(output)
    output = add_bottleneck_flags(output)
    return output
