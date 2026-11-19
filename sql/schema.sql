-- ============================================================================
-- SCHEMA: hospital_patient_flow.db
-- ============================================================================
-- The cleaned dataset (data/processed/hospital_patient_flow_clean.csv) is a
-- single flat table, one row per patient encounter. For the SQL portion of
-- this project it is split into three related tables so the queries can
-- demonstrate real JOINs, not just filter a single flat file — and because a
-- real hospital records system would naturally separate department and
-- doctor reference data from the encounter log itself.
--
-- Build script: sql/build_database.py (regenerates hospital_patient_flow.db
-- from the cleaned CSV)
-- ============================================================================

-- departments: one row per clinical department
CREATE TABLE departments (
    "Department"    TEXT,
    "Department_ID" INTEGER PRIMARY KEY
);

-- doctors: one row per distinct doctor, with the department they belong to
CREATE TABLE doctors (
    "Doctor_ID"  TEXT,
    "Department" TEXT
);

-- encounters: one row per patient visit (the fact table)
CREATE TABLE encounters (
    "Patient_ID"                  TEXT,
    "Department_ID"               INTEGER REFERENCES departments("Department_ID"),
    "Department"                  TEXT,
    "Visit_Date"                  TEXT,
    "Day_of_Week"                 TEXT,
    "Arrival_Time"                TEXT,
    "Registration_Time"           TEXT,
    "Registration_End_Time"       TEXT,
    "Triage_Start_Time"           TEXT,
    "Triage_End_Time"             TEXT,
    "Consultation_Start_Time"     TEXT,
    "Consultation_End_Time"       TEXT,
    "Laboratory_Requested"        INTEGER,   -- 0/1
    "Laboratory_Start_Time"       TEXT,
    "Laboratory_End_Time"         TEXT,
    "Pharmacy_Needed"             INTEGER,   -- 0/1
    "Pharmacy_Start_Time"         TEXT,
    "Pharmacy_End_Time"           TEXT,
    "Priority_Level"              TEXT,      -- Routine / Urgent / Emergency
    "Queue_Size"                  INTEGER,
    "Disposition"                 TEXT,      -- Discharged / Admitted / Referred Out
    "Age_Group"                   TEXT,
    "Sex"                         TEXT,
    "Referral_Status"             TEXT,
    "Visit_Type"                  TEXT,
    "Doctor_ID"                   TEXT REFERENCES doctors("Doctor_ID"),
    "Total_Waiting_Time"          REAL,      -- raw, may include flagged bad values
    "Total_Waiting_Time_Valid"    REAL,      -- NULL where timestamp/negative-wait errors were flagged
    "Consultation_Duration"       REAL,
    "Registration_Duration"       REAL,
    "Triage_Duration"             REAL,
    "Laboratory_Wait_Time"        REAL,
    "Laboratory_Duration"         REAL,
    "Pharmacy_Wait_Time"          REAL,
    "Pharmacy_Duration"           REAL,
    "Total_Length_of_Stay"        REAL,
    "Patient_Satisfaction_Score"  REAL,      -- NULL where not recorded
    "Arrival_Hour"                INTEGER,
    "Peak_Period"                 TEXT,      -- Peak / Non-Peak
    "Long_Wait_Flag"              INTEGER,   -- 0/1, Total_Waiting_Time_Valid > 60
    "High_Congestion_Flag"        INTEGER,   -- 0/1, hospital-wide upper-quartile queue-size threshold
    "Impossible_Timestamp_Flag"   INTEGER,
    "Negative_Wait_Flag"          INTEGER,
    "LOS_Outlier_Flag"            INTEGER,
    "Department_Data_Error"       INTEGER
);

-- Row counts as built: departments = 6 | doctors = 36 | encounters = 35,082
-- encounters.Total_Waiting_Time_Valid averages 13.75 minutes, matching the
-- flat cleaned CSV exactly (sanity-checked in build_database.py).
