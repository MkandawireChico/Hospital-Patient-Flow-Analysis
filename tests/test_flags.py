import pandas as pd

from patient_flow.flags import boolean_flag_column


def test_boolean_flags_parse_csv_strings_and_missing_values() -> None:
    frame = pd.DataFrame({"flag": ["False", "True", " false ", "yes", "0", None]})

    assert boolean_flag_column(frame, "flag").tolist() == [
        False, True, False, True, False, False
    ]


def test_boolean_flags_parse_native_boolean_and_numeric_columns() -> None:
    assert boolean_flag_column(pd.DataFrame({"flag": [True, False, None]}), "flag").tolist() == [
        True, False, False
    ]
    assert boolean_flag_column(pd.DataFrame({"flag": [1, 0, None]}), "flag").tolist() == [
        True, False, False
    ]


def test_missing_flag_column_defaults_to_false() -> None:
    frame = pd.DataFrame({"other": [1, 2]})

    assert boolean_flag_column(frame, "missing").tolist() == [False, False]


def test_cleaning_does_not_treat_string_false_as_invalid() -> None:
    from patient_flow.cleaning import compute_valid_waits

    frame = pd.DataFrame(
        {
            "Total_Waiting_Time": [15.0, 30.0],
            "Negative_Wait_Flag": ["False", "True"],
            "Impossible_Timestamp_Flag": ["False", "False"],
        }
    )

    result = compute_valid_waits(frame)

    assert result["Total_Waiting_Time_Valid"].iloc[0] == 15.0
    assert pd.isna(result["Total_Waiting_Time_Valid"].iloc[1])


def test_feature_engineering_does_not_treat_string_false_as_invalid() -> None:
    from patient_flow.features import add_wait_quality_flags

    frame = pd.DataFrame(
        {
            "Total_Waiting_Time": [12.0],
            "Negative_Wait_Flag": ["False"],
            "Impossible_Timestamp_Flag": ["False"],
        }
    )

    result = add_wait_quality_flags(frame)

    assert result["Total_Waiting_Time_Valid"].iloc[0] == 12.0
    assert not bool(result["Long_Wait_Flag"].iloc[0])
