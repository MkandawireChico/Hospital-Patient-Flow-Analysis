from __future__ import annotations

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
