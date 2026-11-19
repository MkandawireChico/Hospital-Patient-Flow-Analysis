from __future__ import annotations

from pathlib import Path

import pandas as pd

from patient_flow.config import PROJECT_ROOT

STAFF_PATH = PROJECT_ROOT / "data" / "reference" / "staff_directory_synthetic.csv"
ROSTER_PATH = PROJECT_ROOT / "data" / "reference" / "staff_roster_synthetic.csv"
SHIFT_HOURS = 8


def generate_monthly_roster(
    staff: pd.DataFrame,
    start_date: str = "2026-01-01",
    days: int = 28,
) -> pd.DataFrame:
    """Build a deterministic illustrative roster; it is not a validated safe-staffing plan."""
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
            # Each person receives two staggered rest days in each seven-day cycle.
            weekday_slot = (day_offset + staff_index * 2) % 7
            if weekday_slot in {5, 6}:
                shift = "OFF"
                start_time = ""
                end_time = ""
                hours = 0
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
                    shift = "DAY"
                    start_time, end_time = "07:00", "15:00"
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


def ensure_roster(
    staff_path: Path = STAFF_PATH,
    roster_path: Path = ROSTER_PATH,
    start_date: str = "2026-01-01",
    days: int = 28,
) -> pd.DataFrame:
    """Load the committed synthetic register and reproducibly create its roster."""
    staff = pd.read_csv(staff_path)
    roster = generate_monthly_roster(staff, start_date=start_date, days=days)
    roster_path.parent.mkdir(parents=True, exist_ok=True)
    roster.to_csv(roster_path, index=False)
    return roster


if __name__ == "__main__":
    generated = ensure_roster()
    print(f"Generated {len(generated):,} synthetic roster assignments at {ROSTER_PATH}")
