# isort: skip_file
from __future__ import annotations

import heapq
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import config as config_module


def _daytime_hour_probs(
    open_hour: int,
    close_hour: int,
    peak_start: int,
    peak_end: int,
    weights_config: dict[str, Any],
) -> np.ndarray:
    hours = range(open_hour, close_hour)
    weights = np.array([
        float(weights_config["peak"] if peak_start <= hour < peak_end else weights_config["default"])
        for hour in hours
    ])
    return weights / weights.sum()


def _emergency_hour_probs(pattern: dict[str, Any]) -> np.ndarray:
    weights = np.full(24, float(pattern["default"]))
    weights[list(pattern["evening_hours"])] = float(pattern["evening_peak"])
    weights[list(pattern["early_morning_hours"])] = float(pattern["early_morning"])
    return weights / weights.sum()


def _sample_arrival(
    department: dict[str, Any],
    day_start: pd.Timestamp,
    emergency_pattern: dict[str, Any],
    daytime_pattern: dict[str, Any],
    minute_bounds: list[int],
) -> pd.Timestamp:
    open_hour, close_hour = department["open"]
    peak_start, peak_end = department["peak"]
    if department["night"]:
        hour = int(np.random.choice(range(24), p=_emergency_hour_probs(emergency_pattern)))
    else:
        hour = int(np.random.choice(
            range(open_hour, close_hour),
            p=_daytime_hour_probs(
                open_hour, close_hour, peak_start, peak_end, daytime_pattern
            ),
        ))
    minute = int(np.random.randint(int(minute_bounds[0]), int(minute_bounds[1]) + 1))
    return day_start + pd.Timedelta(hours=hour, minutes=minute)


def _process_queue(
    ready_times: list[pd.Timestamp],
    n_servers: int,
    duration: tuple[float, float, float],
) -> tuple[list[pd.Timestamp], list[pd.Timestamp]]:
    if not ready_times:
        return [], []
    if n_servers < 1:
        raise ValueError("Every queue must have at least one server.")
    server_heap = [ready_times[0]] * n_servers
    heapq.heapify(server_heap)
    starts: list[pd.Timestamp] = []
    ends: list[pd.Timestamp] = []
    for ready in ready_times:
        start = max(ready, heapq.heappop(server_heap))
        end = start + pd.Timedelta(minutes=np.random.triangular(*duration))
        heapq.heappush(server_heap, end)
        starts.append(start)
        ends.append(end)
    return starts, ends


def _sample_age_group(department: str, settings: dict[str, Any]) -> str:
    demographics = settings["demographics"]
    distribution = demographics["department_age_distributions"].get(department)
    if distribution:
        groups, probabilities = distribution["groups"], distribution["probabilities"]
    else:
        groups = demographics["age_groups"]
        probabilities = demographics["default_age_distribution"]
    return str(np.random.choice(groups, p=probabilities))


def _sample_sex(department: str, settings: dict[str, Any]) -> str:
    demographics = settings["demographics"]
    distribution = demographics["department_sex_distributions"].get(
        department, demographics["default_sex_distribution"]
    )
    return str(np.random.choice(list(distribution), p=list(distribution.values())))


def _sample_referral(department: str, settings: dict[str, Any]) -> str:
    patterns = settings["encounter_patterns"]
    referred = float(patterns["department_referral_probabilities"].get(
        department, patterns["referral_probability"]
    ))
    return str(np.random.choice(
        ["Self-Presented", "Referred from Health Centre"], p=[1 - referred, referred]
    ))


def _sample_visit_type(department: str, settings: dict[str, Any]) -> str:
    distributions = settings["encounter_patterns"]["visit_type_probabilities"]
    distribution = distributions.get(department, distributions["default"])
    return str(np.random.choice(list(distribution), p=list(distribution.values())))


