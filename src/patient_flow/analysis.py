from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from patient_flow.flags import boolean_flag_column

LONG_WAIT_THRESHOLD_MINUTES = 60.0
STAGE_WAIT_COLUMNS = {
    "Registration": "Wait_For_Registration_Min",
    "Triage": "Wait_For_Triage_Min",
    "Consultation": "Wait_For_Consultation_Min",
    "Laboratory": "Laboratory_Wait_Time",
    "Pharmacy": "Pharmacy_Wait_Time",
}
WAIT_COLUMNS = [*STAGE_WAIT_COLUMNS.values(), "Total_Waiting_Time", "Total_Waiting_Time_Valid"]


def load_processed_data(path: str) -> pd.DataFrame:
    """Load a processed synthetic patient-flow CSV from an explicit path."""
    return pd.read_csv(Path(path))


def _boolean_column(df: pd.DataFrame, column: str) -> pd.Series:
    """Compatibility wrapper for the shared CSV-safe boolean parser."""
    return boolean_flag_column(df, column)


def _wait_column(df: pd.DataFrame) -> str:
    if "Total_Waiting_Time_Valid" in df.columns:
        return "Total_Waiting_Time_Valid"
    if "Total_Waiting_Time" in df.columns:
        return "Total_Waiting_Time"
    raise KeyError("Total_Waiting_Time_Valid or Total_Waiting_Time column is required")


