from __future__ import annotations

import sys
from pathlib import Path

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
from patient_flow.costing import calculate_staffing_budget, format_mwk  # noqa: E402
from patient_flow.flags import boolean_flag_column  # noqa: E402
from patient_flow.prediction import train_long_wait_model  # noqa: E402
from patient_flow.scenarios import (  # noqa: E402
    build_scenario_comparison,
    build_scenario_department_effects,
)
from patient_flow.uncertainty import bootstrap_wait_confidence_intervals  # noqa: E402

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
    """Compatibility wrapper around the shared CSV-safe boolean parser."""
    return boolean_flag_column(pd.DataFrame({"flag": series}), "flag")


def minutes(value: float) -> str:
    return "—" if pd.isna(value) else f"{value:,.1f} min"


def add_empty_state(message: str) -> None:
    st.info(message)


@st.cache_data(show_spinner="Calculating bootstrap confidence intervals…")
def cached_bootstrap_intervals(values: tuple[float, ...]) -> dict[str, float | int]:
    return bootstrap_wait_confidence_intervals(pd.Series(values), n_bootstrap=500)


@st.cache_data(show_spinner="Training and evaluating the long-wait model…")
def cached_prediction_summary(frame: pd.DataFrame) -> dict[str, object]:
    result = train_long_wait_model(frame)
    return {
        "metrics": result["metrics"],
        "feature_effects": result["feature_effects"],
        "roc_curve": result["roc_curve"],
    }


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
            selected_dates = st.sidebar.date_input(
                "Visit date range",
                value=(dates.min().date(), dates.max().date()),
                min_value=dates.min().date(),
                max_value=dates.max().date(),
            )
            if isinstance(selected_dates, (tuple, list)):
                if len(selected_dates) >= 2 and selected_dates[1] is not None:
                    start, end = selected_dates[0], selected_dates[1]
                elif len(selected_dates) == 1:
                    start = end = selected_dates[0]
                else:
                    start, end = dates.min().date(), dates.max().date()
            else:
                start = end = selected_dates
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
    if st.toggle("Estimate 95% bootstrap confidence intervals", value=False):
        intervals = cached_bootstrap_intervals(tuple(waits.astype(float).tolist()))
        ci_cols = st.columns(3)
        ci_cols[0].metric(
            "Median wait 95% CI",
            f"{intervals['median_ci_lower']:.1f}–{intervals['median_ci_upper']:.1f} min",
        )
        ci_cols[1].metric(
            "P90 wait 95% CI",
            f"{intervals['p90_ci_lower']:.1f}–{intervals['p90_ci_upper']:.1f} min",
        )
        ci_cols[2].metric(
            "Long-wait share 95% CI",
            f"{intervals['long_wait_pct_ci_lower']:.1f}–{intervals['long_wait_pct_ci_upper']:.1f}%",
        )
        st.caption(
            f"Percentile bootstrap, 500 replicates, {intervals['observations_used']:,} observations "
            "used. Intervals reflect sampling variation within this synthetic cohort only; they "
            "do not capture uncertainty in the simulation assumptions."
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
            monthly["_month"] = pd.to_datetime(monthly["Visit_Date"], errors="coerce").dt.strftime("%Y-%m")
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
    st.subheader("Long-wait classification model")
    st.caption(
        "An interpretable logistic-regression baseline estimates whether an encounter will exceed "
        "the project's 60-minute long-wait threshold. Only department, recorded priority, visit type, "
        "and arrival-time features are eligible predictors; wait components, length of stay, and "
        "disposition are excluded to reduce target leakage."
    )
    if st.toggle("Train and evaluate the long-wait model", value=False):
        try:
            prediction = cached_prediction_summary(cohort)
            model_metrics = prediction["metrics"]
            model_cols = st.columns(5)
            model_cols[0].metric("ROC AUC", f"{model_metrics['roc_auc']:.3f}")
            model_cols[1].metric("Average precision", f"{model_metrics['average_precision']:.3f}")
            model_cols[2].metric("Recall", f"{model_metrics['recall']:.3f}")
            model_cols[3].metric("Precision", f"{model_metrics['precision']:.3f}")
            model_cols[4].metric("F1 score", f"{model_metrics['f1']:.3f}")
            st.caption(
                f"Stratified random hold-out: {model_metrics['train_observations']:,} training and "
                f"{model_metrics['test_observations']:,} test encounters. Long-wait prevalence: "
                f"{model_metrics['long_wait_prevalence_pct']:.1f}%. Classification threshold: "
                f"{model_metrics['threshold']:.2f}."
            )
            roc_left, roc_right = st.columns(2)
            with roc_left:
                roc = prediction["roc_curve"]
                chart = px.line(
                    roc,
                    x="false_positive_rate",
                    y="true_positive_rate",
                    title="Receiver operating characteristic",
                    template=CHART_TEMPLATE,
                    labels={
                        "false_positive_rate": "False-positive rate",
                        "true_positive_rate": "True-positive rate",
                    },
                )
                chart.add_shape(
                    type="line",
                    x0=0,
                    y0=0,
                    x1=1,
                    y1=1,
                    line=dict(dash="dash"),
                )
                st.plotly_chart(chart, use_container_width=True)
            with roc_right:
                confusion = pd.DataFrame(
                    [
                        [model_metrics["true_negatives"], model_metrics["false_positives"]],
                        [model_metrics["false_negatives"], model_metrics["true_positives"]],
                    ],
                    index=["Actual ≤60 min", "Actual >60 min"],
                    columns=["Predicted ≤60 min", "Predicted >60 min"],
                )
                chart = px.imshow(
                    confusion,
                    text_auto=True,
                    title="Held-out confusion matrix",
                    color_continuous_scale="Blues",
                    labels={"x": "Prediction", "y": "Observed class", "color": "Encounters"},
                )
                st.plotly_chart(chart, use_container_width=True)
            effects = prediction["feature_effects"].head(12).sort_values("coefficient")
            chart = px.bar(
                effects,
                x="coefficient",
                y="feature",
                orientation="h",
                title="Largest logistic-regression coefficients",
                template=CHART_TEMPLATE,
                labels={
                    "coefficient": "Coefficient (log-odds scale)",
                    "feature": "Encoded feature",
                },
            )
            st.plotly_chart(chart, use_container_width=True)
            st.caption(
                "Coefficients describe model associations on the log-odds scale, not causal effects. "
                "This is a single stratified hold-out evaluation on synthetic data; performance "
                "does not establish readiness for clinical or operational deployment."
            )
        except ValueError as exc:
            st.info(f"Model evaluation is unavailable for this filtered cohort: {exc}")

    st.divider()
    st.subheader("Staffing budget planner — Malawi Kwacha (MWK)")
    st.caption(
        "Enter locally verified, fully loaded monthly staff costs. All figures are entered and "
        "reported in MWK; this planner performs no USD conversion and does not supply market "
        "salary estimates. Results are illustrative budget scenarios, not approved hospital costs."
    )
    with st.expander("Set staffing assumptions", expanded=True):
        budget_months = st.number_input(
            "Budget period (months)", min_value=1, max_value=36, value=12, step=1
        )
        roles = [
            "Additional laboratory technician",
            "Additional triage nurse",
            "Additional doctor",
            "Additional registration clerk",
            "Additional pharmacy staff",
        ]
        budget_inputs: dict[str, dict[str, float | int]] = {}
        for role in roles:
            st.markdown(f"**{role}**")
            staff_col, cost_col = st.columns(2)
            staff_count = staff_col.number_input(
                "Additional staff (FTE)",
                min_value=0.0,
                max_value=100.0,
                value=0.0,
                step=0.5,
                key=f"budget_staff_{role}",
            )
            monthly_cost = cost_col.number_input(
                "Fully loaded monthly cost per person (MWK)",
                min_value=0.0,
                max_value=1_000_000_000.0,
                value=0.0,
                step=50_000.0,
                key=f"budget_cost_{role}",
                help="Enter a verified local monthly cost including employer on-costs where appropriate.",
            )
            cost_source = st.text_input(
                "Cost source / payroll reference",
                key=f"budget_source_{role}",
                placeholder="e.g. approved payroll scale or finance estimate",
            )
            effective_date = st.text_input(
                "Effective date (YYYY-MM-DD)",
                key=f"budget_date_{role}",
                placeholder="YYYY-MM-DD",
            )
            budget_inputs[role] = {
                "additional_staff": staff_count,
                "monthly_cost_mwk": monthly_cost,
                "cost_source": cost_source,
                "effective_date": effective_date,
            }

    budget = calculate_staffing_budget(budget_inputs, months=int(budget_months))
    monthly_budget = float(budget["monthly_total_mwk"].sum()) if not budget.empty else 0.0
    period_budget = float(budget["period_total_mwk"].sum()) if not budget.empty else 0.0
    budget_kpis = st.columns(3)
    budget_kpis[0].metric("Monthly incremental budget", format_mwk(monthly_budget))
    budget_kpis[1].metric(f"{int(budget_months)}-month budget", format_mwk(period_budget))
    budget_kpis[2].metric("Additional staff (FTE)", f"{budget['additional_staff'].sum():,.1f}")
    incomplete_costs = budget.loc[
        (budget["monthly_cost_per_person_mwk"] > 0) & ~budget["assumption_complete"]
    ]
    if not incomplete_costs.empty:
        st.warning(
            "Some non-zero cost assumptions are missing a source or a valid effective date. "
            "Treat the budget as provisional until these details are completed."
        )
    if monthly_budget == 0:
        st.info("Enter verified monthly staff costs and additional FTE assumptions to calculate a budget.")
    else:
        chart = px.bar(
            budget.loc[budget["period_total_mwk"] > 0],
            x="role",
            y="period_total_mwk",
            title=f"Incremental staffing budget over {int(budget_months)} months",
            template=CHART_TEMPLATE,
            labels={"role": "Staff category", "period_total_mwk": "Budget (MWK)"},
        )
        chart.update_layout(xaxis_tickangle=-20)
        st.plotly_chart(chart, use_container_width=True)
    st.dataframe(
        budget.assign(
            monthly_cost_per_person_mwk=budget["monthly_cost_per_person_mwk"].map(format_mwk),
            monthly_total_mwk=budget["monthly_total_mwk"].map(format_mwk),
            period_total_mwk=budget["period_total_mwk"].map(format_mwk),
        ),
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "Download staffing budget (MWK CSV)",
        data=budget.to_csv(index=False).encode("utf-8"),
        file_name="hospital_staffing_budget_mwk.csv",
        mime="text/csv",
    )

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
