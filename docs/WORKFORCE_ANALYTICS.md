# Workforce and roster analytics

The workforce module adds an operational planning layer to the patient-flow analysis. It includes a 40-person staff directory, a reproducible date-aligned shift roster, department and role composition, shift coverage, scheduled hours, and a patient-arrival workload comparison.

## Analytical views

- Workforce establishment by department and staff category
- Daily scheduled headcount by shift
- Encounter arrivals by department and shift
- Encounters per rostered staff member
- Encounters per scheduled staff-hour
- Daily department arrival intensity
- Downloadable directory, roster and demand-coverage tables

Run `python -m patient_flow.workforce` from the repository root to regenerate `data/reference/staff_roster_synthetic.csv`. The Streamlit page at `dashboard/pages/2_Staff_Workforce.py` builds the roster over the encounter date range and aligns arrivals to DAY (07:00–14:59), EVENING (15:00–22:59) and NIGHT (23:00–06:59) shifts.

## Interpreting workload measures

Encounters per rostered staff member and encounters per scheduled staff-hour are workload indicators. They are useful for comparing patterns across departments and shifts, but they do not adjust for patient acuity, service type, skill mix, non-clinical duties, leave, handovers, or differences in care complexity. They must not be interpreted as clinical productivity scores, staffing thresholds or safe-staffing recommendations. A real staffing model would require validated establishment data, role-specific activity, local labour rules and clinical governance.

## Data governance

Staff identities, identifiers, qualifications, employment dates and roster assignments are generated for this case study. They are not real employee records. No payroll values or contact details are stored. Budget assumptions must be entered separately from locally verified payroll or HR sources in MWK, following [the costing guide](MWK_COSTING_GUIDE.md). Never add identifiable employee information to this public repository.


## Demand-to-workforce mapping

The workforce analysis separates three kinds of demand rather than assuming every service belongs to the encounter's recorded department:

- Clinical departments use encounter counts grouped by the encounter department.
- Laboratory and Pharmacy use non-null `Laboratory_Wait_Time` and `Pharmacy_Wait_Time` records as observed stage-use event counts.
- Administration uses non-null registration-wait records as a registration workload proxy.

Service-stage events are grouped by the patient's arrival date and arrival shift because the dataset does not consistently provide service-start timestamps for laboratory and pharmacy. This is a timing proxy, not proof that the event was handled by the staff rostered on that shift. The dashboard labels this explicitly. A zero wait is counted as a recorded service event; a missing stage value is not.

The resulting events-per-rostered-person and events-per-scheduled-hour measures are descriptive workload indicators. They do not estimate throughput capacity, staff productivity, clinical acuity, minimum safe staffing, or causal effects of adding staff. Facilities/support roles are not assigned patient-service demand in this version.
