"""
Builds sql/hospital_patient_flow.db from data/processed/hospital_patient_flow_clean.csv.

Run from the sql/ folder:
    python build_database.py

Splits the single cleaned flat file into three related tables
(departments / doctors / encounters) so the SQL queries can demonstrate
real JOINs. See schema.sql for table definitions and reasoning.
"""
import sqlite3
import pandas as pd

SOURCE_CSV = "../data/processed/hospital_patient_flow_clean.csv"
DB_PATH = "hospital_patient_flow.db"

TIMESTAMP_COLS = [
    "Visit_Date", "Arrival_Time", "Registration_Time", "Registration_End_Time",
    "Triage_Start_Time", "Triage_End_Time", "Consultation_Start_Time", "Consultation_End_Time",
    "Laboratory_Start_Time", "Laboratory_End_Time", "Pharmacy_Start_Time", "Pharmacy_End_Time",
]

ENCOUNTER_COLS = [
    "Patient_ID", "Department_ID", "Department", "Visit_Date", "Day_of_Week", "Arrival_Time",
    "Registration_Time", "Registration_End_Time", "Triage_Start_Time", "Triage_End_Time",
    "Consultation_Start_Time", "Consultation_End_Time", "Laboratory_Requested",
    "Laboratory_Start_Time", "Laboratory_End_Time", "Pharmacy_Needed", "Pharmacy_Start_Time",
    "Pharmacy_End_Time", "Priority_Level", "Queue_Size", "Disposition", "Age_Group", "Sex",
    "Referral_Status", "Visit_Type", "Doctor_ID", "Total_Waiting_Time", "Total_Waiting_Time_Valid",
    "Consultation_Duration", "Registration_Duration", "Triage_Duration", "Laboratory_Wait_Time",
    "Laboratory_Duration", "Pharmacy_Wait_Time", "Pharmacy_Duration", "Total_Length_of_Stay",
    "Patient_Satisfaction_Score", "Arrival_Hour", "Peak_Period", "Long_Wait_Flag",
    "High_Congestion_Flag", "Impossible_Timestamp_Flag", "Negative_Wait_Flag", "LOS_Outlier_Flag",
    "Department_Data_Error",
]

def main():
    df = pd.read_csv(SOURCE_CSV, parse_dates=TIMESTAMP_COLS)

    conn = sqlite3.connect(DB_PATH)

    departments = df[df["Department"] != "Unknown"][["Department"]].drop_duplicates().reset_index(drop=True)
    departments["Department_ID"] = range(1, len(departments) + 1)

    # Doctors are derived from the department code embedded in Doctor_ID
    # (e.g. "DOC-EMG-1" -> Emergency), NOT from the raw Department column.
    # Why: Section 2 of the notebook deliberately injects incorrect Department
    # values on ~0.3% of encounter rows (a realistic data-entry error), which
    # corrupts Department without touching Doctor_ID. Building the doctors
    # table from the flat Department column would let that injected error
    # leak into a dimension table and make it look like individual doctors
    # work across multiple departments, which they don't. Parsing the doctor's
    # actual department from their ID avoids inheriting that corruption.
    _CODE_TO_DEPT = {
        "OPD": "Outpatient Department", "EMG": "Emergency", "MAT": "Maternal Health",
        "PED": "Paediatrics", "CHR": "Chronic Care", "TBH": "TB/HIV Clinic",
    }
    doctors = df[["Doctor_ID"]].drop_duplicates().reset_index(drop=True)
    doctors["Department"] = doctors["Doctor_ID"].str.split("-").str[1].map(_CODE_TO_DEPT)

    encounters = df.merge(departments, on="Department", how="left")[ENCOUNTER_COLS]

    departments.to_sql("departments", conn, if_exists="replace", index=False)
    doctors.to_sql("doctors", conn, if_exists="replace", index=False)
    encounters.to_sql("encounters", conn, if_exists="replace", index=False)

    cur = conn.cursor()
    cur.execute('CREATE INDEX IF NOT EXISTS idx_enc_dept ON encounters("Department")')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_enc_date ON encounters("Visit_Date")')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_enc_patient ON encounters("Patient_ID")')
    conn.commit()

    check = pd.read_sql('SELECT COUNT(*) AS n, ROUND(AVG("Total_Waiting_Time_Valid"), 2) AS avg_wait FROM encounters', conn)
    print(f"departments: {len(departments)} | doctors: {len(doctors)} | encounters: {len(encounters)}")
    print(f"Sanity check -> rows: {check.iloc[0]['n']}, avg wait: {check.iloc[0]['avg_wait']} min")

    conn.close()
    print(f"Database written to {DB_PATH}")

if __name__ == "__main__":
    main()
