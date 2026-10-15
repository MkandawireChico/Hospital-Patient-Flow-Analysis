-- ============================================================================
-- 01_volume_and_trends.sql
-- Patient volume, daily/monthly trends, peak hours.
-- ============================================================================

-- Q1: Patient volume by department.
-- Business purpose: the most basic operational question — where is patient
-- load actually concentrated?
SELECT
    "Department",
    COUNT(*) AS patient_count
FROM encounters
WHERE "Department" != 'Unknown'
GROUP BY "Department"
ORDER BY patient_count DESC;


-- Q2: Daily patient arrivals (first 15 days shown for brevity).
-- Business purpose: day-to-day staffing and supply planning needs actual
-- daily counts, not just a yearly or monthly average.
SELECT
    "Visit_Date",
    COUNT(*) AS patients
FROM encounters
GROUP BY "Visit_Date"
ORDER BY "Visit_Date"
LIMIT 15;


-- Q3: Monthly patient volume.
-- Business purpose: budget and staffing cycles are usually monthly — this
-- is the number that would go into a monthly operations report.
SELECT
    STRFTIME('%Y-%m', "Visit_Date") AS year_month,
    COUNT(*) AS patients
FROM encounters
GROUP BY year_month
ORDER BY year_month;


-- Q9: Peak arrival hours (grouped here with volume/time queries).
-- Business purpose: identifies exactly which hour(s) need extra registration/
-- triage capacity — "mornings are busy" is not actionable, "8am is busy" is.
SELECT
    "Arrival_Hour",
    COUNT(*) AS arrivals
FROM encounters
GROUP BY "Arrival_Hour"
ORDER BY arrivals DESC
LIMIT 5;


-- Daily and monthly trend, combined with a 7-day rolling average via a window function.
-- Business purpose: a single day's count is noisy — a rolling average is what
-- reveals a genuine trend versus normal day-to-day variation.
WITH daily AS (
    SELECT "Visit_Date", COUNT(*) AS patients
    FROM encounters
    GROUP BY "Visit_Date"
)
SELECT
    "Visit_Date",
    patients,
    ROUND(AVG(patients) OVER (
        ORDER BY "Visit_Date" ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 1) AS rolling_7day_avg
FROM daily
ORDER BY "Visit_Date"
LIMIT 15;