def _build_encounters(config: dict[str, Any]) -> pd.DataFrame:
    settings = config["simulation"]
    np.random.seed(int(config["project"]["random_seed"]))
    start_date = pd.Timestamp(settings["start_date"])
    n_days = int(settings["n_days"])
    departments = settings["departments"]
    shared = settings["shared_services"]

    department_codes = settings["department_codes"]
    emergency_pattern = settings["arrival_patterns"]["emergency_hour_weights"]
    daytime_pattern = settings["arrival_patterns"]["daytime_hour_weights"]
    minute_bounds = settings["arrival_patterns"]["arrival_minute_bounds"]
    records: list[dict[str, Any]] = []
    patient_counter = 0

    for day_index in range(n_days):
        day_start = start_date + pd.Timedelta(days=day_index)
        day_name = day_start.day_name()
        day_records: list[dict[str, Any]] = []

        for department, dept in departments.items():
            weekend_factor = (
                float(dept["weekend_multiplier"])
                if day_name in ("Saturday", "Sunday")
                else 1.0
            )
            n_patients = int(np.random.poisson(float(dept["daily_mean"]) * weekend_factor))
            if not n_patients:
                continue

            arrivals = sorted(
                _sample_arrival(
                    dept, day_start, emergency_pattern, daytime_pattern, minute_bounds
                )
                for _ in range(n_patients)
            )
            reg_starts, reg_ends = _process_queue(
                arrivals,
                int(dept["registration_staff"]),
                tuple(dept["registration_duration"]),
            )
            triage_starts, triage_ends = _process_queue(
                reg_ends,
                int(dept["triage_staff"]),
                tuple(dept["triage_duration"]),
            )
            consult_starts, consult_ends = _process_queue(
                triage_ends,
                int(dept["doctors"]),
                tuple(dept["consultation_duration"]),
            )

            consult_array = np.array(consult_starts)
            arrival_array = np.array(arrivals)
            queue_sizes = [
                int(np.sum((arrival_array <= arrival) & (consult_array > arrival)))
                for arrival in arrival_array
            ]
            priority_distribution = dept["priority_distribution"]
            priorities = np.random.choice(
                list(priority_distribution), size=n_patients, p=list(priority_distribution.values())
            )

            for index in range(n_patients):
                patient_counter += 1
                priority = str(priorities[index])
                lab_probability = float(dept["laboratory_probability"])
                if priority != "Routine":
                    lab_probability *= float(
                        settings["behaviour"]["non_routine_laboratory_probability_multiplier"]
                    )
                lab_requested = np.random.random() < lab_probability
                pharmacy_needed = np.random.random() < float(dept["pharmacy_probability"])
                admission_probability = float(dept["admission_probability"][priority])
                disposition_distribution = settings["behaviour"][
                    "non_admitted_disposition_probabilities"
                ]
                disposition = "Admitted" if np.random.random() < admission_probability else str(
                    np.random.choice(
                        list(disposition_distribution), p=list(disposition_distribution.values())
                    )
                )
                day_records.append({
                    "Patient_ID": f"PT-{patient_counter:07d}",
                    "Visit_Date": day_start.date(),
                    "Day_of_Week": day_name,
                    "Department": department,
                    "Arrival_Time": arrivals[index],
                    "Registration_Time": reg_starts[index],
                    "Registration_End_Time": reg_ends[index],
                    "Triage_Start_Time": triage_starts[index],
                    "Triage_End_Time": triage_ends[index],
                    "Consultation_Start_Time": consult_starts[index],
                    "Consultation_End_Time": consult_ends[index],
                    "Priority_Level": priority,
                    "Queue_Size": queue_sizes[index],
                    "Laboratory_Requested": bool(lab_requested),
                    "Pharmacy_Needed": bool(pharmacy_needed),
                    "Disposition": disposition,
                    "Age_Group": _sample_age_group(department, settings),
                    "Sex": _sample_sex(department, settings),
                    "Referral_Status": _sample_referral(department, settings),
                    "Visit_Type": _sample_visit_type(department, settings),
                    "Doctor_ID": (
                        f"DOC-{department_codes[department]}-"
                        f"{np.random.randint(1, int(dept['doctors']) + 1)}"
                    ),
                })

        lab_config = shared["laboratory"]
        lab_records = sorted(
            [row for row in day_records if row["Laboratory_Requested"]],
            key=lambda row: row["Consultation_End_Time"],
        )
        if lab_records:
            ready = [row["Consultation_End_Time"] for row in lab_records]
            starts, ends = _process_queue(
                ready, int(lab_config["servers"]), tuple(lab_config["duration"])
            )
            for row, start, end in zip(lab_records, starts, ends):
                row["Laboratory_Start_Time"], row["Laboratory_End_Time"] = start, end

        pharmacy_config = shared["pharmacy"]
        pharmacy_records = [row for row in day_records if row["Pharmacy_Needed"]]
        for row in pharmacy_records:
            row["_pharm_ready"] = row.get("Laboratory_End_Time", row["Consultation_End_Time"])
        pharmacy_records.sort(key=lambda row: row["_pharm_ready"])
        if pharmacy_records:
            ready = [row["_pharm_ready"] for row in pharmacy_records]
            starts, ends = _process_queue(
                ready, int(pharmacy_config["servers"]), tuple(pharmacy_config["duration"])
            )
            for row, start, end in zip(pharmacy_records, starts, ends):
                row["Pharmacy_Start_Time"], row["Pharmacy_End_Time"] = start, end

        records.extend(day_records)

    return pd.DataFrame(records)


