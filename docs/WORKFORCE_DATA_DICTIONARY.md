# Workforce register

This register contains 40 staff profiles created for the Chilungamo District Hospital case study. Names, identifiers, employment dates and role assignments are generated case-study values, not employee records. The register is for workforce analytics demonstrations, not live HR administration.

## Fields

- `Staff_ID`: stable synthetic identifier
- `Staff_Name`: invented name for portfolio demonstration
- `Job_Title`, `Department`, `Staff_Category`: simulated role and organisational placement
- `Qualification`: illustrative label, not credential verification
- `Employment_Type`, `Employment_Status`, `Start_Date`: simulated employment attributes

## Governance

Do not add real names, phone numbers, addresses, payroll identifiers, or other personal data to this public portfolio dataset. Staff pay is intentionally not stored in this register. Staffing costs must be entered separately from locally verified payroll or HR sources in MWK, following [the costing guide](MWK_COSTING_GUIDE.md).


| Field | Definition |
|---|---|
| `Demand_Events` | Count of encounter arrivals or recorded service-stage events mapped to a workforce unit |
| `Demand_Basis` | Source field/basis used to construct the demand count |
| `Demand_Shift_Basis` | Documents that service-stage demand is grouped by patient arrival shift as a proxy |
| `Staff_On_Duty` | Unique staff scheduled in the roster for the date, workforce unit and shift |
| `Scheduled_Hours` | Sum of rostered hours for the matched group |
| `Demand_Events_Per_Staff` | Demand events divided by rostered staff; descriptive workload indicator |
| `Demand_Events_Per_Scheduled_Hour` | Demand events divided by scheduled staff-hours; descriptive workload indicator |
