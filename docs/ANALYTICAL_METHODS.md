# Analytical Methods and Metric Definitions

## Analysis population

The baseline analysis uses the processed synthetic encounter dataset. Rows with impossible timestamp flags, negative-wait flags, or negative values in measured wait columns are excluded from wait analysis. Missing total waits are not treated as zero: such encounters can remain in volume and stage-level summaries, while wait-specific metrics omit missing observations.

The audit records the input row count, exclusions, retained cohort size, and missing total waits. A row may be excluded because more than one quality issue is present; the exclusion count is a count of unique excluded rows, not a sum of issue categories.

## Waiting-time metrics

- **Mean:** arithmetic average of non-missing valid wait observations.
- **Median:** 50th percentile of non-missing valid wait observations.
- **P90:** 90th percentile; approximately 10% of observations lie above this value.
- **Long-wait share:** percentage of non-missing valid waits strictly greater than 60 minutes.
- **Stage P90:** 90th percentile of the recorded wait column for that stage.
- **Stage contribution:** each stage's sum of observed wait minutes divided by the sum across all included stage columns. This is not a decomposition of total patient waiting time because stage observations may be missing, overlap, or represent different pathways.
- **Department comparison:** the same total-wait statistics grouped by recorded department. These are descriptive comparisons and may reflect differences in patient mix, service pathways, and volume.

The 60-minute threshold is a project convention for exploration. It is not a clinical triage rule or an externally validated service standard.

## Time-of-day analysis

The repository defines the Peak period as arrivals at 08:00 or 09:00, consistent with the current synthetic data configuration. The label is a grouping feature, not evidence that those hours cause delays. Arrival volume and wait metrics are displayed together to help identify periods for further investigation.

## Bootstrap confidence intervals

When requested, the dashboard uses a percentile bootstrap with 500 resamples. A reproducible sample of up to 5,000 valid wait observations is used for large filtered cohorts. The dashboard reports 95% intervals for the median, P90, and long-wait share.

These intervals quantify sampling variation conditional on the selected synthetic cohort and resampling procedure. They do not capture uncertainty in the synthetic data-generating assumptions, selection bias, measurement error, or generalisation to a real hospital.

## What-if scenarios

The scenario module applies a 20% reduction to the recorded consultation wait for:
1. Routine encounters; or
2. Urgent/Emergency encounters arriving during the defined Peak period.

The same reduction is subtracted from the total valid wait, with other components held fixed. Scenario outputs are recalculated on the same cleaned cohort as baseline.

This is a transparent arithmetic sensitivity exercise. It does not model staff scheduling, queue dynamics, service capacity, patient safety, downstream congestion, or behavioural adaptation. It is not a causal estimate, forecast, or implementation recommendation.

## Long-wait classification model

The optional predictive baseline defines the target as a valid total wait strictly greater than 60 minutes. It uses a stratified random hold-out split and a class-weighted logistic regression. Numeric arrival-time features are median-imputed and standardised; categorical encounter descriptors are imputed and one-hot encoded.

Eligible features are department, visit type, arrival hour, arrival weekday, and arrival month where available. Triage priority is excluded because it may be assigned after the waiting-time clock has started. Total wait, stage waits, length of stay, disposition, and post-outcome variables are excluded to reduce leakage. The dashboard reports ROC AUC, average precision, precision, recall, F1, a confusion matrix, an ROC curve, and logistic-regression coefficients.

This is an exploratory baseline, not a deployment-ready risk score. A real-world application would require temporal and external validation, calibration, subgroup performance and fairness analysis, clinical governance, and a clear human decision process. The model must not be used for clinical triage or patient prioritisation.

## Cost analysis

The dashboard's staffing budget planner uses user-supplied additional FTE counts and fully loaded monthly staff costs, denominated only in MWK. It calculates monthly and selected-period incremental staffing costs.

No salary benchmarks or exchange rates are embedded. Users should document source, effective date, allowances, pension, statutory contributions, and other employer on-costs. The tool does not monetise waiting time or clinical harm.

## Recommended interpretation

Use the dashboard to formulate operational questions, not to make automatic staffing decisions. Before applying the methods to real data, validate definitions with hospital teams, confirm data completeness and timestamp quality, assess case mix, and obtain all required governance approvals.
