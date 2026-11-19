# Malawi Kwacha (MWK) Costing Guide

## Purpose

The workforce dashboard includes a role-based planner for comparing proposed additional establishment with an incremental staffing budget. All amounts are denominated in **Malawi Kwacha (MWK)**. It does not convert currencies or supply salary benchmarks.

## Required inputs

For each department and job title being considered, provide:

- Additional full-time-equivalent staff (FTE).
- Fully loaded monthly cost per FTE in MWK.
- Source of the cost assumption and its effective date.

The fully loaded cost should be defined consistently. Depending on the organisation's accounting practice, it may include gross salary, employer pension contributions, allowances, statutory employer contributions, and other recurring employment costs. Do not add an item twice if it is already included in the supplied monthly amount.

## Formula

For each role:

`Monthly role budget = Additional FTE × Monthly fully loaded cost per FTE (MWK)`

`Period role budget = Monthly role budget × Budget period in months`

`Total incremental budget = Sum of period role budgets across selected roles`

The dashboard keeps department, staff category and job title on each budget line. It reports the proposed FTE, monthly cost and period cost by role, then totals the selected proposal.

## Dashboard workflow

1. Open **Workforce & Roster Intelligence** and select the departments to include.
2. In **Role-based establishment and MWK budget planner**, enter additional FTE for the relevant job titles.
3. Enter a locally verified fully loaded monthly cost per FTE in MWK.
4. Record the payroll/finance source and effective date for every non-zero cost assumption.
5. Set the budget period and review the role-level lines, totals and downloadable CSV.

Starting values are zero. They are not Malawi salary estimates. The planner does not automatically populate costs from public salary data and does not assume that different job titles are interchangeable.

## Governance and interpretation

- Use current, authorised local payroll or finance sources and record their effective dates.
- Confirm whether costs are monthly, per contract, or per FTE before entering values.
- A staffing budget is not a full cost-benefit analysis.
- Do not infer that a staffing change will produce the simulated wait reduction in the scenario charts.
- Do not monetise patient waiting time or clinical harm without a defensible local valuation method and appropriate approval.
- A proposed establishment is not a validated minimum establishment, safe-staffing plan, or proof of available recruitment capacity.
- Check local approvals, contract terms, statutory employer costs and funding availability before using a proposal operationally.

## Template

Use `config/mwk_staffing_cost_template.csv` to record assumptions and sources before entering values into the dashboard.
