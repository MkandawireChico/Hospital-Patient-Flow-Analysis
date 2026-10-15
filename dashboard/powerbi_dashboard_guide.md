# Power BI Dashboard Guide

This guide describes a dashboard design for the synthetic patient-flow project. Any report built from these files should retain the synthetic-data disclaimer and must not present simulated results as real hospital performance.

## Data source and model

Load `data/processed/hospital_patient_flow_clean.csv` as the encounter fact table. Use `Visit_Date` for a calendar dimension, and use the encounter fields for department, priority, visit type, disposition, stage timestamps, waits, and quality flags. Keep `Total_Waiting_Time_Valid` as the wait KPI field so invalid timing rows remain excluded. Stage-specific waits can be blank when a visit did not use that service; do not treat those blanks as zero-delay observations.

For scenario views, load `results/scenario_comparison.csv` as a separate comparison table. Baseline stage, department, peak-period, and priority summaries are available in the other `results/baseline_*.csv` files. The generated decision summary is in `reports/baseline_decision_summary.md`.

## Suggested measures

```dax
Encounters = COUNTROWS(encounters)

Mean Valid Wait = AVERAGE(encounters[Total_Waiting_Time_Valid])

Median Valid Wait = MEDIAN(encounters[Total_Waiting_Time_Valid])

Long-Wait Encounters =
    CALCULATE(COUNTROWS(encounters), encounters[Long_Wait_Flag] = TRUE)

Long-Wait Share = DIVIDE([Long-Wait Encounters], [Encounters])

Mean Length of Stay = AVERAGE(encounters[Total_Length_of_Stay])
```

Use the generated `Long_Wait_Flag` rather than duplicating its threshold in a report measure. Use `DIVIDE` for ratios so an empty filter context does not produce a division error.

## Report views

- **Overview:** encounter volume, wait distribution, long-wait share, and department comparison.
- **Patient flow:** arrivals over time, department mix, disposition, and stage utilization.
- **Waiting and bottlenecks:** stage and department wait distributions, peak-period comparison, priority pattern, and observed laboratory/pharmacy stage waits.
- **Scenario comparison:** baseline and what-if upper-tail wait and long-wait-share metrics from the generated scenario table.

Useful filters include date, department, priority, visit type, disposition, and peak period. Keep the same filter behavior across report views and clearly distinguish visit length from waiting time.

## Interpretation

Use generated result tables for displayed values instead of embedding findings in report text. Laboratory stage contribution is the share of summed observed stage-wait minutes, not a decomposition of total wait. Peak-period and priority comparisons are descriptive. Scenario outputs are what-if calculations under simulation assumptions and do not establish causal effects or predict real operational outcomes.
