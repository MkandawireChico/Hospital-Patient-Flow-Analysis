# Interactive Dashboard User Guide

## Start the application

From the repository root:

```bash
python -m pip install -r requirements.txt
python -m patient_flow.cli run
streamlit run dashboard/app.py
```

The dashboard reads `data/processed/hospital_patient_flow_clean.csv`. If that file is missing, rerun the pipeline. After changing source data, rerun the pipeline and refresh the dashboard.

## Explore the cohort

Use the sidebar to filter by:
- Visit date range.
- Department.
- Priority.
- Visit type.
- Disposition.

All charts and KPI cards update for the filtered cohort. If a filter selection removes all records, clear or widen the selection.

## Dashboard sections

1. **Performance at a glance:** encounter count, mean, median, P90, and long-wait share.
2. **Waiting-time distribution:** histogram and box plot with the 60-minute threshold.
3. **Department bottlenecks:** department-level P90 waits with encounter volume context.
4. **Arrival pressure:** encounter count and P90 wait by arrival hour.
5. **Monthly trend:** median and P90 waiting-time trends by month.
6. **Stage delays:** P90 wait by recorded stage and each stage's share of summed observed stage-wait minutes.
7. **Priority comparison:** median and P90 by recorded priority.
8. **What-if scenarios:** baseline versus consultation wait-reduction scenarios.
9. **Bootstrap intervals:** optional 95% confidence intervals for median, P90, and long-wait share.
10. **MWK staffing budget planner:** enter additional FTE and verified monthly fully loaded staff cost per person. Results show monthly and selected-period budgets in MWK.
11. **Data-quality audit:** flagged quality issues, exclusions, and missing wait values.
12. **Filtered data export:** download the filtered valid cohort as CSV.

## Enter local costs in MWK

The staffing budget planner starts at zero intentionally. For each role, enter the additional FTE and fully loaded monthly cost per person in Malawi Kwacha. Select the budget period. The dashboard calculates:

`Monthly budget = Additional FTE × Monthly fully loaded cost per person`

`Period budget = Monthly budget × Number of months`

Use the MWK costing guide and assumptions template to record the source and effective date. The application does not fetch or convert exchange rates and does not supply local salary benchmarks.

## Download data

- Use **Download filtered encounter data (CSV)** to export the filtered cohort.
- Use **Download staffing budget (MWK CSV)** to export the entered budget assumptions and calculations.

## Important limitations

All records are synthetic. The fictional hospital is not a real facility. Scenario outputs are illustrative what-if calculations, not causal estimates or forecasts. Read [Analytical Methods](ANALYTICAL_METHODS.md) before interpreting subgroup or stage comparisons.
