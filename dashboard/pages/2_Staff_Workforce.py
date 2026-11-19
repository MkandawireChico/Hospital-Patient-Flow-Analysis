from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from patient_flow.capacity import build_capacity_sensitivity  # noqa: E402
from patient_flow.workforce import (  # noqa: E402
    ENCOUNTER_PATH,
    STAFF_PATH,
    build_demand_coverage,
    build_workforce_summary,
    ensure_roster,
)

st.set_page_config(page_title="Workforce & Roster", page_icon="👥", layout="wide")
st.title("Workforce & Roster Intelligence")
st.caption("Workforce composition, scheduled coverage and patient-arrival workload analysis")

if not STAFF_PATH.exists():
    st.error("Staff directory is missing. Check data/reference/staff_directory_synthetic.csv.")
    st.stop()
if not ENCOUNTER_PATH.exists():
    st.error("Run the patient-flow pipeline first: python -m patient_flow.cli run")
    st.stop()

staff = pd.read_csv(STAFF_PATH)
encounters = pd.read_csv(ENCOUNTER_PATH)
roster = ensure_roster()
summary = build_workforce_summary(roster)
coverage = build_demand_coverage(encounters, roster)

st.sidebar.header("Workforce filters")
departments = sorted(staff["Department"].dropna().unique().tolist())
selected_departments = st.sidebar.multiselect("Department", departments, default=departments)
staff_view = staff.loc[staff["Department"].isin(selected_departments)].copy()
roster_view = roster.loc[roster["Department"].isin(selected_departments)].copy()
summary_view = summary.loc[summary["Department"].isin(selected_departments)].copy()
coverage_view = coverage.loc[coverage["Department"].isin(selected_departments)].copy()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Registered staff", f"{len(staff_view):,}")
k2.metric("Departments represented", f"{staff_view['Department'].nunique():,}")
k3.metric("Scheduled shift records", f"{roster_view['Shift'].ne('OFF').sum():,}")
k4.metric("Scheduled hours", f"{roster_view['Scheduled_Hours'].sum():,.0f}")

left, right = st.columns(2)
with left:
    category = staff_view.groupby("Staff_Category").size().reset_index(name="Staff")
    st.plotly_chart(px.bar(category, x="Staff_Category", y="Staff", title="Workforce composition by category"), use_container_width=True)
with right:
    dept = staff_view.groupby("Department").size().reset_index(name="Staff")
    st.plotly_chart(px.bar(dept, x="Department", y="Staff", title="Staff establishment by department"), use_container_width=True)

st.subheader("Shift coverage")
if not summary_view.empty:
    coverage_by_shift = summary_view.groupby(["Roster_Date", "Shift"], as_index=False)["Staff_On_Duty"].sum()
    pivot = coverage_by_shift.pivot(index="Roster_Date", columns="Shift", values="Staff_On_Duty").fillna(0)
    st.plotly_chart(px.line(pivot.reset_index(), x="Roster_Date", y=list(pivot.columns), markers=True, title="Hospital-wide scheduled staff by shift"), use_container_width=True)
    dept_coverage = summary_view.groupby(["Department", "Shift"], as_index=False)["Staff_On_Duty"].mean()
    st.plotly_chart(px.bar(dept_coverage, x="Department", y="Staff_On_Duty", color="Shift", barmode="group", title="Average scheduled staff by department and shift"), use_container_width=True)

st.subheader("Service demand and workforce coverage")
st.caption("Clinical demand uses encounter department. Laboratory and pharmacy demand use recorded stage-use fields; registration demand maps to Administration. Events are grouped by patient arrival shift as a timing proxy, not verified service-start shift. Workload ratios are descriptive, not validated capacity or staffing-safety measures.")
if not coverage_view.empty:
    demand_left, demand_right = st.columns(2)
    with demand_left:
        daily_demand = coverage_view.groupby(["Roster_Date", "Department"], as_index=False)["Demand_Events"].sum()
        st.plotly_chart(px.line(daily_demand, x="Roster_Date", y="Demand_Events", color="Department", title="Daily demand events by workforce unit"), use_container_width=True)
    with demand_right:
        workload = coverage_view.groupby(["Department", "Shift"], as_index=False).agg(
            Demand_Events=("Demand_Events", "sum"),
            Mean_Staff=("Staff_On_Duty", "mean"),
        )
        st.plotly_chart(px.bar(workload, x="Department", y="Demand_Events", color="Shift", barmode="group", title="Encounter and service-stage demand by shift"), use_container_width=True)

    valid_workload = coverage_view.dropna(subset=["Demand_Events_Per_Staff"])
    if not valid_workload.empty:
        st.plotly_chart(
            px.box(valid_workload, x="Department", y="Demand_Events_Per_Staff", color="Shift",
                   title="Distribution of demand events per rostered staff member and shift",
                   points=False),
            use_container_width=True,
        )
    daily_staffing = coverage_view.groupby(["Roster_Date", "Department"], as_index=False).agg(
        Demand_Events=("Demand_Events", "sum"),
        Staff_On_Duty=("Staff_On_Duty", "sum"),
    )
    heat = daily_staffing.pivot(index="Department", columns="Roster_Date", values="Demand_Events").fillna(0)
    st.plotly_chart(px.imshow(heat, aspect="auto", color_continuous_scale="Blues",
                              labels={"x": "Roster date", "y": "Workforce unit", "color": "Demand events"},
                              title="Workforce-unit demand intensity across the roster period"),
                    use_container_width=True)
    st.dataframe(coverage_view, use_container_width=True, hide_index=True)
    st.download_button("Download demand and coverage analysis", coverage_view.to_csv(index=False).encode("utf-8"),
                       "workforce_demand_coverage.csv", "text/csv")
