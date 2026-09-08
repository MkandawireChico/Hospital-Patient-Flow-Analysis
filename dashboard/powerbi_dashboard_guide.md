# Power BI Dashboard — Implementation Guide

**Status: not yet built.** This is a structured implementation plan for building the dashboard in Power BI Desktop, written from the actual fields and findings in `data/processed/hospital_patient_flow_clean.csv`. All data is synthetic (see the project README) — any screenshots added after building should carry the same notice.

---

## 1. Data source

Import `data/processed/hospital_patient_flow_clean.csv`, or connect to `sql/hospital_patient_flow.db` (three related tables) via an ODBC/SQLite connector if the goal is to practice a database-sourced model.

## 2. Data model

```
Calendar (date dimension) ---1:*--- encounters (fact) ---*:1--- departments
                                          |
                                          *:1
                                          |
                                       doctors
```

Add a **Calendar** table related to `Visit_Date`, marked as a Date Table — this is what makes time-intelligence DAX (`SAMEPERIODLASTYEAR`, rolling averages, etc.) work correctly rather than operating on the raw date column directly.

## 3. Measures (DAX)

```dax
Total Patients = COUNTROWS(encounters)

Average Waiting Time = AVERAGE(encounters[Total_Waiting_Time_Valid])

Median Waiting Time = MEDIAN(encounters[Total_Waiting_Time_Valid])

Average Length of Stay = AVERAGE(encounters[Total_Length_of_Stay])

Long Wait Patients = CALCULATE(COUNTROWS(encounters), encounters[Long_Wait_Flag] = TRUE)

Long Wait Rate = DIVIDE([Long Wait Patients], [Total Patients])

Peak Hour = 
    CALCULATE(
        SELECTEDVALUE(encounters[Arrival_Hour]),
        TOPN(1, SUMMARIZE(encounters, encounters[Arrival_Hour], "n", COUNTROWS(encounters)), [n], DESC)
    )

Average Consultation Duration = AVERAGE(encounters[Consultation_Duration])

Average Satisfaction = AVERAGE(encounters[Patient_Satisfaction_Score])
```

**Why `DIVIDE()` instead of `/`:** returns `BLANK()` rather than erroring when a filter/slicer selection produces a zero-row context — common once Department/Age Group/Priority slicers are added.

**Why `MEDIAN()` gets its own KPI card, not just `AVERAGE()`:** the notebook found waiting time is heavily right-skewed (median 0 minutes, mean 13.75 minutes, driven by a minority of very congested periods) — showing only the mean would overstate the "typical" patient's experience. Both numbers earn a place on Page 1.

## 4. Pages

### Page 1 — Executive Overview

KPI cards: `[Total Patients]`, `[Average Waiting Time]`, `[Median Waiting Time]`, `[Average Length of Stay]`, `[Long Wait Patients]`, `[Peak Hour]`, plus a card showing the highest-congestion department (Outpatient Department, per the notebook).

Visuals: patient volume trend (line), patient volume by department (bar), waiting-time overview (the median-vs-mean gap deserves its own visual, not just two cards), department performance table.

### Page 2 — Patient Flow

Arrival patterns by hour (bar), patient flow by department (bar), visit type breakdown (donut), admission vs. discharge vs. referred-out (donut), daily trend (line, 7-day rolling average) and monthly trend (bar).

### Page 3 — Waiting Time & Bottlenecks

Average and median wait by department (bar), long-wait percentage by department (bar), waiting time by priority level (bar — should visibly show Emergency < Urgent < Routine, confirming triage is working), queue size vs. waiting time (scatter — this is the strongest visual in the whole dashboard, given the 0.92 correlation found in the notebook), laboratory-related delay (a dedicated card/chart, since lab wait time averages far higher than general queueing wait — see Section 6 below), pharmacy-related delay.

### Page 4 — Operational Performance

Department ranking (table, replicating the SQL `overall_attention_score` composite ranking), length of stay by department (bar), patient throughput (patients per day, line), peak congestion periods (heatmap: day-of-week x hour), long-wait patient list (table, filterable), and a text box listing the bottlenecks actually found (Section 6).

## 5. Filters / slicers

Date range, Department, Age Group, Sex, Visit Type, Priority Level, Admission Status — all from the Calendar/encounters tables, applied hospital-wide via a single interaction model rather than per-visual.

## 6. Findings that belong directly on the dashboard, not just in the README

Two results from the notebook are strong enough that they should be callouts on the dashboard itself, not left for someone to discover in a PDF report:

- **The Laboratory is a bigger source of delay than department queueing itself.** Average `Laboratory_Wait_Time` (~80–85 minutes across departments) is several times larger than the general registration/triage/consultation queueing delay that Page 3's department comparison shows. A dashboard that only shows "waiting time by department" without a specific lab-delay callout would miss the single largest driver of total visit time for the ~44% of patients who need a lab test.
- **Outpatient Department is the clear priority for intervention** — it has the highest average wait, the highest long-wait rate (14.9%), and ranks worst overall on the SQL composite ranking, despite Chronic Care and TB/HIV Clinic having *longer* average length of stay. These are different problems (OPD has a queueing/congestion problem; Chronic Care and TB/HIV have a naturally longer clinical process) and the dashboard should let a viewer tell them apart rather than conflating "long wait" and "long visit."

## 7. Build order

1. Import data, build the Calendar table and relationships
2. Write the core measures (Section 3)
3. Build Page 1's KPI cards and volume charts — sense-check every number against the notebook's printed output
4. Build Pages 2–4
5. Add the Section 6 callouts explicitly (a text box or dedicated KPI card each) — don't leave them implicit in a chart someone has to interpret correctly
6. Add slicers last
7. Screenshot into a `visuals/dashboard/` folder and link from the main README
