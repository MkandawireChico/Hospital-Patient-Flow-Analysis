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
    STAFF_PATH,
    build_workforce_summary,
    ensure_roster,
)

st.set_page_config(page_title="Workforce & Roster", page_icon="👥", layout="wide")
st.title("Workforce & Roster Intelligence")
st.caption("Synthetic staff directory, shift coverage and scheduled-hours analysis")

st.warning(
    "All staff names, IDs, qualifications, employment dates and shifts are fictional. "
    "This is a portfolio simulation, not a real hospital HR register or safe-staffing tool."
)

if not STAFF_PATH.exists():
    st.error("Synthetic staff directory is missing. Check data/reference/staff_directory_synthetic.csv.")
    st.stop()

staff = pd.read_csv(STAFF_PATH)
roster = ensure_roster()
summary = build_workforce_summary(roster)

st.sidebar.header("Workforce filters")
departments = sorted(staff["Department"].dropna().unique().tolist())
selected_departments = st.sidebar.multiselect("Department", departments, default=departments)
staff_view = staff.loc[staff["Department"].isin(selected_departments)].copy()
roster_view = roster.loc[roster["Department"].isin(selected_departments)].copy()
summary_view = summary.loc[summary["Department"].isin(selected_departments)].copy()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Registered staff", f"{len(staff_view):,}")
k2.metric("Departments represented", f"{staff_view['Department'].nunique():,}")
k3.metric("Scheduled shift records", f"{roster_view['Shift'].ne('OFF').sum():,}")
k4.metric("Scheduled hours", f"{roster_view['Scheduled_Hours'].sum():,.0f}")

left, right = st.columns(2)
with left:
    category = staff_view.groupby("Staff_Category").size().reset_index(name="Staff")
    st.plotly_chart(px.bar(category, x="Staff_Category", y="Staff", title="Staff mix by category"), use_container_width=True)
with right:
    dept = staff_view.groupby("Department").size().reset_index(name="Staff")
    st.plotly_chart(px.bar(dept, x="Department", y="Staff", title="Staff establishment by department"), use_container_width=True)

st.subheader("Shift coverage")
if not summary_view.empty:
    coverage = summary_view.groupby(["Roster_Date", "Shift"], as_index=False)["Staff_On_Duty"].sum()
    pivot = coverage.pivot(index="Roster_Date", columns="Shift", values="Staff_On_Duty").fillna(0)
    st.plotly_chart(px.line(pivot.reset_index(), x="Roster_Date", y=[c for c in pivot.columns], markers=True, title="Hospital-wide staff scheduled by shift"), use_container_width=True)
    dept_coverage = summary_view.groupby(["Department", "Shift"], as_index=False)["Staff_On_Duty"].mean()
    st.plotly_chart(px.bar(dept_coverage, x="Department", y="Staff_On_Duty", color="Shift", barmode="group", title="Average staff scheduled by department and shift"), use_container_width=True)

st.subheader("Synthetic staff directory")
st.dataframe(staff_view, use_container_width=True, hide_index=True)
st.download_button("Download staff directory (CSV)", staff_view.to_csv(index=False).encode("utf-8"), "staff_directory_synthetic.csv", "text/csv")

st.subheader("Roster detail")
st.caption("The 28-day illustrative roster is regenerated deterministically when this page loads.")
st.dataframe(roster_view, use_container_width=True, hide_index=True)
st.download_button("Download filtered roster (CSV)", roster_view.to_csv(index=False).encode("utf-8"), "staff_roster_synthetic.csv", "text/csv")