def filter_analysis_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Exclude flagged or negative-timing rows and attach an auditable exclusion summary.

    Rows with missing valid total wait remain available for volume and stage summaries;
    wait-specific metrics naturally omit missing observations.
    """
    output = df.copy()
    invalid_timing = _boolean_column(output, "Impossible_Timestamp_Flag")
    invalid_wait_flag = _boolean_column(output, "Negative_Wait_Flag")
    negative_values = pd.Series(False, index=output.index)
    for column in WAIT_COLUMNS:
        if column in output.columns:
            values = pd.to_numeric(output[column], errors="coerce")
            negative_values |= values.lt(0)

    exclude = invalid_timing | invalid_wait_flag | negative_values
    filtered = output.loc[~exclude].copy()
    wait_column = (
        _wait_column(filtered)
        if ("Total_Waiting_Time_Valid" in filtered or "Total_Waiting_Time" in filtered)
        else None
    )
    if wait_column is not None:
        filtered[wait_column] = pd.to_numeric(filtered[wait_column], errors="coerce")
    filtered.attrs["analysis_audit"] = {
        "input_rows": int(len(df)),
        "excluded_invalid_timing_rows": int(exclude.sum()),
        "analysis_rows": int(len(filtered)),
        "missing_total_wait_rows": int(
            pd.to_numeric(filtered[wait_column], errors="coerce").isna().sum()
        )
        if wait_column is not None
        else int(len(filtered)),
        "total_wait_column": wait_column or "unavailable",
    }
    return filtered


def _wait_metrics(values: pd.Series) -> dict[str, float | int]:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return {
            "wait_count": 0,
            "mean_wait_minutes": float("nan"),
            "median_wait_minutes": float("nan"),
            "p90_wait_minutes": float("nan"),
            "long_wait_pct": float("nan"),
        }
    return {
        "wait_count": int(numeric.count()),
        "mean_wait_minutes": float(numeric.mean()),
        "median_wait_minutes": float(numeric.median()),
        "p90_wait_minutes": float(numeric.quantile(0.9)),
        "long_wait_pct": float(numeric.gt(LONG_WAIT_THRESHOLD_MINUTES).mean() * 100),
    }


def summarise_overall_waits(df: pd.DataFrame) -> pd.DataFrame:
    """Return overall wait and length-of-stay KPIs as a one-row tidy table."""
    analysis = filter_analysis_frame(df)
    wait_metrics = _wait_metrics(analysis[_wait_column(analysis)])
    los = pd.to_numeric(
        analysis.get("Total_Length_of_Stay", pd.Series(dtype=float)), errors="coerce"
    ).dropna()
    row: dict[str, Any] = {
        "patient_count": int(len(analysis)),
        **wait_metrics,
        "median_los_minutes": float(los.median()) if not los.empty else float("nan"),
        "p90_los_minutes": float(los.quantile(0.9)) if not los.empty else float("nan"),
        "long_wait_threshold_minutes": LONG_WAIT_THRESHOLD_MINUTES,
    }
    return pd.DataFrame([row])


def summarise_waits_by_stage(df: pd.DataFrame) -> pd.DataFrame:
    """Summarise measured wait columns and their share of observed stage-wait minutes."""
    analysis = filter_analysis_frame(df)
    stage_rows: list[dict[str, Any]] = []
    for stage, column in STAGE_WAIT_COLUMNS.items():
        if column not in analysis.columns:
            continue
        values = pd.to_numeric(analysis[column], errors="coerce")
        stage_rows.append(
            {
                "stage": stage,
                **_wait_metrics(values),
                "stage_wait_total_minutes": float(values.sum()),
            }
        )

    result = pd.DataFrame(stage_rows)
    if result.empty:
        return result
    total_stage_wait = result["stage_wait_total_minutes"].sum()
    result["stage_contribution_pct"] = (
        result["stage_wait_total_minutes"] / total_stage_wait * 100
        if total_stage_wait > 0
        else float("nan")
    )
    return result.sort_values("p90_wait_minutes", ascending=False, na_position="last").reset_index(
        drop=True
    )


def _summarise_wait_by_group(df: pd.DataFrame, group_column: str, label: str) -> pd.DataFrame:
    analysis = filter_analysis_frame(df)
    if group_column not in analysis.columns:
        return pd.DataFrame(
            columns=[
                label,
                "patient_count",
                "wait_count",
                "mean_wait_minutes",
                "median_wait_minutes",
                "p90_wait_minutes",
                "long_wait_pct",
            ]
        )
    wait_column = _wait_column(analysis)
    rows: list[dict[str, Any]] = []
    for group, group_df in analysis.groupby(group_column, dropna=False, sort=True):
        metrics = _wait_metrics(group_df[wait_column])
        rows.append({label: group, "patient_count": int(len(group_df)), **metrics})
    return pd.DataFrame(rows)


def summarise_waits_by_department(df: pd.DataFrame) -> pd.DataFrame:
    """Return total-wait KPIs and volume by department."""
    return _summarise_wait_by_group(df, "Department", "department")


def summarise_arrivals_by_hour(df: pd.DataFrame) -> pd.DataFrame:
    """Return visit volume and total-wait KPIs by arrival hour."""
    analysis = filter_analysis_frame(df)
    if "Arrival_Hour" in analysis.columns:
        analysis["Arrival_Hour"] = pd.to_numeric(analysis["Arrival_Hour"], errors="coerce")
    elif "Arrival_Time" in analysis.columns:
        analysis["Arrival_Hour"] = pd.to_datetime(analysis["Arrival_Time"], errors="coerce").dt.hour
    else:
        return pd.DataFrame(
            columns=[
                "arrival_hour",
                "patient_count",
                "wait_count",
                "mean_wait_minutes",
                "median_wait_minutes",
                "p90_wait_minutes",
                "long_wait_pct",
            ]
        )
    wait_column = _wait_column(analysis)
    rows: list[dict[str, Any]] = []
    for hour, group_df in analysis.groupby("Arrival_Hour", dropna=False, sort=True):
        rows.append(
            {
                "arrival_hour": hour,
                "patient_count": int(len(group_df)),
                **_wait_metrics(group_df[wait_column]),
            }
        )
    return pd.DataFrame(rows)


def summarise_peak_vs_offpeak(df: pd.DataFrame) -> pd.DataFrame:
    """Compare total waits by the dataset's peak-period feature."""
    analysis = filter_analysis_frame(df)
    if "Peak_Period" not in analysis.columns:
        if "Arrival_Hour" in analysis.columns:
            hours = pd.to_numeric(analysis["Arrival_Hour"], errors="coerce")
        elif "Arrival_Time" in analysis.columns:
            hours = pd.to_datetime(analysis["Arrival_Time"], errors="coerce").dt.hour
        else:
            return pd.DataFrame(
                columns=[
                    "peak_period",
                    "patient_count",
                    "wait_count",
                    "mean_wait_minutes",
                    "median_wait_minutes",
                    "p90_wait_minutes",
                    "long_wait_pct",
                ]
            )
        analysis["Peak_Period"] = hours.apply(
            lambda hour: "Peak" if pd.notna(hour) and 8 <= hour <= 9 else "Non-Peak"
        )
    return _summarise_wait_by_group(analysis, "Peak_Period", "peak_period")


