from __future__ import annotations

import pandas as pd
import pytest
import yaml

from patient_flow.config import DEFAULT_CONFIG_PATH
from patient_flow.simulation import generate_case_study_data


def test_simulation_uses_config_and_is_reproducible(tmp_path):
    config = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    config["simulation"]["n_days"] = 3
    config_path = tmp_path / "small_simulation.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    clean_first, raw_first = generate_case_study_data(config_path)
    clean_second, raw_second = generate_case_study_data(config_path)

    assert not clean_first.empty
    assert len(raw_first) > len(clean_first)
    assert clean_first.equals(clean_second)
    assert raw_first.equals(raw_second)
    assert {
        "Total_Waiting_Time",
        "Total_Length_of_Stay",
        "Patient_Satisfaction_Score",
    } <= set(clean_first)
    assert {"Laboratory_Requested", "Pharmacy_Needed", "Department"} <= set(raw_first)


def test_default_config_contains_all_department_and_shared_queue_settings():
    config = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    departments = config["simulation"]["departments"]

    assert len(departments) == 6
    assert all("weekend_multiplier" in settings for settings in departments.values())
    assert config["simulation"]["shared_services"]["laboratory"]["servers"] == 3
    assert config["simulation"]["shared_services"]["pharmacy"]["servers"] == 4
    assert config["simulation"]["n_days"] == 365


def test_demographic_and_encounter_assumptions_are_configurable(tmp_path):
    config = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    config["simulation"]["n_days"] = 2
    for department in config["simulation"]["departments"]:
        config["simulation"]["demographics"]["department_age_distributions"][department] = {
            "groups": ["Configured age"],
            "probabilities": [1.0],
        }
        config["simulation"]["demographics"]["department_sex_distributions"][department] = {
            "Female": 1.0
        }
    config_path = tmp_path / "demographics.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    clean, _ = generate_case_study_data(config_path)

    assert clean["Age_Group"].eq("Configured age").all()
    assert clean["Sex"].eq("Female").all()


def test_quality_issue_values_and_randomness_are_configurable(tmp_path):
    config = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    config["simulation"]["n_days"] = 2
    issue = config["simulation"]["issue_injection"]
    issue.update({
        "missing_satisfaction_rate": 0.0,
        "missing_referral_rate": 0.0,
        "duplicate_rate": 0.0,
        "department_error_rate": 1.0,
        "impossible_timestamp_rate": 0.0,
        "negative_wait_rate": 0.0,
        "los_outlier_rate": 0.0,
        "random_seed": 777,
        "department_error_values": ["CONFIGURED_ERROR"],
    })
    config_path = tmp_path / "quality.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    _, raw_first = generate_case_study_data(config_path)
    _, raw_second = generate_case_study_data(config_path)

    assert raw_first["Department"].eq("CONFIGURED_ERROR").all()
    assert raw_first.equals(raw_second)


def test_invalid_probability_distribution_is_rejected(tmp_path):
    config = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    config["simulation"]["n_days"] = 1
    config["simulation"]["demographics"]["default_sex_distribution"] = {
        "Female": 0.7,
        "Male": 0.7,
    }
    config_path = tmp_path / "invalid.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="sum to 1"):
        generate_case_study_data(config_path)


def test_generated_raw_dataset_uses_configured_output_path(tmp_path):
    from patient_flow.simulation import generate_and_save_raw_dataset

    config = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    config["simulation"]["n_days"] = 2
    config["paths"]["raw"] = "exports/custom_raw.csv"
    config_path = tmp_path / "custom.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    raw, output_path = generate_and_save_raw_dataset(config_path)

    assert output_path == tmp_path / "exports" / "custom_raw.csv"
    assert output_path.exists()
    assert len(pd.read_csv(output_path)) == len(raw)
