# Workforce & roster analytics

The project includes a 40-person fictional staff directory and a deterministic 28-day illustrative roster. The directory spans clinical, nursing, diagnostics, pharmacy, administration, community-health and support roles. The roster assigns DAY / EVENING / NIGHT shifts to selected 24-hour departments and daytime shifts to other units, with staggered rest days.

Run `python -m patient_flow.workforce` from the repository root to regenerate `data/reference/staff_roster_synthetic.csv`. The Streamlit page at `dashboard/pages/2_Staff_Workforce.py` displays staff mix, establishment by department, shift coverage, scheduled hours, the staff register and roster downloads.

## Important modelling limitations

- Every staff name, ID, qualification label, employment date and roster entry is fictional.
- The roster is a demonstration dataset, not a validated duty rota, labour-law check, clinical skill-mix assessment, or safe-staffing recommendation.
- The simple schedule does not model leave, sickness, overtime, public holidays, fatigue, handovers, minimum skill mix, or individual contractual hours.
- No salaries are included. Use locally verified payroll assumptions in MWK through the staffing-cost planner; do not treat illustrative role counts as a funded establishment.
- Never add real employee personal data to this public repository.
