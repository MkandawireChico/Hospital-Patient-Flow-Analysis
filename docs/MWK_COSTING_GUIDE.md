# Malawi Kwacha (MWK) Costing Guide

## Purpose

The dashboard's budget planner estimates the incremental staffing budget for a hypothetical operational change. All amounts are denominated in **Malawi Kwacha (MWK)**. It does not convert currencies or supply salary benchmarks.

## Required inputs

For each role, provide:

- Additional full-time-equivalent staff (FTE).
- Fully loaded monthly cost per staff member in MWK.
- Source of the cost assumption and its effective date.

The fully loaded cost should be defined consistently. Depending on the organisation's accounting practice, it may include gross salary, employer pension contributions, allowances, statutory employer contributions, and other recurring employment costs. Do not add an item twice if it is already included in the supplied monthly amount.

## Formula

For each role:

`Monthly role budget = Additional FTE × Monthly fully loaded cost per person (MWK)`

`Period budget = Monthly role budget × Number of budget months`

The total budget is the sum of the role-level budgets. The dashboard also exports the underlying inputs so assumptions can be reviewed.

## Governance and interpretation

- Starting values in the dashboard are zero by design; they are not Malawi salary estimates.
- Use current, authorised local payroll or finance sources and record their effective dates.
- Confirm whether costs are monthly, per contract, or per FTE before entering them.
- A staffing budget is not a full cost-benefit analysis.
- Do not infer that a staffing change will produce the simulated wait reduction in the scenario charts.
- Do not monetise patient waiting time or clinical harm without a defensible local valuation method and appropriate approval.
- The cost planner is a portfolio demonstration and not a substitute for institutional budgeting or procurement review.

## Template

Use `config/mwk_staffing_cost_template.csv` to record the assumptions and their sources before entering values into the dashboard.