def summarise_priority_differences(df: pd.DataFrame) -> pd.DataFrame:
    """Compare total waits by recorded priority category."""
    return _summarise_wait_by_group(df, "Priority_Level", "priority_level")


def identify_top_bottlenecks(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Rank observed stages and departments by p90 wait, retaining volume context."""
    if n < 1:
        raise ValueError("n must be at least 1")
    analysis = filter_analysis_frame(df)
    rows: list[dict[str, Any]] = []
    stages = summarise_waits_by_stage(analysis)
    for row in stages.to_dict(orient="records"):
        rows.append(
            {
                "bottleneck_type": "stage",
                "bottleneck": row["stage"],
                "patient_count": row["wait_count"],
                "median_wait_minutes": row["median_wait_minutes"],
                "p90_wait_minutes": row["p90_wait_minutes"],
                "long_wait_pct": row["long_wait_pct"],
            }
        )
    departments = summarise_waits_by_department(analysis)
    for row in departments.to_dict(orient="records"):
        rows.append(
            {
                "bottleneck_type": "department",
                "bottleneck": row["department"],
                "patient_count": row["wait_count"],
                "median_wait_minutes": row["median_wait_minutes"],
                "p90_wait_minutes": row["p90_wait_minutes"],
                "long_wait_pct": row["long_wait_pct"],
            }
        )
    return (
        pd.DataFrame(rows)
        .sort_values("p90_wait_minutes", ascending=False, na_position="last")
        .head(n)
        .reset_index(drop=True)
    )


def build_baseline_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Build headline baseline KPIs and an explicit row-exclusion audit."""
    analysis = filter_analysis_frame(df)
    overall = summarise_overall_waits(analysis).iloc[0].to_dict()
    return {"overall": overall, "audit": analysis.attrs["analysis_audit"]}


def _format_minutes(value: Any) -> str:
    return "not available" if pd.isna(value) else f"{float(value):.1f} minutes"


def _replace_readme_block(text: str, start_marker: str, end_marker: str, content: str) -> str:
    start = text.index(start_marker) + len(start_marker)
    end = text.index(end_marker, start)
    return f"{text[:start]}\n{content}\n{text[end:]}"


def _update_readme_generated_sections(root: Path, outputs: dict[str, Path]) -> None:
    readme_path = root / "README.md"
    if not readme_path.exists():
        return

    overall = pd.read_csv(outputs["baseline_overall"]).iloc[0]
    stages = pd.read_csv(outputs["baseline_by_stage"])
    departments = pd.read_csv(outputs["baseline_by_department"])
    peak = pd.read_csv(outputs["baseline_peak_vs_offpeak"]).set_index("peak_period")
    priority = pd.read_csv(outputs["baseline_by_priority"]).set_index("priority_level")
    scenarios = pd.read_csv(outputs["scenario_comparison"]).set_index("scenario")
    dataset = pd.read_csv(outputs["dataset_overview"]).iloc[0]

    top_stage = stages.loc[stages["p90_wait_minutes"].idxmax()]
    top_department = departments.loc[departments["p90_wait_minutes"].idxmax()]
    candidates = scenarios.drop(index="Baseline")
    best = candidates.sort_values(
        ["p90_total_valid_wait_minutes", "long_wait_pct"], ascending=True
    ).iloc[0]
    baseline = scenarios.loc["Baseline"]
    peak_wait = peak.loc["Peak"]
    offpeak_wait = peak.loc["Non-Peak"]
    priority_text = ", ".join(
        f"{label}: p90 {priority.loc[label, 'p90_wait_minutes']:.1f} min"
        for label in ("Routine", "Urgent", "Emergency")
    )
    findings = "\n".join(
        [
            (
                f"- **Analysis cohort:** {int(overall['analysis_rows']):,} of "
                f"{int(overall['input_rows']):,} processed rows; "
                f"{int(overall['excluded_invalid_timing_rows']):,} rows were excluded "
                "for invalid timing or negative-wait evidence."
            ),
            (
                f"- **Overall valid wait:** median {overall['median_wait_minutes']:.1f} min, "
                f"mean {overall['mean_wait_minutes']:.1f} min, p90 "
                f"{overall['p90_wait_minutes']:.1f} min, and "
                f"{overall['long_wait_pct']:.1f}% above the "
                f"{overall['long_wait_threshold_minutes']:g}-minute long-wait threshold."
            ),
            (
                f"- **Largest stage-wait signal:** {top_stage['stage']} has a p90 of "
                f"{top_stage['p90_wait_minutes']:.1f} min and contributes "
                f"{top_stage['stage_contribution_pct']:.1f}% of summed observed "
                "stage-wait minutes. This share is not a decomposition of total wait."
            ),
            (
                f"- **Department signal:** {top_department['department']} has the highest "
                f"department p90 total wait at {top_department['p90_wait_minutes']:.1f} min."
            ),
            (
                f"- **Peak pattern:** median wait is {peak_wait['median_wait_minutes']:.1f} min "
                f"during Peak versus {offpeak_wait['median_wait_minutes']:.1f} min during "
                f"Non-Peak; p90 is {peak_wait['p90_wait_minutes']:.1f} versus "
                f"{offpeak_wait['p90_wait_minutes']:.1f} min. These are group comparisons, "
                "not evidence that the period label causes delay."
            ),
            f"- **Priority pattern:** {priority_text}.",
            (
                f"- **Strongest tested scenario:** {best.name} has p90 "
                f"{best['p90_total_valid_wait_minutes']:.1f} min versus baseline "
                f"{baseline['p90_total_valid_wait_minutes']:.1f} min "
                f"({abs(best['p90_wait_change_vs_baseline_minutes']):.1f} min lower) and "
                f"a {abs(best['long_wait_change_vs_baseline_pp']):.2f}-percentage-point "
                "lower long-wait share. Median wait remains "
                f"{baseline['median_total_valid_wait_minutes']:.1f} min across all scenarios, "
                "so the comparison is ranked on p90 and long-wait share rather than median alone."
            ),
        ]
    )
    data_counts = "\n".join(
        [
            f"- Raw synthetic source: **{int(dataset['raw_rows']):,} rows**.",
            f"- Processed dataset: **{int(dataset['processed_rows']):,} rows**.",
            f"- Valid analysis cohort: **{int(overall['analysis_rows']):,} rows**.",
        ]
    )

    readme = readme_path.read_text(encoding="utf-8")
    readme = _replace_readme_block(
        readme, "<!-- BEGIN GENERATED FINDINGS -->", "<!-- END GENERATED FINDINGS -->", findings
    )
    readme = _replace_readme_block(
        readme,
        "<!-- BEGIN GENERATED DATA COUNTS -->",
        "<!-- END GENERATED DATA COUNTS -->",
        data_counts,
    )
    readme_path.write_text(readme, encoding="utf-8")


def export_analysis_artifacts(df: pd.DataFrame, project_root: str | Path = ".") -> dict[str, Path]:
    """Write baseline/scenario CSVs and a data-generated decision summary report."""
    from patient_flow.scenarios import build_scenario_comparison, build_scenario_department_effects

    root = Path(project_root)
    results_dir = root / "results"
    reports_dir = root / "reports"
    results_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    baseline = build_baseline_summary(df)
    overall = pd.DataFrame(
        [
            {
                **baseline["overall"],
                **baseline["audit"],
                "synthetic_data": True,
            }
        ]
    )
    outputs = {
        "baseline_overall": results_dir / "baseline_overall.csv",
        "baseline_by_department": results_dir / "baseline_by_department.csv",
        "baseline_by_stage": results_dir / "baseline_by_stage.csv",
        "baseline_by_hour": results_dir / "baseline_by_hour.csv",
        "baseline_peak_vs_offpeak": results_dir / "baseline_peak_vs_offpeak.csv",
        "baseline_by_priority": results_dir / "baseline_by_priority.csv",
        "scenario_comparison": results_dir / "scenario_comparison.csv",
        "scenario_by_department": results_dir / "scenario_by_department.csv",
        "dataset_overview": results_dir / "dataset_overview.csv",
        "report": reports_dir / "baseline_decision_summary.md",
    }
    overall.to_csv(outputs["baseline_overall"], index=False)
    summarise_waits_by_department(df).to_csv(outputs["baseline_by_department"], index=False)
    summarise_waits_by_stage(df).to_csv(outputs["baseline_by_stage"], index=False)
    summarise_arrivals_by_hour(df).to_csv(outputs["baseline_by_hour"], index=False)
    summarise_peak_vs_offpeak(df).to_csv(outputs["baseline_peak_vs_offpeak"], index=False)
    summarise_priority_differences(df).to_csv(outputs["baseline_by_priority"], index=False)
    comparison = build_scenario_comparison(df)
    comparison.to_csv(outputs["scenario_comparison"], index=False)
    build_scenario_department_effects(df).to_csv(outputs["scenario_by_department"], index=False)
    raw_path = root / "data" / "raw" / "hospital_patient_flow_synthetic.csv"
    raw_rows = len(pd.read_csv(raw_path)) if raw_path.exists() else pd.NA
    pd.DataFrame(
        [
            {
                "raw_rows": raw_rows,
                "processed_rows": len(df),
                "analysis_rows": baseline["audit"]["analysis_rows"],
            }
        ]
    ).to_csv(outputs["dataset_overview"], index=False)

    saved_overall = pd.read_csv(outputs["baseline_overall"]).iloc[0]
    saved_stages = pd.read_csv(outputs["baseline_by_stage"])
    saved_departments = pd.read_csv(outputs["baseline_by_department"])
    saved_peak = pd.read_csv(outputs["baseline_peak_vs_offpeak"])
    saved_priority = pd.read_csv(outputs["baseline_by_priority"])
    saved_scenarios = pd.read_csv(outputs["scenario_comparison"])
    top_bottlenecks = identify_top_bottlenecks(df, n=5)
    top_stage = saved_stages.iloc[0] if not saved_stages.empty else None
    top_department = (
        saved_departments.sort_values("p90_wait_minutes", ascending=False).iloc[0]
        if not saved_departments.empty
        else None
    )
    peak = saved_peak.loc[saved_peak["peak_period"].eq("Peak")]
    offpeak = saved_peak.loc[saved_peak["peak_period"].eq("Non-Peak")]
    peak_median = peak.iloc[0]["median_wait_minutes"] if not peak.empty else float("nan")
    offpeak_median = offpeak.iloc[0]["median_wait_minutes"] if not offpeak.empty else float("nan")
    priority_text = "; ".join(
        f"{row.priority_level}: median {_format_minutes(row.median_wait_minutes)}, "
        f"p90 {_format_minutes(row.p90_wait_minutes)}"
        for row in saved_priority.itertuples(index=False)
    ) or "No priority-level wait comparison was available."
    scenario_candidates = saved_scenarios.loc[saved_scenarios["scenario"].ne("Baseline")]
    best = scenario_candidates.sort_values(
        ["p90_total_valid_wait_minutes", "long_wait_pct"], ascending=True
    ).iloc[0]
    consultation_scenario = saved_scenarios.loc[
        saved_scenarios["scenario"].eq("Consultation wait reduction")
    ].iloc[0]
    peak_priority_scenario = saved_scenarios.loc[
        saved_scenarios["scenario"].eq("Peak priority fast-track")
    ].iloc[0]
    bottleneck_text = (
        "\n".join(
            (
                f"- {row.bottleneck_type.title()}: {row.bottleneck}, "
                f"p90 {_format_minutes(row.p90_wait_minutes)} (n={int(row.patient_count)})"
            )
            for row in top_bottlenecks.itertuples(index=False)
        )
        or "- No measurable bottleneck could be ranked from the available fields."
    )
    stage_text = (
        f"{top_stage['stage']} has the highest observed stage-wait p90 at "
        f"{_format_minutes(top_stage['p90_wait_minutes'])}; "
        f"its share of summed observed stage waits is {top_stage['stage_contribution_pct']:.1f}%."
        if top_stage is not None
        else "No stage wait columns were available."
    )
    department_text = (
        f"{top_department['department']} has the highest department-level p90 total wait "
        f"at {_format_minutes(top_department['p90_wait_minutes'])}."
        if top_department is not None
        else "No department-level wait comparison was available."
    )
    report = "\n".join(
        [
            "# Baseline Decision Summary",
            "",
            "> All records and findings are generated from a synthetic hospital simulation. "
            "These results describe the simulation assumptions, not real hospital performance.",
            "",
            "## Where patients lose time",
            "",
            (
                f"Among {int(saved_overall['wait_count']):,} usable total-wait observations, "
                f"the median total valid wait is "
                f"{_format_minutes(saved_overall['median_wait_minutes'])} and the p90 is "
                f"{_format_minutes(saved_overall['p90_wait_minutes'])}."
            ),
            (
                f"{stage_text} Stage contribution is each stage's share of summed observed "
                "stage-wait minutes, not a decomposition of the total-wait KPI."
            ),
            "",
            "## Top bottlenecks",
            "",
            bottleneck_text,
            "",
            department_text,
            "",
            "## Peak-period pattern",
            "",
            (
                f"The median total wait is {_format_minutes(peak_median)} during the recorded "
                f"Peak period and {_format_minutes(offpeak_median)} during Non-Peak."
            ),
            "Peak labels follow the existing dataset feature and are not inferred as a "
            "causal effect.",
            f"By recorded priority: {priority_text}.",
            "",
            "## Scenario comparison",
            "",
            (
                f"The comparison ranks simulated p90 and long-wait share because the baseline "
                f"median is {_format_minutes(saved_overall['median_wait_minutes'])}; median-only "
                "improvement is uninformative here."
            ),
            (
                f"**{best['scenario']}** has the lowest p90 at "
                f"{_format_minutes(best['p90_total_valid_wait_minutes'])} "
                f"({best['p90_wait_change_vs_baseline_minutes']:.1f} minutes versus baseline) "
                f"and a long-wait share change of "
                f"{best['long_wait_change_vs_baseline_pp']:.2f} percentage points."
            ),
            (
                f"Consultation wait reduction lowers Routine consultation waits by "
                f"{consultation_scenario['consultation_reduction_pct']:.0f}%; "
                "peak priority fast-track lowers "
                f"Urgent/Emergency consultation waits during Peak by "
                f"{peak_priority_scenario['peak_priority_reduction_pct']:.0f}%."
            ),
            "Both apply to the same valid analysis records. These are what-if calculations, "
            "not causal evidence or forecasts.",
            "",
            "## Data handling and limitations",
            "",
            (
                f"The analysis excluded "
                f"{int(saved_overall['excluded_invalid_timing_rows']):,} rows with invalid "
                "timing or negative wait evidence."
            ),
            (
                f"A further {int(saved_overall['missing_total_wait_rows']):,} analysis rows "
                "have no valid total wait and do not contribute to wait percentiles."
            ),
            (
                f"Long wait means a total valid wait above "
                f"{saved_overall['long_wait_threshold_minutes']:g} minutes. Laboratory and "
                "pharmacy waits are observed only for records with those stages; stage shares "
                "reflect observed stage-wait values only."
            ),
            "Data cleaning and scenario rules may change results; all findings remain "
            "conditional on this synthetic dataset and its simulation assumptions.",
            "",
        ]
    )
    outputs["report"].write_text(report, encoding="utf-8")
    _update_readme_generated_sections(root, outputs)
    return outputs


def department_wait_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Backward-compatible department summary with the decision-layer metrics."""
    return summarise_waits_by_department(df)