def _add_derived_fields(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    output = df.copy()
    output["Wait_For_Registration_Min"] = (
        output["Registration_Time"] - output["Arrival_Time"]
    ).dt.total_seconds() / 60
    output["Wait_For_Triage_Min"] = (
        output["Triage_Start_Time"] - output["Registration_End_Time"]
    ).dt.total_seconds() / 60
    output["Wait_For_Consultation_Min"] = (
        output["Consultation_Start_Time"] - output["Triage_End_Time"]
    ).dt.total_seconds() / 60
    output["Total_Waiting_Time"] = (
        output["Wait_For_Registration_Min"]
        + output["Wait_For_Triage_Min"]
        + output["Wait_For_Consultation_Min"]
    )
    output["Consultation_Duration"] = (
        output["Consultation_End_Time"] - output["Consultation_Start_Time"]
    ).dt.total_seconds() / 60
    output["Registration_Duration"] = (
        output["Registration_End_Time"] - output["Registration_Time"]
    ).dt.total_seconds() / 60
    output["Triage_Duration"] = (
        output["Triage_End_Time"] - output["Triage_Start_Time"]
    ).dt.total_seconds() / 60
    output["Laboratory_Wait_Time"] = np.where(
        output["Laboratory_Requested"],
        (output["Laboratory_Start_Time"] - output["Consultation_End_Time"]).dt.total_seconds() / 60,
        np.nan,
    )
    output["Laboratory_Duration"] = np.where(
        output["Laboratory_Requested"],
        (output["Laboratory_End_Time"] - output["Laboratory_Start_Time"]).dt.total_seconds() / 60,
        np.nan,
    )
    pharmacy_ready = output["Laboratory_End_Time"].where(
        output["Laboratory_Requested"], output["Consultation_End_Time"]
    )
    output["Pharmacy_Wait_Time"] = np.where(
        output["Pharmacy_Needed"],
        (output["Pharmacy_Start_Time"] - pharmacy_ready).dt.total_seconds() / 60,
        np.nan,
    )
    output["Pharmacy_Duration"] = np.where(
        output["Pharmacy_Needed"],
        (output["Pharmacy_End_Time"] - output["Pharmacy_Start_Time"]).dt.total_seconds() / 60,
        np.nan,
    )

    def final_end(row: pd.Series) -> pd.Timestamp:
        if pd.notna(row.get("Pharmacy_End_Time")):
            return row["Pharmacy_End_Time"]
        if pd.notna(row.get("Laboratory_End_Time")):
            return row["Laboratory_End_Time"]
        return row["Consultation_End_Time"]

    output["Final_Stage_End_Time"] = output.apply(final_end, axis=1)
    admitted = output["Disposition"].eq("Admitted")
    stay_min, stay_max = config["simulation"]["behaviour"]["admission_extra_stay_minutes"]
    admission_extra = np.where(admitted, np.random.uniform(stay_min, stay_max, len(output)), 0.0)
    output["Total_Length_of_Stay"] = (
        (output["Final_Stage_End_Time"] - output["Arrival_Time"]).dt.total_seconds() / 60
        + admission_extra
    )
    satisfaction = config["simulation"]["behaviour"]["satisfaction"]
    wait_component = (
        output["Total_Waiting_Time"] / float(satisfaction["wait_penalty_divisor_minutes"])
    ).clip(upper=float(satisfaction["maximum_wait_penalty"]))
    admission_component = np.where(admitted, float(satisfaction["admission_penalty"]), 0.0)
    noise = np.random.normal(0, float(satisfaction["noise_standard_deviation"]), len(output))
    score_min, score_max = satisfaction["score_bounds"]
    output["Patient_Satisfaction_Score"] = (
        float(satisfaction["baseline_score"]) - wait_component - admission_component + noise
    ).round().clip(int(score_min), int(score_max)).astype(int)
    return output


def _inject_quality_issues(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    output = df.copy()
    issue = config["simulation"]["issue_injection"]
    rng = np.random.default_rng(int(issue["random_seed"]))
    missing_satisfaction = float(issue["missing_satisfaction_rate"])
    missing_referral = float(issue["missing_referral_rate"])
    duplicate_rate = float(issue["duplicate_rate"])
    impossible_rate = float(issue["impossible_timestamp_rate"])
    negative_rate = float(issue["negative_wait_rate"])
    outlier_rate = float(issue["los_outlier_rate"])
    department_rate = float(issue["department_error_rate"])

    states = issue["random_states"]
    satisfaction_idx = output.sample(
        frac=missing_satisfaction, random_state=states["missing_satisfaction"]
    ).index
    output.loc[satisfaction_idx, "Patient_Satisfaction_Score"] = np.nan
    referral_idx = output.sample(
        frac=missing_referral, random_state=states["missing_referral"]
    ).index
    output.loc[referral_idx, "Referral_Status"] = np.nan
    duplicate_idx = output.sample(frac=duplicate_rate, random_state=states["duplicates"]).index
    output = pd.concat([output, output.loc[duplicate_idx]], ignore_index=True)

    impossible_idx = output.sample(
        frac=impossible_rate, random_state=states["impossible_timestamps"]
    ).index
    output.loc[impossible_idx, "Consultation_Start_Time"] = (
        output.loc[impossible_idx, "Arrival_Time"]
        - pd.Timedelta(minutes=float(issue["impossible_timestamp_offset_minutes"]))
    )
    negative_idx = output.sample(frac=negative_rate, random_state=states["negative_waits"]).index
    output.loc[negative_idx, "Total_Waiting_Time"] = (
        -np.abs(output.loc[negative_idx, "Total_Waiting_Time"])
        - rng.uniform(*issue["negative_wait_magnitude_minutes"], size=len(negative_idx))
    )
    outlier_idx = output.sample(frac=outlier_rate, random_state=states["los_outliers"]).index
    output.loc[outlier_idx, "Total_Length_of_Stay"] *= rng.uniform(
        *issue["los_outlier_multiplier"], size=len(outlier_idx)
    )
    bad_department_idx = output.sample(
        frac=department_rate, random_state=states["department_errors"]
    ).index
    bad_department_values = issue["department_error_values"]
    output.loc[bad_department_idx, "Department"] = rng.choice(
        bad_department_values, size=len(bad_department_idx)
    )
    return output


def generate_case_study_data(
    config_path: str | Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate clean encounters and the raw case-study dataset with configured quality issues.

    Returns (clean_simulation, raw_dataset). Random seeds and all model parameters
    are loaded from config/default.yaml unless another YAML path is supplied.
    """
    config_file = Path(config_path) if config_path else config_module.DEFAULT_CONFIG_PATH
    config = config_module.load_config(config_file)
    clean = _add_derived_fields(_build_encounters(config), config)
    raw = _inject_quality_issues(clean, config)
    return clean, raw


def generate_and_save_raw_dataset(
    config_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> tuple[pd.DataFrame, Path]:
    """Generate the configured raw dataset, save it, and return the data and path."""
    config_file = Path(config_path) if config_path else config_module.DEFAULT_CONFIG_PATH
    config = config_module.load_config(config_file)
    _, raw = generate_case_study_data(config_file)
    configured_path = Path(config["paths"]["raw"])
    if not configured_path.is_absolute():
        config_root = (
            config_module.PROJECT_ROOT
            if config_file.resolve() == config_module.DEFAULT_CONFIG_PATH.resolve()
            else config_file.resolve().parent
        )
        configured_path = config_root / configured_path
    target = Path(output_path) if output_path else configured_path
    if not target.is_absolute():
        target = Path.cwd() / target
    target.parent.mkdir(parents=True, exist_ok=True)
    raw.to_csv(target, index=False)
    return raw, target
