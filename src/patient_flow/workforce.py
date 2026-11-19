from __future__ import annotations

from pathlib import Path

import pandas as pd

from patient_flow.config import PROJECT_ROOT

STAFF_PATH = PROJECT_ROOT / "data" / "reference" / "staff_directory_synthetic.csv"
ROSTER_PATH = PROJECT_ROOT / "data" / "reference" / "staff_roster_synthetic.csv"
ENCOUNTER_PATH = PROJECT_ROOT / "data" / "processed" / "hospital_patient_flow_clean.csv"
SHIFT_HOURS = 8
SHIFT_WINDOWS = {
    "DAY": (7, 15),
    "EVENING": (15, 23),
    "NIGHT": (23, 7),
}


def generate_monthly_roster(
    staff: pd.DataFrame,
    start_date: str = "2026-01-01",
    days: int = 28,
) -> pd.DataFrame:
    """Build a deterministic illustrative roster for workforce planning analysis."""
    if days < 1:
        raise ValueError("days must be at least one")
    required = {"Staff_ID", "Staff_Name", "Job_Title", "Department"}
    missing = required.difference(staff.columns)
    if missing:
        raise ValueError(f"Staff register is missing columns: {sorted(missing)}")

    start = pd.Timestamp(start_date).normalize()
    records: list[dict[str, object]] = []
    rotating_departments = {"Emergency", "Laboratory", "Pharmacy"}
    for staff_index, person in staff.reset_index(drop=True).iterrows():
        department = str(person["Department"])
        rotating = department in rotating_departments
        for day_offset in range(days):
            day = start + pd.Timedelta(days=day_offset)
            weekday_slot = (day_offset + staff_index * 2) % 7
            if weekday_slot in {5, 6}:
                shift, start_time, end_time, hours = "OFF", "", "", 0
            else:
                shift_index = (day_offset // 7 + staff_index) % 3
                if rotating:
                    shift = ("DAY", "EVENING", "NIGHT")[shift_index]
                    start_time, end_time = {
                        "DAY": ("07:00", "15:00"),
                        "EVENING": ("15:00", "23:00"),
                        "NIGHT": ("23:00", "07:00"),
                    }[shift]
                else:
                    shift, start_time, end_time = "DAY", "07:00", "15:00"
                hours = SHIFT_HOURS
            records.append(
                {
                    "Roster_Date": day.date().isoformat(),
                    "Staff_ID": person["Staff_ID"],
                    "Staff_Name": person["Staff_Name"],
                    "Job_Title": person["Job_Title"],
                    "Department": department,
                    "Shift": shift,
                    "Shift_Start": start_time,
                    "Shift_End": end_time,
                    "Scheduled_Hours": hours,
                    "Roster_Status": "REST" if shift == "OFF" else "SCHEDULED",
                    "Simulation_Flag": True,
                }
            )
    return pd.DataFrame.from_records(records)


def build_workforce_summary(roster: pd.DataFrame) -> pd.DataFrame:
    """Aggregate scheduled headcount and hours by date, department and shift."""
    working = roster.loc[roster["Shift"].ne("OFF")].copy()
    return (
        working.groupby(["Roster_Date", "Department", "Shift"], as_index=False)
        .agg(
            Staff_On_Duty=("Staff_ID", "nunique"),
            Scheduled_Hours=("Scheduled_Hours", "sum"),
        )
        .sort_values(["Roster_Date", "Department", "Shift"])
        .reset_index(drop=True)
    )


def assign_arrival_shift(hours: pd.Series) -> pd.Series:
    """Map arrival hour to the roster's day, evening or overnight shift windows."""
    numeric = pd.to_numeric(hours, errors="coerce")
    return pd.Series(
        pd.cut(
            numeric.mod(24),
            bins=[-0.001, 6.999, 14.999, 22.999, 24],
            labels=["NIGHT", "DAY", "EVENING", "NIGHT"],
            right=True,
            ordered=False,
        ).astype("string"),
        index=hours.index,
    )


def build_demand_coverage(
    encounters: pd.DataFrame,
    roster: pd.DataFrame,
) -> pd.DataFrame:
    """Join encounter and service-stage demand events to rostered shift coverage.

    Demand events per staff member are descriptive workload indicators, not
    clinical productivity, acuity-adjusted capacity, or safe-staffing thresholds.
    """
    required = {"Department", "Arrival_Time"}
    missing = required.difference(encounters.columns)
    if missing:
        raise ValueError(f"Encounter data is missing columns: {sorted(missing)}")
    frame = encounters.copy()
    arrival = pd.to_datetime(frame["Arrival_Time"], errors="coerce")
    frame["Roster_Date"] = arrival.dt.strftime("%Y-%m-%d")
    frame["Shift"] = assign_arrival_shift(arrival.dt.hour)
    demand_frames: list[pd.DataFrame] = []

    # Clinical services are represented by encounter department.
    clinical = (
        frame.dropna(subset=["Roster_Date", "Department", "Shift"])
        .groupby(["Roster_Date", "Department", "Shift"], as_index=False)
        .size()
        .rename(columns={"size": "Demand_Events"})
    )
    clinical["Demand_Basis"] = "Department encounter arrivals"
    demand_frames.append(clinical)

    # Laboratory and pharmacy demand is derived from recorded stage use, not
    # from the encounter's owning department. Arrival shift is a timing proxy
    # because service-stage start timestamps are not consistently available.
    for column, department, basis in [
        ("Laboratory_Wait_Time", "Laboratory", "Recorded laboratory-stage events"),
        ("Pharmacy_Wait_Time", "Pharmacy", "Recorded pharmacy-stage events"),
        ("Wait_For_Registration_Min", "Administration", "Recorded registration-stage events"),
    ]:
        if column not in frame.columns:
            continue
        service = frame.loc[frame[column].notna()].copy()
        service = service.dropna(subset=["Roster_Date", "Shift"])
        if service.empty:
            continue
        grouped = (
            service.groupby(["Roster_Date", "Shift"], as_index=False)
            .size()
            .rename(columns={"size": "Demand_Events"})
        )
        grouped["Department"] = department
        grouped["Demand_Basis"] = basis
        demand_frames.append(grouped)

    demand = pd.concat(demand_frames, ignore_index=True)
    demand["Demand_Shift_Basis"] = "Arrival shift; service-stage shift is not observed"
    coverage = build_workforce_summary(roster)
    result = demand.merge(
        coverage,
        on=["Roster_Date", "Department", "Shift"],
        how="left",
        validate="one_to_one",
    )
    result["Staff_On_Duty"] = result["Staff_On_Duty"].fillna(0).astype(int)
    result["Scheduled_Hours"] = result["Scheduled_Hours"].fillna(0)
    result["Demand_Events_Per_Staff"] = (
        result["Demand_Events"] / result["Staff_On_Duty"].where(result["Staff_On_Duty"].gt(0))
    )
    result["Demand_Events_Per_Scheduled_Hour"] = (
        result["Demand_Events"] / result["Scheduled_Hours"].where(result["Scheduled_Hours"].gt(0))
    )
    result["Coverage_Status"] = result["Staff_On_Duty"].map(
        lambda count: "No rostered staff" if count == 0 else "Rostered"
    )
    return result.sort_values(
        ["Roster_Date", "Department", "Shift"]
    ).reset_index(drop=True)


def ensure_roster(
    staff_path: Path = STAFF_PATH,
    roster_path: Path = ROSTER_PATH,
    start_date: str | None = None,
    days: int | None = None,
    encounter_path: Path = ENCOUNTER_PATH,
) -> pd.DataFrame:
    """Create a reproducible roster aligned to the encounter data's date range."""
    staff = pd.read_csv(staff_path)
    if start_date is None or days is None:
        if encounter_path.exists():
            dates = pd.to_datetime(
                pd.read_csv(encounter_path, usecols=["Visit_Date"])["Visit_Date"],
                errors="coerce",
            ).dropna()
        else:
            dates = pd.Series(dtype="datetime64[ns]")
        if dates.empty:
            start_date = start_date or "2026-01-01"
            days = days or 28
        else:
            start_date = start_date or dates.min().strftime("%Y-%m-%d")
            days = days or int((dates.max().normalize() - dates.min().normalize()).days + 1)
    roster = generate_monthly_roster(staff, start_date=start_date, days=days)
    roster_path.parent.mkdir(parents=True, exist_ok=True)
    roster.to_csv(roster_path, index=False)
    return roster


if __name__ == "__main__":
    generated = ensure_roster()
    print(f"Generated {len(generated):,} roster assignments at {ROSTER_PATH}")
