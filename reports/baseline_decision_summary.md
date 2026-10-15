# Baseline Decision Summary

> All records and findings are generated from a synthetic hospital simulation. These results describe the simulation assumptions, not real hospital performance.

## Where patients lose time

Among 34,728 usable total-wait observations, the median total valid wait is 0.0 minutes and the p90 is 48.2 minutes.
Laboratory has the highest observed stage-wait p90 at 182.9 minutes; its share of summed observed stage waits is 68.7%. Stage contribution is each stage's share of summed observed stage-wait minutes, not a decomposition of the total-wait KPI.

## Top bottlenecks

- Stage: Laboratory, p90 182.9 minutes (n=15358)
- Department: Outpatient Department, p90 73.5 minutes (n=14002)
- Department: Maternal Health, p90 50.6 minutes (n=3360)
- Stage: Consultation, p90 44.2 minutes (n=34728)
- Department: Unknown, p90 39.0 minutes (n=23)

Outpatient Department has the highest department-level p90 total wait at 73.5 minutes.

## Peak-period pattern

The median total wait is 14.9 minutes during the recorded Peak period and 0.0 minutes during Non-Peak.
Peak labels follow the existing dataset feature and are not inferred as a causal effect.
By recorded priority: Emergency: median 0.0 minutes, p90 10.8 minutes; Routine: median 0.6 minutes, p90 54.4 minutes; Urgent: median 0.0 minutes, p90 41.6 minutes.

## Scenario comparison

The comparison ranks simulated p90 and long-wait share because the baseline median is 0.0 minutes; median-only improvement is uninformative here.
**Consultation wait reduction** has the lowest p90 at 41.4 minutes (-6.8 minutes versus baseline) and a long-wait share change of -2.10 percentage points.
Consultation wait reduction lowers Routine consultation waits by 20%; peak priority fast-track lowers Urgent/Emergency consultation waits during Peak by 20%.
Both apply to the same valid analysis records. These are what-if calculations, not causal evidence or forecasts.

## Data handling and limitations

The analysis excluded 354 rows with invalid timing or negative wait evidence.
A further 0 analysis rows have no valid total wait and do not contribute to wait percentiles.
Long wait means a total valid wait above 60 minutes. Laboratory and pharmacy waits are observed only for records with those stages; stage shares reflect observed stage-wait values only.
Data cleaning and scenario rules may change results; all findings remain conditional on this synthetic dataset and its simulation assumptions.
