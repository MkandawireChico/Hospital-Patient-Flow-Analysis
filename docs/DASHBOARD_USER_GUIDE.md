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
5. **Department/hour heatmap:** median valid wait by department and arrival hour, with encounter counts on hover.
6. **Monthly trend:** median and P90 waiting-time trends by month.
7. **Stage delays:** P90 wait by recorded stage and each stage's share of summed observed stage-wait minutes.
8. **Priority comparison:** median and P90 by recorded priority.
9. **What-if scenarios:** baseline versus consultation wait-reduction scenarios.
10. **Bootstrap intervals:** optional 95% confidence intervals for median, P90, and long-wait share.
11. **Long-wait classification:** exploratory logistic-regression model with hold-out metrics and diagnostic charts.
12. **MWK staffing budget planner:** additional FTE, verified monthly staff costs, source and effective date, and monthly/period totals in MWK.
13. **Data-quality audit:** flagged quality issues, exclusions, and missing wait values.
14. **Filtered data export:** download the filtered valid cohort as CSV.

### Long-wait classification

Toggle **Train and evaluate the long-wait model** to fit an exploratory logistic-regression classifier on the current filtered cohort. It shows hold-out ROC AUC, average precision, recall, precision, F1, the ROC curve, confusion matrix, and the largest encoded coefficients. The model uses only department, visit type, and arrival-time features. Triage priority is excluded because it may be assigned after the waiting-time clock has started. If the filtered cohort is too small or contains only one target class, the dashboard explains why evaluation is unavailable.

The classifier is an exploratory synthetic-data demonstration, not a clinical decision tool. See [Analytical Methods](ANALYTICAL_METHODS.md) for feature exclusions, leakage safeguards, and validation requirements.

## Enter local costs in MWK

The staffing budget planner starts at zero intentionally. For each role, enter the additional FTE, fully loaded monthly cost per person in Malawi Kwacha, the cost source/payroll reference, and its effective date. Select the budget period. Non-zero cost assumptions without a source and valid effective date are flagged as provisional. The dashboard calculates:

`Monthly budget = Additional FTE × Monthly fully loaded cost per person`

`Period budget = Monthly budget × Number of months`

Use the MWK costing guide and assumptions template to record the source and effective date. The application does not fetch or convert exchange rates and does not supply local salary benchmarks.

## Download data

- Use **Download filtered encounter data (CSV)** to export the filtered cohort.
- Use **Download staffing budget (MWK CSV)** to export the entered budget assumptions and calculations.

## Important limitations

All records are synthetic. The fictional hospital is not a real facility. Scenario outputs are illustrative what-if calculations, not causal estimates or forecasts. Read [Analytical Methods](ANALYTICAL_METHODS.md) before interpreting subgroup or stage comparisons.
