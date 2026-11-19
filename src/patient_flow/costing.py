from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


def calculate_staffing_budget(
    staffing: Mapping[str, Mapping[str, float | int | str]],
    months: int = 12,
) -> pd.DataFrame:
    """Calculate an illustrative incremental staffing budget in Malawi Kwacha (MWK).

    Each role entry must contain:
      - additional_staff: additional full-time-equivalent staff
      - monthly_cost_mwk: verified or explicitly assumed fully loaded monthly cost per person

    This function does not fetch, infer, or convert exchange rates. Costs are supplied by the
    user and should be checked against current local salary scales and employer on-costs.
    """
    if isinstance(months, bool) or not isinstance(months, int) or months < 1:
        raise ValueError("months must be a positive integer")

    rows: list[dict[str, float | int | str]] = []
    for role, values in staffing.items():
        if "additional_staff" not in values or "monthly_cost_mwk" not in values:
            raise ValueError(
                f"{role!r} must include additional_staff and monthly_cost_mwk"
            )
        additional_staff = float(values["additional_staff"])
        monthly_cost = float(values["monthly_cost_mwk"])
        if additional_staff < 0 or monthly_cost < 0:
            raise ValueError("Staff counts and monthly costs cannot be negative")
        monthly_total = additional_staff * monthly_cost
        rows.append(
            {
                "role": str(role),
                "additional_staff": additional_staff,
                "monthly_cost_per_person_mwk": monthly_cost,
                "monthly_total_mwk": monthly_total,
                "budget_period_months": months,
                "period_total_mwk": monthly_total * months,
                "cost_source": str(values.get("cost_source", "")),
                "effective_date": str(values.get("effective_date", "")),
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "role",
            "additional_staff",
            "monthly_cost_per_person_mwk",
            "monthly_total_mwk",
            "budget_period_months",
            "period_total_mwk",
            "cost_source",
            "effective_date",
        ],
    )


def format_mwk(value: float | int) -> str:
    """Format a numeric value as Malawi Kwacha without USD conversion."""
    return f"MWK {float(value):,.0f}"
