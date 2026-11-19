from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Support both `streamlit run dashboard/app.py` and package-installed execution.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from patient_flow.analysis import (  # noqa: E402
    filter_analysis_frame,
    summarise_arrivals_by_hour,
    summarise_priority_differences,
    summarise_waits_by_department,
    summarise_waits_by_stage,
)
from patient_flow.scenarios import (  # noqa: E402
    build_scenario_comparison,
    build_scenario_department_effects,
)

DATA_PATH = PROJECT_ROOT / "data" / "processed" / "hospital_patient_flow_clean.csv"
WAIT_COLUMN = "Total_Waiting_Time_Valid"
LONG_WAIT_THRESHOLD = 60.0
CHART_TEMPLATE = "plotly_white"


st.set_page_config(
    page_title="Hospital Operations Command Centre",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner="Loading synthetic encounter data…")
def load_data(path: str, modified_time: float) -> pd.DataFrame:
    """Load the processed encounter table; mtime invalidates the cache after a pipeline run."""
    del modified_time
    return pd.read_csv(path)


def as_bool(series: pd.Series) -> pd.Series:
    """Parse real booleans and common CSV string representations safely."""
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)
    return (
        series.astype("string")
        .str.strip()
        .str.casefold()
        .isin({"true", "1", "yes", "y"})
        .fillna(False)
    )


def minutes(value: float) -> str:
    return "—" if pd.isna(value) else f"{value:,.1f} min"


def add_empty_state(message: str) -> None:
    st.info(message)


