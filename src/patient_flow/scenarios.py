from __future__ import annotations

from typing import Any

import pandas as pd

from patient_flow.analysis import _wait_column, filter_analysis_frame, summarise_waits_by_department

CONSULTATION_REDUCTION_PCT = 20.0
PEAK_PRIORITY_REDUCTION_PCT = 20.0
SCENARIO_LABELS = ["Baseline", "Consultation wait reduction", "Peak priority fast-track"]


def _priority_mask(df: pd.DataFrame, values: set[str]) -> pd.Series:
    if "Priority_Level" not in df.columns:
        return pd.Series(False, index=df.index)
    return df["Priority_Level"].astype("string").str.strip().str.casefold().isin(values)


def _peak_mask(df: pd.DataFrame) -> pd.Series:
    if "Peak_Period" in df.columns:
        return df["Peak_Period"].astype("string").str.strip().str.casefold().eq("peak")
    if "Arrival_Hour" in df.columns:
        hour = pd.to_numeric(df["Arrival_Hour"], errors="coerce")
    elif "Arrival_Time" in df.columns:
        hour = pd.to_datetime(df["Arrival_Time"], errors="coerce").dt.hour
    else:
        return pd.Series(False, index=df.index)
    return hour.between(8, 9, inclusive="both")


def _apply_consultation_reduction(
    df: pd.DataFrame, mask: pd.Series, reduction_pct: float
) -> pd.DataFrame:
    output = df.copy()
    if "Wait_For_Consultation_Min" not in output.columns:
        return output
    wait_column = _wait_column(output)
    stage_wait = pd.to_numeric(output["Wait_For_Consultation_Min"], errors="coerce")
    reduction = stage_wait.where(mask, 0).clip(lower=0) * reduction_pct / 100
    output["Wait_For_Consultation_Min"] = (stage_wait - reduction).clip(lower=0)
    total_wait = pd.to_numeric(output[wait_column], errors="coerce")
    output[wait_column] = (total_wait - reduction).clip(lower=0)
    output["Long_Wait_Flag"] = output[wait_column].gt(60)
    return output


def apply_consultation_wait_scenario(df: pd.DataFrame) -> pd.DataFrame:
    """Reduce consultation waits by 20% for Routine records only; other waits are unchanged."""
    analysis = filter_analysis_frame(df)
    routine = _priority_mask(analysis, {"routine"})
    return _apply_consultation_reduction(analysis, routine, CONSULTATION_REDUCTION_PCT)


def apply_peak_priority_scenario(df: pd.DataFrame) -> pd.DataFrame:
    """Reduce consultation waits by 20% for Urgent/Emergency records during Peak hours."""
    analysis = filter_analysis_frame(df)
    protected_priority = _priority_mask(analysis, {"urgent", "emergency"})
    return _apply_consultation_reduction(
        analysis,
        protected_priority & _peak_mask(analysis),
        PEAK_PRIORITY_REDUCTION_PCT,
    )


def _scenario_kpis(
    df: pd.DataFrame, label: str, consultation_pct: float, peak_priority_pct: float
) -> dict[str, Any]:
    analysis = filter_analysis_frame(df)
    wait_column = _wait_column(analysis)
    waits = pd.to_numeric(analysis[wait_column], errors="coerce").dropna()
    priority = (
        analysis.get("Priority_Level", pd.Series(pd.NA, index=analysis.index))
        .astype("string")
        .str.strip()
        .str.casefold()
    )
    urgent_mask = priority.isin({"urgent", "emergency"})
    urgent_waits = pd.to_numeric(analysis.loc[urgent_mask, wait_column], errors="coerce").dropna()
    return {
        "scenario": label,
        "patient_count": int(len(analysis)),
        "wait_count": int(waits.count()),
        "median_total_valid_wait_minutes": float(waits.median())
        if not waits.empty
        else float("nan"),
        "p90_total_valid_wait_minutes": float(waits.quantile(0.9))
        if not waits.empty
        else float("nan"),
        "long_wait_pct": float(waits.gt(60).mean() * 100) if not waits.empty else float("nan"),
        "urgent_median_wait_minutes": float(urgent_waits.median())
        if not urgent_waits.empty
        else float("nan"),
        "long_wait_threshold_minutes": 60.0,
        "consultation_reduction_pct": consultation_pct,
        "peak_priority_reduction_pct": peak_priority_pct,
    }


def build_scenario_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Compare exactly three scenarios against a shared cleaned-data cohort."""
    baseline = filter_analysis_frame(df)
    consultation = apply_consultation_wait_scenario(baseline)
    peak_priority = apply_peak_priority_scenario(baseline)
    rows = [
        _scenario_kpis(baseline, SCENARIO_LABELS[0], 0.0, 0.0),
        _scenario_kpis(consultation, SCENARIO_LABELS[1], CONSULTATION_REDUCTION_PCT, 0.0),
        _scenario_kpis(peak_priority, SCENARIO_LABELS[2], 0.0, PEAK_PRIORITY_REDUCTION_PCT),
    ]
    comparison = pd.DataFrame(rows)
    baseline_row = comparison.iloc[0]
    comparison["median_wait_change_vs_baseline_minutes"] = (
        comparison["median_total_valid_wait_minutes"]
        - baseline_row["median_total_valid_wait_minutes"]
    )
    comparison["p90_wait_change_vs_baseline_minutes"] = (
        comparison["p90_total_valid_wait_minutes"] - baseline_row["p90_total_valid_wait_minutes"]
    )
    comparison["long_wait_change_vs_baseline_pp"] = (
        comparison["long_wait_pct"] - baseline_row["long_wait_pct"]
    )
    return comparison


def build_scenario_department_effects(df: pd.DataFrame) -> pd.DataFrame:
    """Return department-level median wait changes for both what-if scenarios."""
    baseline = filter_analysis_frame(df)
    baseline_summary = summarise_waits_by_department(baseline).rename(
        columns={"median_wait_minutes": "baseline_median_wait_minutes"}
    )[["department", "patient_count", "baseline_median_wait_minutes"]]
    scenario_frames = [
        (SCENARIO_LABELS[1], apply_consultation_wait_scenario(baseline)),
        (SCENARIO_LABELS[2], apply_peak_priority_scenario(baseline)),
    ]
    rows: list[dict[str, Any]] = []
    for label, scenario_df in scenario_frames:
        scenario_summary = summarise_waits_by_department(scenario_df).rename(
            columns={"median_wait_minutes": "scenario_median_wait_minutes"}
        )[["department", "scenario_median_wait_minutes"]]
        merged = baseline_summary.merge(scenario_summary, on="department", how="left")
        merged["scenario"] = label
        merged["median_wait_change_minutes"] = (
            merged["scenario_median_wait_minutes"] - merged["baseline_median_wait_minutes"]
        )
        baseline_median = merged["baseline_median_wait_minutes"].replace(0, pd.NA)
        merged["median_wait_change_pct"] = (
            merged["median_wait_change_minutes"] / baseline_median * 100
        )
        rows.extend(merged.to_dict(orient="records"))
    return pd.DataFrame(rows)[
        [
            "scenario",
            "department",
            "patient_count",
            "baseline_median_wait_minutes",
            "scenario_median_wait_minutes",
            "median_wait_change_minutes",
            "median_wait_change_pct",
        ]
    ]
