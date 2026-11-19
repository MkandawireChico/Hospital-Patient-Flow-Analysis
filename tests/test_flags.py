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
