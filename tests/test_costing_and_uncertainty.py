import pandas as pd
import pytest

from patient_flow.costing import calculate_staffing_budget, format_mwk
from patient_flow.uncertainty import bootstrap_wait_confidence_intervals


def test_staffing_budget_uses_mwk_and_period_length() -> None:
    result = calculate_staffing_budget(
        {
            "Laboratory technician": {
                "additional_staff": 2,
                "monthly_cost_mwk": 350_000,
                "cost_source": "Approved payroll scale",
                "effective_date": "2026-11-01",
            }
        },
        months=6,
    )

    assert result.loc[0, "monthly_total_mwk"] == 700_000
    assert result.loc[0, "period_total_mwk"] == 4_200_000
    assert result.loc[0, "cost_source"] == "Approved payroll scale"
    assert result.loc[0, "effective_date"] == "2026-11-01"
    assert bool(result.loc[0, "assumption_complete"])


def test_staffing_budget_rejects_negative_costs() -> None:
    with pytest.raises(ValueError):
        calculate_staffing_budget(
            {"Nurse": {"additional_staff": 1, "monthly_cost_mwk": -10}}
        )


def test_staffing_budget_rejects_missing_cost_inputs() -> None:
    with pytest.raises(ValueError):
        calculate_staffing_budget({"Nurse": {"additional_staff": 1}})


def test_mwk_formatter_does_not_convert_currency() -> None:
    assert format_mwk(1_250_000) == "MWK 1,250,000"


def test_bootstrap_intervals_are_reproducible_and_ordered() -> None:
    waits = pd.Series([0, 5, 10, 20, 30, 65, 80, 100] * 20)
    first = bootstrap_wait_confidence_intervals(waits, n_bootstrap=200)
    second = bootstrap_wait_confidence_intervals(waits, n_bootstrap=200)

    assert first == second
    assert first["median_ci_lower"] <= first["median_ci_upper"]
    assert first["p90_ci_lower"] <= first["p90_ci_upper"]
    assert first["long_wait_pct_ci_lower"] <= first["long_wait_pct_ci_upper"]


def test_bootstrap_requires_enough_valid_observations() -> None:
    with pytest.raises(ValueError):
        bootstrap_wait_confidence_intervals(pd.Series([10, None]))
