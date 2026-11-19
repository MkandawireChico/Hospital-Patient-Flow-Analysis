from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "default.yaml"


def _validate_probability_map(values: dict[str, float], label: str) -> None:
    if not values or any(not 0 <= float(value) <= 1 for value in values.values()):
        raise ValueError(f"{label} must contain probabilities between 0 and 1.")
    if abs(sum(float(value) for value in values.values()) - 1.0) > 1e-6:
        raise ValueError(f"{label} probabilities must sum to 1.")


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate model settings before any random data is generated."""
    try:
        project = config["project"]
        simulation = config["simulation"]
        departments = simulation["departments"]
        shared = simulation["shared_services"]
        demographics = simulation["demographics"]
        patterns = simulation["encounter_patterns"]
        behaviour = simulation["behaviour"]
        issue = simulation["issue_injection"]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Simulation configuration is missing a required section: {exc}") from exc

    if int(project["random_seed"]) < 0:
        raise ValueError("project.random_seed must be non-negative.")
    if int(simulation["n_days"]) < 1:
        raise ValueError("simulation.n_days must be at least 1.")
    if not departments:
        raise ValueError("simulation.departments must define at least one department.")

    for name, department in departments.items():
        for key in ("daily_mean", "registration_staff", "triage_staff", "doctors"):
            value = float(department[key])
            if value < 0 or (key != "daily_mean" and value < 1):
                raise ValueError(f"Department {name}: {key} has an invalid value.")
        if float(department["weekend_multiplier"]) < 0:
            raise ValueError(f"Department {name}: weekend_multiplier must be non-negative.")
        for key in ("laboratory_probability", "pharmacy_probability"):
            if not 0 <= float(department[key]) <= 1:
                raise ValueError(f"Department {name}: {key} must be between 0 and 1.")
        for key in ("registration_duration", "triage_duration", "consultation_duration"):
            duration = [float(value) for value in department[key]]
            if len(duration) != 3 or not 0 < duration[0] <= duration[1] <= duration[2]:
                raise ValueError(f"Department {name}: {key} must be three positive, ordered triangular values.")
        _validate_probability_map(department["priority_distribution"], f"{name}.priority_distribution")
        if any(not 0 <= float(value) <= 1 for value in department["admission_probability"].values()):
            raise ValueError(f"{name}.admission_probability values must be between 0 and 1.")
        if set(department["admission_probability"]) != set(department["priority_distribution"]):
            raise ValueError(f"Department {name}: admission probabilities must cover every priority.")

    for name, service in shared.items():
        if int(service["servers"]) < 1:
            raise ValueError(f"Shared service {name} must have at least one server.")
        duration = [float(value) for value in service["duration"]]
        if len(duration) != 3 or not 0 < duration[0] <= duration[1] <= duration[2]:
            raise ValueError(f"Shared service {name}: duration must be three positive, ordered triangular values.")

    _validate_probability_map(demographics["default_sex_distribution"], "demographics.default_sex_distribution")
    _validate_probability_map(behaviour["non_admitted_disposition_probabilities"], "behaviour.non_admitted_disposition_probabilities")
    if len(demographics["age_groups"]) != len(demographics["default_age_distribution"]):
        raise ValueError("Default age groups and probabilities must have matching lengths.")
    _validate_probability_map({
        str(index): value for index, value in enumerate(demographics["default_age_distribution"])
    }, "demographics.default_age_distribution")
    for name, distribution in demographics["department_age_distributions"].items():
        _validate_probability_map(
            {str(index): value for index, value in enumerate(distribution["probabilities"])},
            f"demographics.department_age_distributions.{name}",
        )
        if len(distribution["groups"]) != len(distribution["probabilities"]):
            raise ValueError(f"Age groups and probabilities do not align for {name}.")
    for name, distribution in demographics["department_sex_distributions"].items():
        _validate_probability_map(distribution, f"demographics.department_sex_distributions.{name}")
    for name, probability in patterns["department_referral_probabilities"].items():
        if not 0 <= float(probability) <= 1:
            raise ValueError(f"Referral probability for {name} must be between 0 and 1.")
    for name, distribution in patterns["visit_type_probabilities"].items():
        _validate_probability_map(distribution, f"encounter_patterns.visit_type_probabilities.{name}")
    if set(simulation["department_codes"]) != set(departments):
        raise ValueError("department_codes must contain exactly the configured department names.")
    arrival_patterns = simulation["arrival_patterns"]
    for key, value in arrival_patterns["daytime_hour_weights"].items():
        if float(value) <= 0:
            raise ValueError(f"Daytime arrival weight {key} must be positive.")
    minute_bounds = [int(value) for value in arrival_patterns["arrival_minute_bounds"]]
    if len(minute_bounds) != 2 or not 0 <= minute_bounds[0] <= minute_bounds[1] <= 59:
        raise ValueError("Arrival minute bounds must be ordered values between 0 and 59.")
    arrival = arrival_patterns["emergency_hour_weights"]
    for key in ("default", "evening_peak", "early_morning"):
        if float(arrival[key]) <= 0:
            raise ValueError(f"Emergency arrival weight {key} must be positive.")
    if any(not 0 <= int(hour) <= 23 for key in ("evening_hours", "early_morning_hours") for hour in arrival[key]):
        raise ValueError("Emergency arrival hour lists must contain hours from 0 to 23.")
    if int(issue["random_seed"]) < 0:
        raise ValueError("simulation.issue_injection.random_seed must be non-negative.")
    if float(issue["impossible_timestamp_offset_minutes"]) <= 0:
        raise ValueError("Impossible timestamp offset must be positive.")
    for key in ("negative_wait_magnitude_minutes", "los_outlier_multiplier"):
        values = [float(value) for value in issue[key]]
        minimum = 0 if key == "negative_wait_magnitude_minutes" else 1
        if len(values) != 2 or values[0] < minimum or values[1] < values[0]:
            raise ValueError(f"issue_injection.{key} must contain two ordered valid values.")
    if not issue["department_error_values"]:
        raise ValueError("At least one department error replacement value is required.")
    for key, value in issue.items():
        if key.endswith("_rate") and not 0 <= float(value) <= 1:
            raise ValueError(f"simulation.issue_injection.{key} must be between 0 and 1.")
    satisfaction = behaviour["satisfaction"]
    for name, value in (
        ("referral_probability", patterns["referral_probability"]),
        ("non_routine_laboratory_probability_multiplier", behaviour["non_routine_laboratory_probability_multiplier"]),
        ("satisfaction.noise_standard_deviation", satisfaction["noise_standard_deviation"]),
        ("satisfaction.wait_penalty_divisor_minutes", satisfaction["wait_penalty_divisor_minutes"]),
        ("satisfaction.maximum_wait_penalty", satisfaction["maximum_wait_penalty"]),
        ("satisfaction.baseline_score", satisfaction["baseline_score"]),
    ):
        if float(value) < 0:
            raise ValueError(f"{name} must be non-negative.")
    if float(satisfaction["wait_penalty_divisor_minutes"]) == 0:
        raise ValueError("Satisfaction wait penalty divisor must be greater than zero.")
    if float(satisfaction["admission_penalty"]) < 0:
        raise ValueError("Satisfaction admission penalty must be non-negative.")
    score_bounds = [int(value) for value in satisfaction["score_bounds"]]
    if len(score_bounds) != 2 or score_bounds[0] > score_bounds[1]:
        raise ValueError("Satisfaction score bounds must be two ordered integers.")
    for key in ("admission_extra_stay_minutes",):
        values = [float(value) for value in behaviour[key]]
        if len(values) != 2 or values[0] < 0 or values[1] < values[0]:
            raise ValueError(f"behaviour.{key} must contain two ordered non-negative values.")
    return config


def load_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load and validate a YAML simulation configuration."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    return validate_config(config)


def load_default_config() -> dict[str, Any]:
    """Load and validate the default configuration."""
    return load_config(DEFAULT_CONFIG_PATH)
