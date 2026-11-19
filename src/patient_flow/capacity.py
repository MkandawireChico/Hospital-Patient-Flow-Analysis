from __future__ import annotations

import math

import pandas as pd


def build_capacity_sensitivity(
    coverage: pd.DataFrame,
    workforce_unit: str,
    additional_fte: float,
    monthly_cost_per_fte_mwk: float,
    period_months: float,
    monthly_hours_per_fte: float = 160.0,
) -> dict[str, float | int | str]:
    """Compare observed workload intensity with an explicit added-hours scenario.

    Additional hours are modelled at a configurable monthly-hours assumption.
    This is a workload sensitivity, not a queueing model or a forecast of waits,
    throughput, clinical outcomes, or safe staffing.
    """
    numeric_inputs = {
        "additional_fte": additional_fte,
        "monthly_cost_per_fte_mwk": monthly_cost_per_fte_mwk,
        "period_months": period_months,
        "monthly_hours_per_fte": monthly_hours_per_fte,
    }
    if any(not math.isfinite(float(value)) for value in numeric_inputs.values()):
        raise ValueError("Capacity scenario inputs must be finite numbers")
    if additional_fte < 0 or monthly_cost_per_fte_mwk < 0:
        raise ValueError("Additional FTE and monthly cost cannot be negative")
    if period_months <= 0 or monthly_hours_per_fte <= 0:
        raise ValueError("Period months and monthly hours per FTE must be positive")

    required = {"Department", "Demand_Events", "Scheduled_Hours"}
    missing = required.difference(coverage.columns)
    if missing:
        raise ValueError(f"Coverage data is missing columns: {sorted(missing)}")
    selected = coverage.loc[coverage["Department"].eq(workforce_unit)]
    if selected.empty:
        raise ValueError(f"No demand-coverage records found for {workforce_unit!r}")

    demand_events = float(pd.to_numeric(selected["Demand_Events"], errors="coerce").fillna(0).sum())
    scheduled_hours = float(
        pd.to_numeric(selected["Scheduled_Hours"], errors="coerce").fillna(0).sum()
    )
    added_hours = float(additional_fte * monthly_hours_per_fte * period_months)
    scenario_hours = scheduled_hours + added_hours
    baseline_rate = demand_events / scheduled_hours if scheduled_hours > 0 else float("nan")
    scenario_rate = demand_events / scenario_hours if scenario_hours > 0 else float("nan")
    monthly_budget = float(additional_fte * monthly_cost_per_fte_mwk)
    period_budget = float(monthly_budget * period_months)

    return {
        "workforce_unit": workforce_unit,
        "demand_events": demand_events,
        "current_scheduled_hours": scheduled_hours,
        "additional_fte": float(additional_fte),
        "assumed_monthly_hours_per_fte": float(monthly_hours_per_fte),
        "additional_hours_in_period": added_hours,
        "scenario_scheduled_hours": scenario_hours,
        "baseline_demand_events_per_scheduled_hour": baseline_rate,
        "scenario_demand_events_per_scheduled_hour": scenario_rate,
        "monthly_cost_per_fte_mwk": float(monthly_cost_per_fte_mwk),
        "incremental_monthly_budget_mwk": monthly_budget,
        "period_months": float(period_months),
        "incremental_period_budget_mwk": period_budget,
    }
