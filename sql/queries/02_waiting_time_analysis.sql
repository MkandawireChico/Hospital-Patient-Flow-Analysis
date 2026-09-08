-- ============================================================================
-- 02_waiting_time_analysis.sql
-- Average/median waiting time, long-wait patients, by priority/age/department.
-- ============================================================================

-- Q4: Average waiting time by department.
-- Business purpose: the core department scorecard metric.
SELECT
    "Department",
    ROUND(AVG("Total_Waiting_Time_Valid"), 2) AS avg_wait_minutes,
    COUNT(*) AS patients
FROM encounters
WHERE "Department" != 'Unknown' AND "Total_Waiting_Time_Valid" IS NOT NULL
GROUP BY "Department"
ORDER BY avg_wait_minutes DESC;


-- Q5: Median waiting time (SQLite has no built-in MEDIAN, so it's computed
-- via a window-function percentile rank).
-- Business purpose: waiting time is right-skewed (confirmed in the Python
-- notebook), so the median is a more honest "typical" figure than the mean,
-- which a few very long waits can pull upward.
WITH ranked AS (
    SELECT
        "Department", "Total_Waiting_Time_Valid",
        PERCENT_RANK() OVER (PARTITION BY "Department" ORDER BY "Total_Waiting_Time_Valid") AS pct_rank
    FROM encounters
    WHERE "Department" != 'Unknown' AND "Total_Waiting_Time_Valid" IS NOT NULL
)
SELECT "Department", MIN("Total_Waiting_Time_Valid") AS approx_median
FROM ranked
WHERE pct_rank >= 0.5
GROUP BY "Department"
ORDER BY approx_median DESC;


-- Q6: Patients waiting more than 60 minutes.
-- Business purpose: this is literally the dashboard's named threshold —
-- a hospital administrator needs both the count and the rate.
SELECT
    "Department",
    SUM("Long_Wait_Flag") AS long_wait_patients,
    COUNT(*) AS total_patients,
    ROUND(SUM("Long_Wait_Flag") * 1.0 / COUNT(*), 4) AS long_wait_rate
FROM encounters
WHERE "Department" != 'Unknown'
GROUP BY "Department"
ORDER BY long_wait_rate DESC;


-- Q10: Waiting time by priority level, with a CASE-based readable label.
-- Business purpose: confirms triage is actually working as intended —
-- higher-priority patients should wait less, not just be labeled differently.
SELECT
    "Priority_Level",
    CASE
        WHEN AVG("Total_Waiting_Time_Valid") < 5  THEN 'Fast'
        WHEN AVG("Total_Waiting_Time_Valid") < 15 THEN 'Moderate'
        ELSE 'Slow'
    END AS wait_category,
    ROUND(AVG("Total_Waiting_Time_Valid"), 2) AS avg_wait_minutes
FROM encounters
WHERE "Total_Waiting_Time_Valid" IS NOT NULL
GROUP BY "Priority_Level"
ORDER BY avg_wait_minutes;


-- Q11: Waiting time by age group.
-- Business purpose: checks whether any age group (e.g. elderly patients)
-- is systematically waiting longer, which would be a service-quality concern
-- independent of department or priority.
SELECT
    "Age_Group",
    ROUND(AVG("Total_Waiting_Time_Valid"), 2) AS avg_wait_minutes,
    COUNT(*) AS patients
FROM encounters
WHERE "Total_Waiting_Time_Valid" IS NOT NULL
GROUP BY "Age_Group"
ORDER BY
    CASE "Age_Group"
        WHEN '0-4' THEN 1 WHEN '5-14' THEN 2 WHEN '15-24' THEN 3
        WHEN '25-44' THEN 4 WHEN '45-64' THEN 5 ELSE 6
    END;


-- Q12: Waiting time for laboratory patients specifically (lab wait, not total wait).
-- Business purpose: isolates the lab-specific delay from the rest of the visit,
-- which is what a lab manager (as opposed to a general hospital administrator)
-- actually needs to see.
SELECT
    "Department",
    ROUND(AVG("Laboratory_Wait_Time"), 2) AS avg_lab_wait_minutes,
    ROUND(AVG("Laboratory_Duration"), 2) AS avg_lab_duration_minutes,
    COUNT(*) AS lab_patients
FROM encounters
WHERE "Laboratory_Requested" = 1
GROUP BY "Department"
ORDER BY avg_lab_wait_minutes DESC;


-- Q13: Waiting time and length of stay, admitted vs. discharged.
-- Business purpose: admitted patients are expected to have longer encounters
-- (higher acuity, more procedures) — this confirms it directly and quantifies
-- the gap for bed-planning purposes.
SELECT
    "Disposition",
    ROUND(AVG("Total_Waiting_Time_Valid"), 2) AS avg_wait_minutes,
    ROUND(AVG("Total_Length_of_Stay"), 2) AS avg_los_minutes,
    COUNT(*) AS patients
FROM encounters
GROUP BY "Disposition"
ORDER BY avg_los_minutes DESC;
