import pandas as pd

from patient_flow.workforce import build_workforce_summary, generate_monthly_roster


def sample_staff() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Staff_ID": "S1", "Staff_Name": "A Banda", "Job_Title": "Nurse", "Department": "Emergency"},
            {"Staff_ID": "S2", "Staff_Name": "B Phiri", "Job_Title": "Clerk", "Department": "Administration"},
        ]
    )


def test_roster_is_reproducible_and_has_one_record_per_person_day() -> None:
    staff = sample_staff()
    first = generate_monthly_roster(staff, start_date="2026-01-01", days=14)
    second = generate_monthly_roster(staff, start_date="2026-01-01", days=14)
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 28
    assert not first.duplicated(["Roster_Date", "Staff_ID"]).any()
    assert first["Simulation_Flag"].all()


def test_rest_days_have_zero_hours_and_work_shifts_have_eight() -> None:
    roster = generate_monthly_roster(sample_staff(), days=14)
    assert (roster.loc[roster["Shift"].eq("OFF"), "Scheduled_Hours"] == 0).all()
    assert (roster.loc[roster["Shift"].ne("OFF"), "Scheduled_Hours"] == 8).all()
    assert set(roster["Shift"]).issubset({"DAY", "EVENING", "NIGHT", "OFF"})


def test_summary_counts_unique_staff_and_scheduled_hours() -> None:
    roster = generate_monthly_roster(sample_staff(), days=7)
    summary = build_workforce_summary(roster)
    assert {"Roster_Date", "Department", "Shift", "Staff_On_Duty", "Scheduled_Hours"} <= set(summary.columns)
    assert (summary["Staff_On_Duty"] >= 1).all()
    assert (summary["Scheduled_Hours"] == summary["Staff_On_Duty"] * 8).all()
