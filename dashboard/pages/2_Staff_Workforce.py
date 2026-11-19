from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

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

st.subheader("Patient arrivals and workforce coverage")
st.caption("Arrival counts are aligned to the roster date, department and shift. Encounters per staff member is a workload indicator; it is not a validated capacity or staffing-safety measure.")
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

    valid_workload = coverage_view.dropna(subset=["Encounters_Per_Staff"])
    if not valid_workload.empty:
        st.plotly_chart(
            px.box(valid_workload, x="Department", y="Encounters_Per_Staff", color="Shift",
                   title="Distribution of encounters per rostered staff member and shift",
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
                              title="Department arrival intensity across the roster period"),
                    use_container_width=True)
    st.dataframe(coverage_view, use_container_width=True, hide_index=True)
    st.download_button("Download demand and coverage analysis", coverage_view.to_csv(index=False).encode("utf-8"),
                       "workforce_demand_coverage.csv", "text/csv")
else:
    st.info("No patient arrivals could be aligned to the selected departments and roster dates.")

st.subheader("Staff directory")
st.dataframe(staff_view, use_container_width=True, hide_index=True)
st.download_button("Download staff directory", staff_view.to_csv(index=False).encode("utf-8"),
                   "staff_directory.csv", "text/csv")

st.subheader("Roster detail")
st.dataframe(roster_view, use_container_width=True, hide_index=True)
st.download_button("Download filtered roster", roster_view.to_csv(index=False).encode("utf-8"),
                   "staff_roster.csv", "text/csv")

st.caption("Data provenance and modelling assumptions are documented in the Workforce Analytics guide.")
