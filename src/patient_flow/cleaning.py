from __future__ import annotations

from typing import Iterable

import pandas as pd

DEFAULT_NEGATIVE_WAIT_COLUMNS = [
    "Wait_For_Registration_Min",
    "Wait_For_Triage_Min",
    "Wait_For_Consultation_Min",
    "Total_Waiting_Time",
]

CANONICAL_DEPARTMENTS = {
    "Outpatient Department",
    "Emergency",
    "Maternal Health",
    "Paediatrics",
    "Chronic Care",
    "TB/HIV Clinic",
}

DEPARTMENT_FIXES = {
    "OPD": "Outpatient Department",
    "OPD ": "Outpatient Department",
    "outpatient department": "Outpatient Department",
    "Outpatient department": "Outpatient Department",
    "emergency": "Emergency",
    "PAEDS": "Paediatrics",
    "Maternity": "Maternal Health",
    "Maternal": "Maternal Health",
}


def drop_duplicate_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Drop exact duplicate rows while preserving the original record order."""
    return df.drop_duplicates().reset_index(drop=True)


def standardise_departments(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise department names and flag values that fall outside the expected list."""
    output = df.copy()
    if "Department" not in output.columns:
        output["Department_Data_Error"] = False
        return output

    output["Department"] = output["Department"].astype("string").str.strip()
    output["Department"] = output["Department"].replace(DEPARTMENT_FIXES)
    output["Department_Data_Error"] = ~output["Department"].isin(CANONICAL_DEPARTMENTS)
    return output


def flag_impossible_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Flag visit stages that begin before the patient arrives or end before they start."""
    output = df.copy()
    timestamp_cols = [
        "Arrival_Time",
        "Registration_Start_Time",
        "Registration_End_Time",
        "Triage_Start_Time",
        "Triage_End_Time",
        "Consultation_Start_Time",
        "Consultation_End_Time",
        "Final_Stage_End_Time",
    ]

    output["Impossible_Timestamp_Flag"] = False
    for start_name, end_name in [
        ("Arrival_Time", "Registration_Start_Time"),
        ("Arrival_Time", "Triage_Start_Time"),
        ("Arrival_Time", "Consultation_Start_Time"),
        ("Registration_Start_Time", "Registration_End_Time"),
        ("Triage_Start_Time", "Triage_End_Time"),
        ("Consultation_Start_Time", "Consultation_End_Time"),
    ]:
        if start_name in output.columns and end_name in output.columns:
            start = pd.to_datetime(output[start_name], errors="coerce")
            end = pd.to_datetime(output[end_name], errors="coerce")
            output["Impossible_Timestamp_Flag"] |= end < start

    if "Arrival_Time" in output.columns and "Consultation_Start_Time" in output.columns:
        arrival = pd.to_datetime(output["Arrival_Time"], errors="coerce")
        consultation = pd.to_datetime(output["Consultation_Start_Time"], errors="coerce")
        output["Impossible_Timestamp_Flag"] |= consultation < arrival

    # Final stage end times must also be after the last recorded clinical step.
    if "Consultation_End_Time" in output.columns and "Final_Stage_End_Time" in output.columns:
        consultation_end = pd.to_datetime(output["Consultation_End_Time"], errors="coerce")
        final_end = pd.to_datetime(output["Final_Stage_End_Time"], errors="coerce")
        output["Impossible_Timestamp_Flag"] |= final_end < consultation_end

    return output


def ensure_non_negative_waits(
    df: pd.DataFrame,
    columns: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Clip negative wait values to zero and flag rows that originally violated the rule."""
    output = df.copy()
    wait_columns = list(columns) if columns is not None else DEFAULT_NEGATIVE_WAIT_COLUMNS
    negative_wait_mask = pd.Series(False, index=output.index)

    for col in wait_columns:
        if col not in output.columns:
            continue
        values = pd.to_numeric(output[col], errors="coerce")
        negative_wait_mask |= values.lt(0)
        output[col] = values.clip(lower=0)

    if "Total_Waiting_Time_Valid" in output.columns:
        valid = pd.to_numeric(output["Total_Waiting_Time_Valid"], errors="coerce")
        negative_wait_mask |= valid.lt(0)
        output["Total_Waiting_Time_Valid"] = valid.clip(lower=0)

    output["Negative_Wait_Flag"] = negative_wait_mask.fillna(False).astype(bool)
    return output


