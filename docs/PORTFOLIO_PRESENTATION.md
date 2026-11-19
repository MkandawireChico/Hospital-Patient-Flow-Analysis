# Portfolio Presentation Guide

## Live links

- **Interactive application:** https://hospital-operations-command-centre.streamlit.app/
- **Source repository:** https://github.com/MkandawireChico/Hospital-Patient-Flow-Analysis
- **Case study:** [Portfolio case study](PORTFOLIO_CASE_STUDY.md)
- **User guide:** [Dashboard user guide](DASHBOARD_USER_GUIDE.md)

## A focused five-minute walkthrough

Use this sequence when presenting the project to a recruiter, hiring manager, or technical interviewer.

| Time | Screen / feature | What to explain |
|---|---|---|
| 0:00–0:45 | Command Centre overview | Start with the operational question: where do waits accumulate, and how can teams inspect demand and capacity? Point out the encounter volume, median, mean, P90, and long-wait share together. |
| 0:45–1:30 | Department bottlenecks and arrival patterns | Explain why the median alone is insufficient when the wait distribution is right-skewed. Compare departments and inspect the hourly demand pattern. |
| 1:30–2:15 | Stage and priority analysis | Distinguish total waiting time from individual service-stage waits. Explain that a stage contribution share is not a decomposition of total patient wait. |
| 2:15–3:15 | Workforce & Roster Intelligence | Show staff establishment, job-title mix, the date-aligned roster, shift coverage, and demand-to-workforce views. Emphasise that job titles remain separate rather than being treated as interchangeable. |
| 3:15–4:15 | Capacity sensitivity | Select a workforce unit and shift, test additional FTE-hours, and explain the demand-events-per-scheduled-hour calculation. State clearly that this is a sensitivity analysis, not a queueing model or a prediction of wait reduction. |
| 4:15–5:00 | Role-based MWK budget planner | Demonstrate the role-level FTE and fully loaded monthly cost inputs, source/effective-date fields, monthly and period totals, and CSV export. Explain that costs are entered from locally verified sources rather than assumed salary benchmarks. |

## Suggested project explanation

> I built an end-to-end hospital operations analytics case study in Python. It includes a reproducible data-quality pipeline, distribution-aware patient-flow metrics, department and service-stage analysis, an interactive Streamlit dashboard, workforce roster analytics, a leakage-conscious long-wait classification baseline, and role-based staffing budget scenarios in Malawi Kwacha. I focused on making the assumptions visible, keeping job roles distinct, and ensuring the outputs can be inspected and exported.

## Selected results to discuss

The current repository findings report:

- 34,728 encounters in the valid waiting-time analysis cohort.
- Mean valid wait of 13.8 minutes, median of 0.0 minutes, and P90 of 48.2 minutes.
- 7.1% of valid waits above the project's 60-minute threshold.
- Laboratory stage-wait P90 of 182.9 minutes.
- Outpatient Department P90 total wait of 73.5 minutes.

Explain the skewed distribution and the difference between stage waits and total waits. These figures describe the case-study dataset; they are not estimates of performance at a real hospital.

## Engineering points worth highlighting

- Modular Python code separates cleaning, analysis, prediction, uncertainty, costing, capacity sensitivity, and workforce logic.
- Automated tests and Ruff lint checks run in GitHub Actions.
- The Streamlit application is deployed from the repository's `main` branch.
- CSV exports make the analysis inspectable outside the dashboard.
- MWK budget calculations retain cost-source and effective-date fields.
- Predictive features exclude triage priority to reduce the risk of target leakage.

## Questions to prepare for

**Why report the median and P90 together?**  
The median describes the centre of the distribution, while P90 makes the upper tail visible. In this dataset, the difference is substantial.

**Does the capacity sensitivity predict shorter waits?**  
No. It changes scheduled hours under explicit assumptions and recalculates demand events per scheduled hour. It does not model queues, service-time distributions, throughput, outcomes, or safe staffing.

**Where do staffing costs come from?**  
The planner expects the user to enter a locally verified fully loaded monthly cost, plus a source and effective date. It does not hard-code salary benchmarks.

**Can this be used to set safe staffing levels?**  
No. The roster and ratios are analytical demonstrations. A real staffing plan requires validated HR, leave, skill-mix, workload, policy, and clinical governance information.

## CV-ready project entry

**Hospital Operations Analytics & Workforce Planning | Python, pandas, Streamlit, Plotly, scikit-learn**

Built a deployed analytics command centre for patient-flow performance and workforce planning, including data-quality controls, waiting-time distribution analysis, bottleneck diagnostics, predictive modelling, shift-roster analytics, and role-based MWK budget sensitivity. Added automated tests, reproducible outputs, documentation, and downloadable reports.

