import pandas as pd
import pytest

from patient_flow.costing import calculate_staffing_budget, format_mwk


def test_role_budget_calculates_monthly_and_period_totals_in_mwk() -> None:
    result = calculate_staffing_budget(
        {
            "Emergency · Nursing · Registered Nurse": {
                "additional_staff": 1.5,
                "monthly_cost_mwk": 450_000,
                "cost_source": "Approved payroll scale 2026",
                "effective_date": "2026-07-01",
            },
            "Laboratory · Technical · Technologist": {
                "additional_staff": 1,
                "monthly_cost_mwk": 600_000,
                "cost_source": "Finance memo 14",
                "effective_date": "2026-08-01",
            },
        },
        months=6,
    )
    assert result["monthly_total_mwk"].sum() == 1_275_000
    assert result["period_total_mwk"].sum() == 7_650_000
    assert result["additional_staff"].sum() == 2.5
    assert result["assumption_complete"].all()


def test_missing_provenance_is_flagged_without_changing_budget_math() -> None:
    result = calculate_staffing_budget(
        {"Pharmacy · Pharmacist": {
            "additional_staff": 1,
            "monthly_cost_mwk": 350_000,
        }},
        months=3,
    )
    assert result.loc[0, "period_total_mwk"] == 1_050_000
    assert not result.loc[0, "assumption_complete"]


@pytest.mark.parametrize(
    ("staff", "cost"),
    [(-1, 0), (0, -1), (float("inf"), 1), (1, float("nan"))],
)
def test_role_budget_rejects_negative_or_non_finite_inputs(
    staff: float, cost: float
) -> None:
    with pytest.raises(ValueError):
        calculate_staffing_budget(
            {"Role": {"additional_staff": staff, "monthly_cost_mwk": cost}}
        )


def test_budget_period_must_be_positive_integer() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        calculate_staffing_budget({}, months=0)


def test_format_mwk_never_converts_currency() -> None:
    assert format_mwk(1250000) == "MWK 1,250,000"
