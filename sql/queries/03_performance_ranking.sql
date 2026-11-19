-- ============================================================================
-- 03_performance_ranking.sql
-- Consultation duration, length of stay, department performance ranking.
-- ============================================================================

-- Q7: Average consultation duration by department.
-- Business purpose: distinguishes "patients wait a long time before being
-- seen" (a queueing problem) from "consultations themselves take a long
-- time" (a clinical-workflow question) — these need different responses.
SELECT
    "Department",
    ROUND(AVG("Consultation_Duration"), 2) AS avg_consultation_minutes,
    COUNT(*) AS patients
FROM encounters
WHERE "Department" != 'Unknown'
GROUP BY "Department"
ORDER BY avg_consultation_minutes DESC;


-- Q8: Average length of stay by department.
SELECT
    "Department",
    ROUND(AVG("Total_Length_of_Stay"), 2) AS avg_los_minutes,
    ROUND(AVG("Total_Length_of_Stay") / 60.0, 2) AS avg_los_hours,
    COUNT(*) AS patients
FROM encounters
WHERE "Department" != 'Unknown'
GROUP BY "Department"
ORDER BY avg_los_minutes DESC;


-- Q14: Department performance ranking — a composite view combining wait,
-- long-wait rate, and LOS into a single RANK() per metric, then an overall
-- average rank.
-- Business purpose: a single "which department needs the most attention"
-- answer is more useful to an administrator than four separate rankings
-- they have to reconcile themselves.
WITH dept_metrics AS (
    SELECT
        "Department",
        AVG("Total_Waiting_Time_Valid") AS avg_wait,
        SUM("Long_Wait_Flag") * 1.0 / COUNT(*) AS long_wait_rate,
        AVG("Total_Length_of_Stay") AS avg_los
    FROM encounters
    WHERE "Department" != 'Unknown'
      AND "Total_Waiting_Time_Valid" IS NOT NULL
    GROUP BY "Department"
),
ranked AS (
    SELECT *,
        RANK() OVER (ORDER BY avg_wait DESC) AS wait_rank,
        RANK() OVER (ORDER BY long_wait_rate DESC) AS long_wait_rank,
        RANK() OVER (ORDER BY avg_los DESC) AS los_rank
    FROM dept_metrics
)
SELECT
    "Department",
    ROUND(avg_wait, 2) AS avg_wait_minutes,
    ROUND(long_wait_rate, 4) AS long_wait_rate,
    ROUND(avg_los, 2) AS avg_los_minutes,
    wait_rank, long_wait_rank, los_rank,
    ROUND((wait_rank + long_wait_rank + los_rank) / 3.0, 2) AS overall_attention_score
FROM ranked
ORDER BY overall_attention_score;


-- Q15: Monthly trend by department (JOIN across departments + encounters,
-- with a CTE for the monthly aggregation).
-- Business purpose: checks whether a department's congestion is worsening,
-- improving, or stable over the course of the year — a single annual average
-- would hide a department that started fine and deteriorated.
WITH monthly_dept AS (
    SELECT
        d."Department",
        STRFTIME('%Y-%m', e."Visit_Date") AS year_month,
        AVG(e."Total_Waiting_Time_Valid") AS avg_wait
    FROM encounters e
    JOIN departments d ON e."Department_ID" = d."Department_ID"
    GROUP BY d."Department", year_month
)
SELECT "Department", year_month, ROUND(avg_wait, 2) AS avg_wait_minutes
FROM monthly_dept
ORDER BY "Department", year_month
LIMIT 24;


-- Bonus: doctors with the highest average consultation duration (JOIN to the
-- doctors dimension table, which is itself built from the doctor ID's
-- embedded department code rather than the raw Department column — see the
-- comment in build_database.py for why that matters).
-- Business purpose: a workload/case-mix question a department head would
-- actually ask, not just a demonstration JOIN for its own sake.
SELECT
    doc."Doctor_ID",
    doc."Department",
    ROUND(AVG(e."Consultation_Duration"), 2) AS avg_consultation_minutes,
    COUNT(*) AS patients_seen
FROM encounters e
JOIN doctors doc ON e."Doctor_ID" = doc."Doctor_ID"
GROUP BY doc."Doctor_ID", doc."Department"
HAVING COUNT(*) > 100
ORDER BY avg_consultation_minutes DESC
LIMIT 10;
