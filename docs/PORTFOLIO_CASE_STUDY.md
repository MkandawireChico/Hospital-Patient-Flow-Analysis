# Portfolio Case Study: Hospital Patient Flow Analytics

## Executive summary

This project demonstrates how a data scientist can turn operational event data into an auditable decision-support workflow. Using a structured Malawi-inspired district-hospital case study, it examines waiting-time patterns across registration, triage, consultation, laboratory, and pharmacy-related stages.

The work combines Python data preparation, data-quality controls, descriptive statistics, leakage-conscious predictive modelling, scenario analysis, interactive visualisation, MWK budget planning, and reproducible reporting. The results are simulated examples for a portfolio; they are not evidence about any real hospital.

## Business question

**Where do patients lose time in the hospital pathway, which groups experience the longest waits, and how could managers investigate possible operational improvements?**

The project deliberately separates three questions:

1. **Measurement:** What does the available encounter data say about waits and patient flow?
2. **Diagnosis:** Which stages, departments, periods, or priority groups show the strongest delay signals?
3. **Exploration:** How would selected wait-reduction assumptions change the distribution of simulated waiting times?

## Data and governance

The case study uses generated encounter records and an invented workforce register to demonstrate a complete analytics workflow. The hospital is a constructed case-study setting; no identifiable patient or employee records are included. The analysis is designed to demonstrate methods and operational reasoning, not to report the performance of a named facility.
- Missing stage waits are retained as missing when a service was not used or no value was recorded; they are not automatically treated as zero.
- Records with invalid timestamp or negative-wait evidence are excluded from wait KPIs, while the audit records the excluded count.
- The 60-minute long-wait threshold is an explicit analytical convention, not a clinical standard.

The current repository snapshot contains 35,418 raw synthetic records, 35,082 processed records, and 34,728 records in the valid analysis cohort. The generated report should be rerun after any data or pipeline changes.

## Selected case-study findings

| Measure | Result | Interpretation |
|---|---:|---|
| Median total valid wait | 0.0 min | At least half of valid simulated waits are at or below zero minutes; this highlights a highly skewed distribution and the need to inspect the median alongside tail metrics. |
| Mean total valid wait | 13.8 min | The mean is pulled upward by longer waits. |
| 90th percentile total wait | 48.2 min | One in ten valid waits is above approximately this level. |
| Share above 60 minutes | 7.1% | A minority of encounters experience long waits under the project's chosen threshold. |
| Laboratory stage-wait P90 | 182.9 min | Laboratory waits are a strong upper-tail signal in the simulated stage data. |
| Laboratory share of summed observed stage waits | 68.7% | This is a share of summed stage-wait minutes, not a decomposition of total waiting time. |
| Highest department P90 total wait | Outpatient Department: 73.5 min | Department comparisons should be interpreted with encounter volume and case mix in view. |

The gap between the median and P90 is important: a single average would hide the right-skewed tail. Stage and department rankings are useful for prioritising investigation, but do not establish the cause of delay.

## Scenario analysis

The current scenario module compares a baseline with two transparent what-if transformations:

- A 20% reduction in consultation wait for Routine encounters.
- A 20% reduction in consultation wait for Urgent/Emergency encounters during the defined peak period.

In the current simulated output, the Routine consultation-reduction scenario lowers P90 total valid wait from 48.2 to 41.4 minutes and reduces the share above 60 minutes by 2.10 percentage points.

These calculations assume the targeted component can be reduced by the stated amount and that other components remain unchanged. They are exploratory comparisons, not forecasts, causal estimates, or recommendations to change hospital operations. A real intervention would require operational validation, resource constraints, safety review, and evaluation using appropriate pre/post or experimental designs.

## Analytical workflow

1. **Ingest:** load the raw synthetic encounter table.
2. **Clean:** remove exact duplicates, standardise known department aliases, and retain explicit data-quality flags.
3. **Validate:** identify impossible timestamp sequences and negative waits; create a valid-wait measure for analysis.
4. **Engineer features:** derive arrival hour, peak-period indicator, long-wait flag, congestion flag, and month.
5. **Analyse:** calculate mean, median, P90, long-wait share, stage-level summaries, department summaries, hourly patterns, peak/off-peak comparisons, and priority comparisons.
6. **Model scenarios:** apply explicit reductions to targeted consultation waits and compare distributional KPIs on the same valid cohort.
7. **Communicate:** export CSV result tables, a generated Markdown decision summary, and an interactive Plotly/Streamlit dashboard.

