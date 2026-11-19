# Project Architecture

## High-level flow

```text
Synthetic raw CSV
      |
      v
patient_flow.io  ---> configuration (config/default.yaml)
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
      v
patient_flow.scenarios
  - explicit what-if wait transformations
      |
      v
results/*.csv and reports/*.md
```

## Main components

| Component | Responsibility |
|---|---|
| `config/default.yaml` | Synthetic hospital configuration and generation assumptions. |
| `src/patient_flow/io.py` | Paths and CSV loading/saving. |
| `src/patient_flow/cleaning.py` | Data cleaning and quality flags. |
| `src/patient_flow/flags.py` | Consistent parsing of boolean flags from native and CSV representations. |
| `src/patient_flow/features.py` | Temporal, wait-quality, and congestion features. |
| `src/patient_flow/analysis.py` | Descriptive summaries, cohort audit, and report exports. |
| `src/patient_flow/scenarios.py` | Transparent what-if transformations and comparisons. |
| `src/patient_flow/uncertainty.py` | Reproducible percentile-bootstrap confidence intervals. |
| `src/patient_flow/prediction.py` | Leakage-conscious logistic-regression baseline for long-wait classification. |
| `src/patient_flow/costing.py` | MWK-only staffing budget arithmetic. |
| `dashboard/app.py` | Interactive Streamlit and Plotly user interface. |
| `tests/` | Regression tests for analysis flags, cost arithmetic, and uncertainty estimates. |
| `.github/workflows/quality.yml` | Automated test and lint workflow. |

## Reproducibility

The project uses a configured random seed in `config/default.yaml`. The cleaning and analysis steps are run through the command-line interface:

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