else:
    st.info("No demand events could be aligned to the selected workforce units and roster dates.")

st.divider()
st.subheader("Workforce capacity sensitivity")
st.caption(
    "Test how additional rostered hours change the observed demand-per-hour ratio for one workforce unit. "
    "The scenario does not predict waiting-time reductions, throughput, clinical outcomes or safe staffing."
)
if not coverage_view.empty:
    unit_options = sorted(coverage_view["Department"].dropna().unique().tolist())
    selected_unit = st.selectbox("Workforce unit for sensitivity", unit_options)
    scenario_left, scenario_right = st.columns(2)
    with scenario_left:
        additional_fte = st.number_input(
            "Additional FTE across the analysis period",
            min_value=0.0,
            max_value=50.0,
            value=0.0,
            step=0.5,
            key="capacity_additional_fte",
        )
        monthly_hours = st.number_input(
            "Assumed hours per FTE per 30-day month",
            min_value=1.0,
            max_value=240.0,
            value=160.0,
            step=8.0,
            key="capacity_monthly_hours",
        )
    with scenario_right:
        monthly_cost = st.number_input(
            "Fully loaded monthly cost per FTE (MWK)",
            min_value=0.0,
            max_value=1_000_000_000.0,
            value=0.0,
            step=50_000.0,
            key="capacity_monthly_cost",
        )
        cost_source = st.text_input(
            "Cost source / payroll reference",
            key="capacity_cost_source",
            placeholder="Approved payroll scale or finance reference",
        )
        effective_date = st.text_input(
            "Cost effective date (YYYY-MM-DD)",
            key="capacity_cost_date",
            placeholder="YYYY-MM-DD",
        )

    period_days = int(coverage_view["Roster_Date"].nunique())
    period_months = period_days / 30.0
    sensitivity = build_capacity_sensitivity(
        coverage_view,
        workforce_unit=selected_unit,
        additional_fte=additional_fte,
        monthly_cost_per_fte_mwk=monthly_cost,
        period_months=period_months,
        monthly_hours_per_fte=monthly_hours,
    )
    metric_cols = st.columns(3)
    baseline_rate = sensitivity["baseline_demand_events_per_scheduled_hour"]
    scenario_rate = sensitivity["scenario_demand_events_per_scheduled_hour"]
    metric_cols[0].metric(
        "Current demand events / scheduled hour",
        "Not available" if pd.isna(baseline_rate) else f"{baseline_rate:.3f}",
    )
    metric_cols[1].metric(
        "Scenario demand events / scheduled hour",
        "Not available" if pd.isna(scenario_rate) else f"{scenario_rate:.3f}",
        delta=(
            "Not available"
            if pd.isna(baseline_rate) or pd.isna(scenario_rate)
            else f"{scenario_rate - baseline_rate:+.3f}"
        ),
    )
    metric_cols[2].metric(
        "Incremental period budget",
        f"MWK {sensitivity['incremental_period_budget_mwk']:,.0f}",
    )
    comparison = pd.DataFrame({
        "Scenario": ["Current roster", "Added-hours sensitivity"],
        "Demand events per scheduled hour": [baseline_rate, scenario_rate],
    })
    st.plotly_chart(
        px.bar(
            comparison,
            x="Scenario",
            y="Demand events per scheduled hour",
            title=f"{selected_unit}: workload intensity sensitivity",
        ),
        use_container_width=True,
    )
    if additional_fte > 0 and monthly_cost > 0:
        valid_date = pd.to_datetime(effective_date, errors="coerce")
        if not cost_source.strip() or pd.isna(valid_date):
            st.warning("The non-zero MWK cost is provisional until a source reference and valid effective date are recorded.")
    st.caption(
        f"Analysis window: {period_days} roster days, cost and added hours prorated over {period_months:.2f} 30-day months. "
        f"Added hours assume {monthly_hours:.0f} hours per FTE-month. This is an explicit sensitivity assumption, "
        "not a prediction that the same hours can be safely scheduled in every shift."
    )
    st.download_button(
        "Download capacity sensitivity (CSV)",
        data=pd.DataFrame([sensitivity]).to_csv(index=False).encode("utf-8"),
        file_name="workforce_capacity_sensitivity.csv",
        mime="text/csv",
    )

st.subheader("Staff directory")
st.dataframe(staff_view, use_container_width=True, hide_index=True)
st.download_button("Download staff directory", staff_view.to_csv(index=False).encode("utf-8"),
                   "staff_directory.csv", "text/csv")

st.subheader("Roster detail")
st.dataframe(roster_view, use_container_width=True, hide_index=True)
st.download_button("Download filtered roster", roster_view.to_csv(index=False).encode("utf-8"),
                   "staff_roster.csv", "text/csv")

st.caption("Data provenance and modelling assumptions are documented in the Workforce Analytics guide.")