def main() -> None:
    st.title("Hospital Operations Command Centre")
    st.caption(
        "An interactive operational analytics view of a fictional, Malawi-inspired district "
        "hospital. All records are synthetic; this is a portfolio simulation, not live hospital data."
    )
    st.warning(
        "Synthetic-data notice: Chilungamo District Hospital is fictional. These charts describe "
        "the simulation only and must not be interpreted as evidence about a real facility."
    )

    if not DATA_PATH.exists():
        st.error(
            f"Processed data was not found at `{DATA_PATH.relative_to(PROJECT_ROOT)}`. "
            "Run `python -m patient_flow.cli run` from the project root, then refresh this page."
        )
        st.stop()

    try:
        data = load_data(str(DATA_PATH), DATA_PATH.stat().st_mtime)
    except (OSError, pd.errors.ParserError) as exc:
        st.error(f"Could not load the processed dataset: {exc}")
        st.stop()

    st.sidebar.header("Explore the encounter cohort")
    st.sidebar.caption("Filters apply to all charts and summary metrics.")

    if "Visit_Date" in data.columns:
        dates = pd.to_datetime(data["Visit_Date"], errors="coerce").dropna()
        if not dates.empty:
            start, end = st.sidebar.date_input(
                "Visit date range",
                value=(dates.min().date(), dates.max().date()),
                min_value=dates.min().date(),
                max_value=dates.max().date(),
            )
            if isinstance(start, tuple):
                start, end = start
            data["_visit_date"] = pd.to_datetime(data["Visit_Date"], errors="coerce")
            data = data.loc[data["_visit_date"].dt.date.between(start, end)].copy()

    for column, label in [
        ("Department", "Department"),
        ("Priority_Level", "Priority"),
        ("Visit_Type", "Visit type"),
        ("Disposition", "Disposition"),
    ]:
        if column in data.columns:
            options = sorted(data[column].dropna().astype(str).unique().tolist())
            selected = st.sidebar.multiselect(label, options, default=options)
            if selected:
                data = data.loc[data[column].astype(str).isin(selected)].copy()
            else:
                data = data.iloc[0:0].copy()

    if data.empty:
        add_empty_state("No encounters match the selected filters. Widen the date range or selections.")
        st.stop()

    cohort = filter_analysis_frame(data)
    wait_col = WAIT_COLUMN if WAIT_COLUMN in cohort.columns else (
        "Total_Waiting_Time" if "Total_Waiting_Time" in cohort.columns else None
    )
    if wait_col is None:
        st.error("The dataset needs Total_Waiting_Time_Valid or Total_Waiting_Time.")
        st.stop()

    waits = pd.to_numeric(cohort[wait_col], errors="coerce").dropna()
    if waits.empty:
        add_empty_state("There are no valid waiting-time observations in this filtered cohort.")
        st.stop()

    n_encounters = len(cohort)
    n_waits = int(waits.count())
    long_wait_share = float(waits.gt(LONG_WAIT_THRESHOLD).mean() * 100)
    median_wait = float(waits.median())
    p90_wait = float(waits.quantile(0.90))
    mean_wait = float(waits.mean())

    st.subheader("Performance at a glance")
    kpis = st.columns(5)
    kpis[0].metric("Encounters", f"{n_encounters:,}")
    kpis[1].metric("Mean valid wait", minutes(mean_wait))
    kpis[2].metric("Median valid wait", minutes(median_wait))
    kpis[3].metric("90th percentile wait", minutes(p90_wait))
    kpis[4].metric("Long waits (>60 min)", f"{long_wait_share:.1f}%")
    st.caption(
        f"{n_waits:,} encounters have a usable total-wait value. "
        "Percentiles describe the upper tail as well as the typical encounter."
    )

    overview_left, overview_right = st.columns(2)
    with overview_left:
        st.subheader("Waiting-time distribution")
        histogram = px.histogram(
            waits.to_frame(name="Wait (minutes)"),
            x="Wait (minutes)",
            nbins=45,
            marginal="box",
            title="How long do encounters wait?",
            template=CHART_TEMPLATE,
            labels={"count": "Encounters"},
        )
        histogram.add_vline(
            x=LONG_WAIT_THRESHOLD,
            line_dash="dash",
            annotation_text="60-minute threshold",
        )
        histogram.update_layout(showlegend=False, xaxis_title="Valid total wait (minutes)")
        st.plotly_chart(histogram, use_container_width=True)

    with overview_right:
        st.subheader("Department bottlenecks")
        department = summarise_waits_by_department(cohort)
        if not department.empty:
            department = department.sort_values("p90_wait_minutes", ascending=True)
            chart = px.bar(
                department,
                x="p90_wait_minutes",
                y="department",
                orientation="h",
                color="patient_count",
                color_continuous_scale="Blues",
                hover_data=["median_wait_minutes", "long_wait_pct", "patient_count"],
                title="90th percentile wait by department",
                template=CHART_TEMPLATE,
                labels={
                    "p90_wait_minutes": "P90 wait (minutes)",
                    "department": "Department",
                    "patient_count": "Encounters",
                },
            )
            st.plotly_chart(chart, use_container_width=True)
        else:
            add_empty_state("Department-level data is not available.")

    st.divider()
    trend_left, trend_right = st.columns(2)
    with trend_left:
        st.subheader("Arrival pressure by hour")
        hourly = summarise_arrivals_by_hour(cohort)
        hourly = hourly.dropna(subset=["arrival_hour"])
        if not hourly.empty:
            hourly["arrival_hour"] = hourly["arrival_hour"].astype(int)
            hourly = hourly.sort_values("arrival_hour")
            chart = go.Figure()
            chart.add_trace(
                go.Bar(
                    x=hourly["arrival_hour"],
                    y=hourly["patient_count"],
                    name="Encounters",
                    yaxis="y",
                )
            )
            chart.add_trace(
                go.Scatter(
                    x=hourly["arrival_hour"],
                    y=hourly["p90_wait_minutes"],
                    name="P90 wait",
                    mode="lines+markers",
                    yaxis="y2",
                )
            )
            chart.update_layout(
                title="Arrival volume and upper-tail wait",
                template=CHART_TEMPLATE,
                xaxis_title="Arrival hour",
                yaxis=dict(title="Encounter count"),
                yaxis2=dict(title="P90 wait (minutes)", overlaying="y", side="right"),
                legend=dict(orientation="h", y=1.12),
            )
            st.plotly_chart(chart, use_container_width=True)
        else:
            add_empty_state("Arrival-hour information is not available.")

    with trend_right:
        st.subheader("Monthly waiting-time trend")
        if "Visit_Date" in cohort.columns:
            monthly = cohort.copy()
            monthly["_month"] = pd.to_datetime(monthly["Visit_Date"], errors="coerce").dt.to_period("M").astype(str)
            monthly["_wait"] = pd.to_numeric(monthly[wait_col], errors="coerce")
            monthly = monthly.dropna(subset=["_wait", "_month"])
            if not monthly.empty:
                monthly = (
                    monthly.groupby("_month", as_index=False)
                    .agg(
                        median_wait=("_wait", "median"),
                        p90_wait=("_wait", lambda values: values.quantile(0.90)),
                        encounters=("_wait", "size"),
                    )
                )
                chart = px.line(
                    monthly,
                    x="_month",
                    y=["median_wait", "p90_wait"],
                    markers=True,
                    title="Monthly median and P90 wait",
                    template=CHART_TEMPLATE,
                    labels={"_month": "Visit month", "value": "Wait (minutes)", "variable": "Metric"},
                )
                st.plotly_chart(chart, use_container_width=True)
            else:
                add_empty_state("There are no dated wait observations for this selection.")
        else:
            add_empty_state("Visit dates are not available.")

    st.divider()
    stage_left, stage_right = st.columns(2)
    with stage_left:
        st.subheader("Where stage delays accumulate")
        stages = summarise_waits_by_stage(cohort)
        if not stages.empty:
            chart = px.bar(
                stages.sort_values("p90_wait_minutes", ascending=True),
                x="p90_wait_minutes",
                y="stage",
                orientation="h",
                color="stage_contribution_pct",
                color_continuous_scale="Oranges",
                hover_data=["median_wait_minutes", "stage_contribution_pct", "wait_count"],
                title="Stage-level P90 wait",
                template=CHART_TEMPLATE,
                labels={
                    "p90_wait_minutes": "P90 stage wait (minutes)",
                    "stage": "Patient-flow stage",
                    "stage_contribution_pct": "Share of summed stage-wait minutes (%)",
                    "wait_count": "Observed stage waits",
                },
            )
            st.plotly_chart(chart, use_container_width=True)
            st.caption(
                "Contribution is each stage's share of summed observed stage-wait minutes; "
                "it is not a decomposition of total patient waiting time."
            )
        else:
            add_empty_state("Stage-level wait columns are not available.")

    with stage_right:
        st.subheader("Waiting time by priority")
        priority = summarise_priority_differences(cohort)
        if not priority.empty:
            chart = px.bar(
                priority,
                x="priority_level",
                y=["median_wait_minutes", "p90_wait_minutes"],
                barmode="group",
                title="Median versus P90 by recorded priority",
                template=CHART_TEMPLATE,
                labels={
                    "priority_level": "Recorded priority",
                    "value": "Wait (minutes)",
                    "variable": "Metric",
                },
            )
            st.plotly_chart(chart, use_container_width=True)
        else:
            add_empty_state("Priority-level comparisons are not available.")

    st.divider()
    st.subheader("What-if operational scenarios")
    st.caption(
        "Scenarios are transparent mathematical what-if transformations, not forecasts or "
        "causal estimates. They assume a 20% reduction in targeted consultation waits."
    )
    scenarios = build_scenario_comparison(cohort)
    scenario_left, scenario_right = st.columns(2)
    with scenario_left:
        chart = px.bar(
            scenarios,
            x="scenario",
            y="p90_total_valid_wait_minutes",
            color="scenario",
            title="P90 total wait by scenario",
            template=CHART_TEMPLATE,
            labels={"scenario": "Scenario", "p90_total_valid_wait_minutes": "P90 wait (minutes)"},
        )
        chart.update_layout(showlegend=False, xaxis_tickangle=-15)
        st.plotly_chart(chart, use_container_width=True)
    with scenario_right:
        chart = px.bar(
            scenarios,
            x="scenario",
            y="long_wait_pct",
            color="scenario",
            title="Share of encounters waiting over 60 minutes",
            template=CHART_TEMPLATE,
            labels={"scenario": "Scenario", "long_wait_pct": "Long-wait encounters (%)"},
        )
        chart.update_layout(showlegend=False, xaxis_tickangle=-15)
        st.plotly_chart(chart, use_container_width=True)

    effects = build_scenario_department_effects(cohort)
    if not effects.empty:
        st.markdown("**Department-level scenario effect (median wait change)**")
        chart = px.bar(
            effects,
            x="department",
            y="median_wait_change_minutes",
            color="scenario",
            barmode="group",
            title="Change versus baseline; negative values indicate lower median wait",
            template=CHART_TEMPLATE,
            labels={
                "department": "Department",
                "median_wait_change_minutes": "Change in median wait (minutes)",
                "scenario": "What-if scenario",
            },
        )
        st.plotly_chart(chart, use_container_width=True)

    st.divider()
    st.subheader("Data quality and audit")
    audit_left, audit_right = st.columns([1, 2])
    with audit_left:
        quality_flags = [
            ("Impossible timestamps", "Impossible_Timestamp_Flag"),
            ("Negative waits", "Negative_Wait_Flag"),
            ("Department labels", "Department_Data_Error"),
            ("Length-of-stay outliers", "LOS_Outlier_Flag"),
        ]
        for label, column in quality_flags:
            count = int(as_bool(data[column]).sum()) if column in data.columns else 0
            st.metric(label, f"{count:,}")
    with audit_right:
        audit = cohort.attrs.get("analysis_audit", {})
        st.write(
            {
                "Filtered encounters before exclusions": int(len(data)),
                "Rows excluded from wait analysis": int(audit.get("excluded_invalid_timing_rows", 0)),
                "Encounters retained for analysis": int(len(cohort)),
                "Missing valid total waits": int(audit.get("missing_total_wait_rows", 0)),
                "Wait threshold (minutes)": LONG_WAIT_THRESHOLD,
            }
        )
        st.caption(
            "Rows with invalid timing or negative-wait evidence are excluded from wait KPIs. "
            "Missing stage waits remain missing rather than being converted to zero."
        )

    st.subheader("Explore the filtered records")
    display_columns = [
        column
        for column in [
            "Encounter_ID",
            "Visit_Date",
            "Department",
            "Priority_Level",
            "Arrival_Hour",
            WAIT_COLUMN,
            "Total_Length_of_Stay",
            "Long_Wait_Flag",
        ]
        if column in cohort.columns
    ]
    st.dataframe(cohort[display_columns].head(500), use_container_width=True, hide_index=True)
    st.download_button(
        "Download filtered encounter data (CSV)",
        data=cohort.to_csv(index=False).encode("utf-8"),
        file_name="hospital_patient_flow_filtered.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()