## Interactive command centre

The Streamlit application supports:

- Date, department, priority, visit-type, and disposition filters.
- KPI cards for encounter count, mean, median, P90, and long-wait share.
- Waiting-time distribution and threshold marker.
- Department-level P90 comparisons with encounter volume context.
- Hourly arrivals alongside upper-tail waiting time.
- Monthly median/P90 trend and department-by-arrival-hour heatmap with encounter-count context.
- Stage-level wait comparisons and priority breakdowns.
- Baseline versus what-if scenario charts.
- Data-quality audit counts and filtered CSV export.

Run it locally:

```bash
python -m pip install -r requirements.txt
python -m patient_flow.cli run
streamlit run dashboard/app.py
```

## Predictive modelling

The dashboard includes an optional logistic-regression baseline for classifying encounters that exceed the 60-minute long-wait threshold. It uses a stratified train/test split and reports ROC AUC, average precision, precision, recall, F1, a confusion matrix, an ROC curve, and encoded feature coefficients.

Predictors are limited to encounter descriptors available at or near registration and arrival-time features (department, visit type, arrival hour, day of week, and month where available). Triage priority is excluded because it may be assigned after the waiting-time clock has started. Wait components, total waiting time, length of stay, and disposition are deliberately excluded from the feature matrix to reduce target leakage. Coefficients are associations in the fitted model, not causal effects.

This is an exploratory baseline on the case-study dataset. It has not been externally validated, calibrated for a real facility, or assessed for fairness or clinical utility. It must not be used to prioritise real patients or make clinical decisions.

## Local budget planning in Malawi Kwacha (MWK)

The interactive dashboard includes an incremental staffing budget planner denominated entirely in **MWK**. Users enter:

- Additional full-time-equivalent staff by role.
- Verified or explicitly assumed fully loaded monthly cost per staff member.
- The budget period in months.

The planner calculates monthly and period totals, visualises the allocation by role, and exports the assumptions and results to CSV. It does not convert USD, fetch exchange rates, or invent salary benchmarks. The zero-value starting inputs are deliberate: local payroll scales, allowances, pension contributions, and employer on-costs should be confirmed with an appropriate Malawi source before a budget is treated as decision-ready.

The dashboard does not assign a monetary value to patient waiting time. Monetising patient time, clinical harm, or delayed care would require a defensible local valuation method and stakeholder approval; a speculative monetary figure would be misleading.

## Statistical uncertainty

The dashboard can estimate 95% percentile-bootstrap confidence intervals for the median wait, P90 wait, and share of waits above 60 minutes. The calculation uses 500 bootstrap replicates and a reproducible sample of up to 5,000 valid waits for responsiveness. These intervals describe sampling variation in the selected analysis cohort only. They do not represent uncertainty in the simulation design, omitted variables, or the effect of a real-world intervention.

## Technical skills demonstrated

- Python package structure and command-line execution.
- pandas-based data cleaning and feature engineering.
- Explicit data-quality flags and auditability.
- Distribution-aware descriptive statistics.
- Scenario-based operational analysis.
- Interactive charts and dashboard development with Plotly and Streamlit.
- scikit-learn preprocessing pipelines, logistic regression, and held-out classification evaluation.
- Automated tests and linting.
- Reproducible outputs and decision-focused documentation.
- Responsible communication of simulated data and analytical limitations.

## Limitations and next steps

The current project is a strong demonstration of the analytics workflow, but several extensions would make it more decision-ready:

1. Add bootstrap confidence intervals for P90 and long-wait shares.
2. Evaluate whether observed group differences persist after adjusting for department, priority, visit type, and arrival time.
3. Model arrival volume and service capacity explicitly, rather than changing wait values directly.
4. Test scenario assumptions across a range of intervention sizes and staffing constraints.
5. Add a database-backed analytical layer and automated data validation.
6. Validate dashboard accessibility, performance, and behaviour on larger datasets.
7. If real data ever becomes available, establish governance, de-identification, data-sharing approval, and clinical/operational review before analysis.

## How to present this project in a job application

A concise, accurate description:

> Built a reproducible hospital patient-flow analytics project using Python, pandas, Plotly, and Streamlit. Developed a data-quality pipeline, distribution-based waiting-time KPIs, department and stage bottleneck analysis, and transparent what-if scenarios. Delivered an interactive dashboard, auditable exports, tests, and documentation using a fully synthetic dataset.

Do not describe the simulated results as findings from a real hospital or claim that the scenarios prove an intervention would reduce waiting time in practice.
