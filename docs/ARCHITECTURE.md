# Project Architecture

## High-level flow

```text
Generated case-study raw CSV
(created in the notebook; committed to data/raw)
      |
      v
patient_flow.io  ---> patient_flow.cli
      |
      v
patient_flow.cleaning
  - exact duplicate handling
  - department standardisation
  - impossible timestamp flags
  - negative wait flags
  - valid total-wait measure
      |
      v
data/processed/hospital_patient_flow_clean.csv
      |
      +-------------------------------+
      |                               |
      v                               v
patient_flow.analysis          Streamlit dashboard
  - cohort filtering             - interactive filters
  - descriptive KPIs             - Plotly charts
  - stage/department             - MWK budget planner
  - hourly/priority summaries    - bootstrap intervals
      |
      +------------------------------+
      |                              |
      v                              v
patient_flow.scenarios        patient_flow.prediction
  - explicit what-if             - pre-outcome features
    wait transformations         - logistic regression
      |                          - hold-out metrics
      +--------------+---------------+
                     |
                     v
           results/*.csv and reports/*.md

Separate application layers:
- `patient_flow.workforce` builds the staff roster and demand-to-workforce views.
- `patient_flow.capacity` and `patient_flow.costing` calculate explicit FTE-hour sensitivity and MWK budgets.
- `sql/build_database.py` builds the SQLite database from the processed CSV; `sql/queries/` contains the analysis queries.
```

## Main components

| Component | Responsibility |
|---|---|
| `config/default.yaml` | Reference simulation settings; currently not loaded by the notebook generator or CLI pipeline. |
| `src/patient_flow/io.py` | Paths and CSV loading/saving. |
| `src/patient_flow/simulation.py` | Compatibility placeholder only; raw-data generation currently lives in the notebook. |
| `src/patient_flow/cleaning.py` | Data cleaning and quality flags. |
| `src/patient_flow/workforce.py` | Generated staff directory, date-aligned roster, workforce demand mapping and role establishment views. |
| `src/patient_flow/capacity.py` | Unit/shift capacity sensitivity using additional FTE-hours and MWK cost assumptions. |
| `src/patient_flow/flags.py` | Consistent parsing of boolean flags from native and CSV representations. |
| `src/patient_flow/features.py` | Temporal, wait-quality, and congestion features. |
| `src/patient_flow/analysis.py` | Descriptive summaries, cohort audit, and report exports. |
| `src/patient_flow/scenarios.py` | Transparent what-if transformations and comparisons. |
| `src/patient_flow/uncertainty.py` | Reproducible percentile-bootstrap confidence intervals. |
| `src/patient_flow/prediction.py` | Leakage-conscious logistic-regression baseline for long-wait classification. |
| `src/patient_flow/costing.py` | MWK-only staffing budget arithmetic. |
| `dashboard/app.py` | Patient-flow Streamlit and Plotly command centre. |
| `dashboard/pages/2_Staff_Workforce.py` | Workforce, roster, role coverage, capacity sensitivity and MWK budget page. |
| `sql/` | SQLite schema, reproducible database builder and analytical SQL queries. |
| `tests/` | Regression tests for analysis, flags, prediction, workforce, costing and uncertainty. |
| `.github/workflows/quality.yml` | Automated test and lint workflow. |

## Reproducibility

The encounter source is generated in the exploratory notebook and committed as `data/raw/hospital_patient_flow_synthetic.csv`. The current CLI does not regenerate that raw source and does not read `config/default.yaml`; it starts from the committed CSV. The YAML file is reference documentation, not an active source of runtime parameters. The cleaning and analysis steps are run through the command-line interface:

```bash
python -m patient_flow.cli run
python -m patient_flow.cli analyse
```

The dashboard consumes the processed dataset and does not mutate source files. Results and reports are written to the repository's `results/` and `reports/` directories.

## Design principles

- Keep synthetic data clearly labelled.
- Separate data preparation, analysis, scenario assumptions, and presentation.
- Keep missing observations distinct from zero.
- Preserve quality flags and report exclusions.
- Use tail-sensitive metrics alongside mean and median.
- Make scenario assumptions visible and avoid causal language.
- Keep financial inputs local, editable, traceable, and denominated in MWK.
