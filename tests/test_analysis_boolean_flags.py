import pandas as pd

from patient_flow.analysis import _boolean_column


def test_boolean_column_parses_string_false_as_false() -> None:
    frame = pd.DataFrame({"flag": ["False", "True", "false", "true", None]})

    result = _boolean_column(frame, "flag")

    assert result.tolist() == [False, True, False, True, False]


def test_boolean_column_accepts_numeric_and_boolean_values() -> None:
    frame = pd.DataFrame({"flag": [0, 1, False, True, None]})

    result = _boolean_column(frame, "flag")

    assert result.tolist() == [False, True, False, True, False]


def test_boolean_column_missing_field_defaults_to_false() -> None:
    frame = pd.DataFrame({"other": [1, 2, 3]})

    result = _boolean_column(frame, "missing")

    assert result.tolist() == [False, False, False]
