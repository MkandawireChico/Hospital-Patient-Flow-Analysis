# Deploy the live dashboard

The Streamlit dashboard can be hosted on Streamlit Community Cloud and connected directly to this public GitHub repository. Once connected, commits to the selected branch are automatically reflected in the app.

## App settings

- **Repository:** `MkandawireChico/Hospital-Patient-Flow-Analysis`
- **Branch:** `main`
- **Main app file:** `dashboard/app.py`
- **Python:** 3.11 (matches the project's automated quality-check environment)
- **Secrets:** none required for the current case-study dashboard

The processed encounter dataset and staff directory are committed under `data/`. The workforce page creates its roster from the staff directory when it first loads, so a pre-generated roster file is not required.

## First deployment

1. Open [Streamlit Community Cloud](https://share.streamlit.io/) and sign in with GitHub.
2. Connect/authorize the GitHub account that owns this repository. The repository owner must grant Streamlit access; do this only on the official Streamlit site.
3. Choose **Create app** and select **Yup, I have an app**.
4. Enter the repository, branch and main file path listed above.
5. Choose an available memorable subdomain, for example `hospital-operations-command-centre`.
6. In **Advanced settings**, select Python 3.11. No secrets need to be entered for this project.
7. Select **Deploy** and wait for the build to finish.

Streamlit will provide the final public `.streamlit.app` URL after deployment. Do not advertise a URL until Streamlit confirms the app is live.

## Post-deployment smoke test

Open the public URL and check:

- The main Patient Flow page loads without a missing-data or import error.
- Date and department filters update the KPIs and charts.
- The Workforce & Roster page loads, creates its roster and displays the 40-person directory.
- The role-based budget planner accepts additional FTE and MWK cost inputs, updates totals, and downloads its CSV.
- The browser can refresh and navigate between both dashboard pages.

If a build fails, open the app's **Manage app** page in Community Cloud and inspect the deployment logs. Resolve the first Python dependency, import, or missing-file error shown there, then push the fix to `main`; Community Cloud redeploys from GitHub.

## Operational notes

- The app is a public portfolio demonstration. Do not add real patient-identifiable data, confidential payroll records, credentials or private operational information.
- Workforce and encounter records are case-study data. The dashboard is not a clinical decision tool or a validated safe-staffing system.
- Community Cloud's free hosting is subject to its current resource and usage limits. See the [official deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app) for current instructions and platform details.