def compute_valid_waits(df: pd.DataFrame) -> pd.DataFrame:
    """Create the valid wait metric used in downstream KPI calculations."""
    output = df.copy()
    if "Total_Waiting_Time" not in output.columns:
        output["Total_Waiting_Time_Valid"] = pd.Series(pd.NA, index=output.index)
        return output

    valid_wait = pd.to_numeric(output["Total_Waiting_Time"], errors="coerce")
    invalid_mask = output.get("Negative_Wait_Flag", pd.Series(False, index=output.index))
    invalid_mask = invalid_mask.fillna(False).astype(bool)
    invalid_mask |= output.get("Impossible_Timestamp_Flag", pd.Series(False, index=output.index)).fillna(False).astype(bool)
    output["Total_Waiting_Time_Valid"] = valid_wait.where(~invalid_mask, pd.NA)
    return output


def add_sync_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add the repository's temporal and congestion signals used in the analysis."""
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

    if "Total_Waiting_Time_Valid" in output.columns:
        output["Long_Wait_Flag"] = pd.to_numeric(output["Total_Waiting_Time_Valid"], errors="coerce") > 60
    else:
        output["Long_Wait_Flag"] = False

    if "Queue_Size" in output.columns:
        q75 = output["Queue_Size"].quantile(0.75)
        output["High_Congestion_Flag"] = output["Queue_Size"].fillna(0) >= q75
    else:
        output["High_Congestion_Flag"] = False

    if "Visit_Date" in output.columns:
        output["Year_Month"] = pd.to_datetime(output["Visit_Date"], errors="coerce").dt.strftime("%Y-%m")
    else:
        output["Year_Month"] = pd.NA

    return output


def flag_los_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """Flag extreme length-of-stay values based on the interquartile range rule."""
    output = df.copy()
    if "Total_Length_of_Stay" not in output.columns:
        output["LOS_Outlier_Flag"] = False
        return output

    los = pd.to_numeric(output["Total_Length_of_Stay"], errors="coerce")
    q1 = los.quantile(0.25)
    q3 = los.quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    output["LOS_Outlier_Flag"] = los.lt(lower) | los.gt(upper)
    return output


def build_clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the repository's standard preparation workflow to the raw hospital-flow file."""
    cleaned = drop_duplicate_rows(df)
    cleaned = standardise_departments(cleaned)
    cleaned = flag_impossible_timestamps(cleaned)
    cleaned = ensure_non_negative_waits(cleaned)
    cleaned = compute_valid_waits(cleaned)
    cleaned = flag_los_outliers(cleaned)
    cleaned = add_sync_features(cleaned)
    return cleaned


def detect_data_quality_issues(df: pd.DataFrame) -> dict[str, int]:
    """Return the issue counts used in the project audit summary."""
    issues = {
        "duplicate_rows": int(df.duplicated().sum()),
        "impossible_timestamps": int(df.get("Impossible_Timestamp_Flag", pd.Series(False, index=df.index)).fillna(False).astype(bool).sum()),
        "negative_waits": int(df.get("Negative_Wait_Flag", pd.Series(False, index=df.index)).fillna(False).astype(bool).sum()),
        "department_errors": int(df.get("Department_Data_Error", pd.Series(False, index=df.index)).fillna(False).astype(bool).sum()),
        "los_outliers": int(df.get("LOS_Outlier_Flag", pd.Series(False, index=df.index)).fillna(False).astype(bool).sum()),
    }
    return issues
