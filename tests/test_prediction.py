import pandas as pd
import pytest

from patient_flow.prediction import prepare_prediction_frame, train_long_wait_model


def sample_encounters() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Department": ["OPD", "Emergency", "Paediatrics", "OPD"] * 50,
            "Priority_Level": ["Routine", "Urgent", "Routine", "Emergency"] * 50,
            "Visit_Type": ["New", "Follow-up", "New", "New"] * 50,
            "Arrival_Time": pd.date_range("2025-01-01 07:00", periods=200, freq="h"),
            "Total_Waiting_Time": [10, 90, 20, 120] * 50,
            "Total_Waiting_Time_Valid": [10, 90, 20, 120] * 50,
            "Negative_Wait_Flag": [False] * 200,
            "Impossible_Timestamp_Flag": [False] * 200,
            "Total_Length_of_Stay": [40, 200, 60, 240] * 50,
            "Disposition": ["Discharged", "Admitted", "Discharged", "Discharged"] * 50,
        }
    )


def test_prediction_features_exclude_outcome_and_post_outcome_fields() -> None:
    features, target = prepare_prediction_frame(sample_encounters())

    assert "Total_Waiting_Time" not in features.columns
    assert "Total_Length_of_Stay" not in features.columns
    assert "Disposition" not in features.columns
    assert "Priority_Level" not in features.columns
    assert len(features) == len(target) == 200
    assert set(target.unique()) == {0, 1}


def test_long_wait_model_returns_holdout_metrics_and_feature_effects() -> None:
    result = train_long_wait_model(sample_encounters())

    assert result["metrics"]["test_observations"] == 40
    assert 0 <= result["metrics"]["roc_auc"] <= 1
    assert not result["feature_effects"].empty
    assert not result["roc_curve"].empty


def test_prediction_rejects_single_class_target() -> None:
    frame = sample_encounters()
    frame["Total_Waiting_Time"] = 10
    frame["Total_Waiting_Time_Valid"] = 10

    with pytest.raises(ValueError):
        train_long_wait_model(frame)
